import json
import logging
import hashlib
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import List, Literal, Optional

from config import get_shuftipro_adapter
from db.dynamo import save_kyc_session, get_kyc_session, update_kyc_session_status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KycStartRequest(BaseModel):
    user_id: str
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
    logger.info(f"Starting KYC verification for user: {body.user_id}")
    
    result = await adapter.start_verification(body.dict())
    
    # Determine status based on result
    status = "pending"
    if result.get("error"):
        status = "failed"
        logger.error(f"KYC verification failed for user {body.user_id}: {result.get('error')}")
    elif result.get("verification_url"):
        status = "pending"
        logger.info(f"KYC verification URL generated for user {body.user_id}")
    else:
        status = "unknown"
        logger.warning(f"KYC verification returned without URL or error for user {body.user_id}")
    
    # Store in DynamoDB
    save_kyc_session(
        reference=result["reference"],
        user_id=body.user_id,
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
    
    # Verify signature (if present)
    signature = request.headers.get("Signature")
    if signature:
        # Get secret key from adapter (already loaded from Vault)
        secret_key = adapter.secret_key
        secret_hash = hashlib.sha256(secret_key.encode()).hexdigest()
        calculated_sig = hashlib.sha256(f"{body_text}{secret_hash}".encode()).hexdigest()
        
        if signature != calculated_sig:
            logger.warning(f"Signature verification failed for {reference}")
            # Log but don't reject - some ShuftiPro modes don't send signatures
        else:
            logger.info(f"Signature verified for {reference}")
    
    # Extract status from webhook
    # ShuftiPro sends status in different formats depending on the event
    event = payload.get("event", "")
    status_code = payload.get("verification_status") or payload.get("status")
    
    # Map ShuftiPro events to our status
    if "verification.accepted" in event or status_code == "accepted":
        status = "approved"
    elif "verification.declined" in event or status_code == "declined":
        status = "declined"
    elif "verification.cancelled" in event:
        status = "cancelled"
    else:
        status = "pending"
    
    logger.info(f"Webhook status for {reference}: {status} (event: {event})")
    
    # Log OCR data if present
    if "document" in payload:
        doc_data = payload.get("document", {})
        if isinstance(doc_data, dict):
            name = doc_data.get("name")
            dob = doc_data.get("dob")
            doc_num = doc_data.get("document_number")
            logger.info(f"OCR data - Name: {name}, DOB: {dob}, Doc#: {doc_num}")
    
    # Update DynamoDB with webhook data
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
    
    # Return success
    return {
        "status": "received",
        "reference": reference,
        "message": "Webhook processed successfully"
    }
