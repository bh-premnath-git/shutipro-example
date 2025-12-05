import json
import logging
import hashlib
import time
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional

from config import get_shuftipro_adapter
from db.dynamo import save_kyc_session, get_kyc_session, update_kyc_session_status, download_documents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KycStartRequest(BaseModel):
    user_id: Optional[str] = None
    email: EmailStr
    journey_id: Optional[str] = None


class KycStartResponse(BaseModel):
    reference: str
    provider: str
    verification_url: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


class KycStatusResponse(BaseModel):
    reference: str
    provider: str
    status: str
    raw: dict


app = FastAPI(title="KYC Backend")
adapter = get_shuftipro_adapter()


@app.post("/kyc/start", response_model=KycStartResponse)
async def kyc_start(body: KycStartRequest):
    # Generate user_id if not provided
    user_id = body.user_id or f"user-{int(time.time())}"
    logger.info(f"Starting KYC verification for user: {user_id}")
    
    # Create request dict with user_id
    request_data = body.dict()
    request_data['user_id'] = user_id
    
    result = await adapter.start_verification(request_data)
    
    # Determine status based on result
    status = "pending"
    if result.get("error"):
        status = "failed"
        logger.error(f"KYC verification failed for user {user_id}: {result.get('error')}")
    elif result.get("verification_url"):
        status = "pending"
        logger.info(f"KYC verification URL generated for user {user_id}")
    else:
        status = "unknown"
        logger.warning(f"KYC verification returned without URL or error for user {user_id}")
    
    # Store in DynamoDB
    save_kyc_session(
        reference=result["reference"],
        user_id=user_id,
        provider=result["provider"],
        status=status,
        raw_response=result["raw"],
    )
    
    # Convert error to string if it's a dict
    error = result.get("error")
    if error and isinstance(error, dict):
        error = json.dumps(error)
    
    return KycStartResponse(
        reference=result["reference"],
        provider=result["provider"],
        verification_url=result.get("verification_url"),
        error=error,
        status_code=result.get("status_code"),
    )


@app.get("/kyc/status/{reference}", response_model=KycStatusResponse)
async def kyc_status(reference: str):
    item = get_kyc_session(reference)
    if not item:
        raise HTTPException(status_code=404, detail="KYC session not found")

    return KycStatusResponse(
        reference=item["reference"],
        provider=item["provider"],
        status=item["status"],
        raw=item.get("raw", {}),
    )


@app.post("/kyc/shuftipro/webhook")
async def shuftipro_webhook(request: Request):
    """
    Receive ShuftiPro webhook callbacks with final verification results and OCR data.
    
    ShuftiPro sends the complete verification result including:
    - Status (verification.accepted, verification.declined, etc.)
    - OCR'd document fields (name, DOB, document number, etc.)
    - Face verification results (if enabled)
    - Reason codes for declined verifications
    """
    # Get raw body for signature verification
    body_bytes = await request.body()
    body_text = body_bytes.decode('utf-8')
    
    # Parse JSON payload
    try:
        payload = json.loads(body_text)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Extract reference
    reference = payload.get("reference")
    if not reference:
        logger.error("Webhook missing reference")
        raise HTTPException(status_code=400, detail="Missing reference")
    
    logger.info(f"Received webhook for reference: {reference}")
    logger.debug(f"Webhook payload: {json.dumps(payload, indent=2)}")
    
    # Verify signature (required for production)
    signature = request.headers.get("Signature")
    if signature:
        # Get secret key from adapter (already loaded from Vault)
        secret_key = adapter.secret_key
        # Double hash for clients registered after 15 March 2023
        secret_hash = hashlib.sha256(secret_key.encode()).hexdigest()
        calculated_sig = hashlib.sha256(f"{body_text}{secret_hash}".encode()).hexdigest()
        
        if signature != calculated_sig:
            logger.error(f"Signature verification FAILED for {reference}")
            raise HTTPException(status_code=401, detail="Invalid signature")
        else:
            logger.info(f"Signature verified for {reference}")
    else:
        logger.warning(f"No signature header for {reference} - accepting anyway")
    
    # Extract event and status
    event = payload.get("event", "")
    
    # Map ShuftiPro events to our status
    if event == "verification.accepted":
        status = "approved"
    elif event == "verification.declined":
        status = "declined"
    elif event == "verification.cancelled":
        status = "cancelled"
    elif event == "review.pending":
        status = "review_pending"
    elif event in ["request.pending", "request.received"]:
        status = "pending"
    elif event == "request.timeout":
        status = "timeout"
    else:
        status = "unknown"
        logger.warning(f"Unknown event type: {event}")
    
    logger.info(f"Webhook event: {event} | Status: {status} | Reference: {reference}")
    
    # Extract OCR data from verification_data and additional_data (official structure)
    verification_data = payload.get("verification_data", {})
    additional_data = payload.get("additional_data", {})
    
    if verification_data:
        # Log key OCR fields for monitoring
        doc_data = verification_data.get("document", {})
        if doc_data:
            name = doc_data.get("name", {})
            logger.info(f"OCR - Name: {name.get('first_name')} {name.get('last_name')}, DOB: {doc_data.get('dob')}, Doc#: {doc_data.get('document_number')}")
        
        addr_data = verification_data.get("address", {})
        if addr_data:
            logger.info(f"OCR - Address: {addr_data.get('full_address')}")
    
    # Update DynamoDB first to extract OCR fields including document URLs
    try:
        update_kyc_session_status(
            reference=reference,
            status=status,
            raw_response=payload,
        )
        logger.info(f"Successfully updated session {reference} with status {status}")
    except Exception as e:
        logger.error(f"Failed to update session {reference}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session")
    
    # Download documents if available
    try:
        # Get updated session with extracted fields
        existing = get_kyc_session(reference)
        if existing:
            user_id = existing.get("user_id")
            fields = existing.get("fields", {})
            document_urls = fields.get("document_urls", {})
            
            # Download documents if any URLs found
            if document_urls:
                logger.info(f"Downloading {len(document_urls)} documents for user {user_id}")
                downloaded = await download_documents(user_id, document_urls)
                logger.info(f"Downloaded {len(downloaded)} documents: {list(downloaded.keys())}")
    except Exception as e:
        logger.error(f"Failed to download documents for {reference}: {e}")
        # Don't fail the webhook if download fails
    
    # Return success
    return {
        "status": "received",
        "reference": reference,
        "message": "Webhook processed successfully"
    }
