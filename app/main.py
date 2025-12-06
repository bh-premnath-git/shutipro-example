import json
import logging
import hashlib
import time
import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional

from config import get_shuftipro_adapter
from db.dynamo import save_kyc_session, get_kyc_session, update_kyc_session_status, download_documents, list_kyc_sessions, download_proof_documents
from storage.s3 import get_s3_storage

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


class KycDeleteRequest(BaseModel):
    comment: str


class AccountInfoResponse(BaseModel):
    account: dict


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


@app.get("/kyc/sessions")
async def list_sessions(limit: int = 50):
    """
    List all KYC sessions from DynamoDB.
    Returns most recent sessions first.
    
    Query Parameters:
    - limit: Maximum number of sessions to return (default: 50, max: 100)
    """
    if limit > 100:
        limit = 100
    
    sessions = list_kyc_sessions(limit=limit)
    
    # Format response
    result = []
    for session in sessions:
        result.append({
            "reference": session.get("reference"),
            "user_id": session.get("user_id"),
            "email": session.get("raw", {}).get("email"),
            "status": session.get("status"),
            "provider": session.get("provider"),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "event": session.get("raw", {}).get("event"),
        })
    
    return {
        "count": len(result),
        "sessions": result
    }


@app.delete("/kyc/{reference}")
async def delete_verification(reference: str, body: KycDeleteRequest):
    """
    Delete verification data from ShuftiPro and local database.
    Required for GDPR compliance and data privacy.
    """
    # Check if session exists locally
    item = get_kyc_session(reference)
    if not item:
        raise HTTPException(status_code=404, detail="KYC session not found")
    
    # Call ShuftiPro delete API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth_header = adapter._auth_header()
            payload = {
                "reference": reference,
                "comment": body.comment
            }
            
            response = await client.post(
                "https://api.shuftipro.com/delete",
                headers=auth_header,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify signature
                signature = response.headers.get("Signature")
                if signature:
                    secret_hash = hashlib.sha256(adapter.secret_key.encode()).hexdigest()
                    calculated_sig = hashlib.sha256(f"{response.text}{secret_hash}".encode()).hexdigest()
                    if signature != calculated_sig:
                        logger.warning(f"Delete response signature mismatch for {reference}")
                
                # Delete from DynamoDB (mark as deleted, don't actually remove for audit trail)
                update_kyc_session_status(reference, "deleted", data)
                
                logger.info(f"Deleted verification {reference}: {body.comment}")
                return {"reference": reference, "event": "request.deleted", "comment": body.comment}
            else:
                error_data = response.json() if response.text else {}
                raise HTTPException(status_code=response.status_code, detail=error_data.get("message", "Delete failed"))
                
    except httpx.HTTPError as e:
        logger.error(f"Failed to delete verification {reference}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@app.get("/kyc/account", response_model=AccountInfoResponse)
async def get_account_info():
    """
    Get ShuftiPro account information including balance and subscription details.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth_header = adapter._auth_header()
            
            response = await client.get(
                "https://api.shuftipro.com/account/info/",
                headers=auth_header
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Account info retrieved: {data.get('account', {}).get('status')}")
                return AccountInfoResponse(account=data.get("account", {}))
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to get account info")
                
    except httpx.HTTPError as e:
        logger.error(f"Failed to get account info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get account info: {str(e)}")


@app.post("/kyc/query-status/{reference}")
async def query_shuftipro_status(reference: str):
    """
    Query verification status directly from ShuftiPro API.
    This pulls the latest data from ShuftiPro's servers.
    
    Use this to:
    - Get latest verification data from ShuftiPro
    - Check if OCR data is available
    - Verify what ShuftiPro has on their end
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth_header = adapter._auth_header()
            payload = {"reference": reference}
            
            response = await client.post(
                "https://api.shuftipro.com/status",
                headers=auth_header,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify signature
                signature = response.headers.get("Signature")
                if signature:
                    secret_hash = hashlib.sha256(adapter.secret_key.encode()).hexdigest()
                    calculated_sig = hashlib.sha256(f"{response.text}{secret_hash}".encode()).hexdigest()
                    if signature != calculated_sig:
                        logger.warning(f"Status query signature mismatch for {reference}")
                
                logger.info(f"Retrieved status from ShuftiPro for {reference}: {data.get('event')}")
                
                # Update local database with latest data
                if data.get("event") in ["verification.accepted", "verification.declined"]:
                    status = "approved" if data.get("event") == "verification.accepted" else "declined"
                    update_kyc_session_status(reference, status, data)
                    logger.info(f"Updated local database with ShuftiPro data for {reference}")
                
                return {
                    "reference": reference,
                    "shuftipro_data": data,
                    "message": "Data retrieved directly from ShuftiPro"
                }
            else:
                error_data = response.json() if response.text else {}
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"ShuftiPro API error: {error_data.get('message', 'Unknown error')}"
                )
                
    except httpx.HTTPError as e:
        logger.error(f"Failed to query ShuftiPro status for {reference}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query ShuftiPro: {str(e)}")


class DownloadProofsRequest(BaseModel):
    proofs: Optional[dict] = None


@app.post("/kyc/download-proofs/{reference}")
async def download_proofs(reference: str, body: Optional[DownloadProofsRequest] = None):
    """
    Download verification proofs (documents, videos, reports) from ShuftiPro to MinIO/S3.
    
    This downloads:
    - Document proof images
    - Verification video
    - Verification report (PDF)
    
    Files are stored in MinIO under: documents/{user_id}/
    
    Can provide proofs in request body or will fetch from session/ShuftiPro API.
    """
    # Get session to extract user_id
    session = get_kyc_session(reference)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    user_id = session.get("user_id")
    
    # Get proofs from request body or session
    if body and body.proofs:
        proofs = body.proofs
        access_token = proofs.get("access_token")
        logger.info(f"Using proofs from request body for {reference}")
    else:
        # Get proofs from session or query ShuftiPro API
        raw_data = session.get("raw", {})
        proofs = raw_data.get("proofs")
        
        if not proofs:
            # Query ShuftiPro API for proofs
            logger.info(f"Proofs not in session, querying ShuftiPro API for {reference}")
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{adapter.api_url}status",
                        headers=adapter._auth_header(),
                        json={"reference": reference}
                    )
                
                if response.status_code == 200:
                    shuftipro_data = response.json()
                    proofs = shuftipro_data.get("proofs", {})
                else:
                    raise HTTPException(status_code=400, detail=f"Failed to fetch proofs from ShuftiPro: {response.status_code}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to query ShuftiPro: {str(e)}")
        
        access_token = proofs.get("access_token")
    
    if not proofs:
        raise HTTPException(status_code=400, detail="No proofs found in session data or ShuftiPro")
    
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token found for downloading proofs")
    
    try:
        # Download proofs to MinIO
        downloaded = await download_proof_documents(user_id, proofs, access_token)
        
        if not downloaded:
            raise HTTPException(status_code=500, detail="Failed to download any proofs")
        
        logger.info(f"Downloaded {len(downloaded)} proofs for {reference}: {list(downloaded.keys())}")
        
        return {
            "reference": reference,
            "user_id": user_id,
            "downloaded": downloaded,
            "count": len(downloaded),
            "message": f"Successfully downloaded {len(downloaded)} proof files to MinIO"
        }
        
    except Exception as e:
        logger.error(f"Failed to download proofs for {reference}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download proofs: {str(e)}")


@app.get("/kyc/documents/{user_id}")
async def list_documents(user_id: str):
    """List all documents for a user from S3 storage."""
    try:
        s3 = get_s3_storage()
        prefix = f"documents/{user_id}/"
        files = s3.list_files(prefix=prefix)
        
        # Generate presigned URLs for each file
        documents = []
        for file_key in files:
            filename = file_key.split("/")[-1]
            url = s3.get_object_url(file_key, expires_in=3600)
            documents.append({
                "key": file_key,
                "filename": filename,
                "url": url,
                "expires_in": "1 hour"
            })
        
        return {
            "user_id": user_id,
            "count": len(documents),
            "documents": documents
        }
    except Exception as e:
        logger.error(f"Failed to list documents for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kyc/documents/{user_id}/{filename}")
async def get_document_url(user_id: str, filename: str, expires_in: int = 3600):
    """Get a presigned URL for a specific document."""
    try:
        s3 = get_s3_storage()
        key = f"documents/{user_id}/{filename}"
        url = s3.get_object_url(key, expires_in=expires_in)
        
        return {
            "user_id": user_id,
            "filename": filename,
            "url": url,
            "expires_in_seconds": expires_in
        }
    except Exception as e:
        logger.error(f"Failed to get document URL for {user_id}/{filename}: {e}")
        raise HTTPException(status_code=404, detail="Document not found")


@app.post("/kyc/shuftipro/webhook")
async def shuftipro_webhook(request: Request):
    """
    Receive ShuftiPro webhook callbacks with final verification results and OCR data.
    
    ShuftiPro sends the complete verification result including:
    - Status (verification.accepted, verification.declined, etc.)
    - OCR'd document fields (name, DOB, document number, etc.)
    - Face verification results (if enabled)
    - Reason codes for declined verifications
    
    Note: This endpoint is called by ShuftiPro, not by clients.
    For testing, use the /kyc/test-webhook endpoint instead.
    """
    # Get raw body for signature verification
    body_bytes = await request.body()
    body_text = body_bytes.decode('utf-8')
    
    # Check if body is empty
    if not body_text or body_text.strip() == '':
        logger.warning("Webhook received empty body")
        raise HTTPException(
            status_code=400, 
            detail="Empty webhook payload. This endpoint is for ShuftiPro callbacks only. Use /kyc/test-webhook for testing."
        )
    
    # Parse JSON payload
    try:
        payload = json.loads(body_text)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    
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
    
    # Map ShuftiPro events to our status (all possible callback events)
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
    elif event == "verification.status.changed":
        # Status updated by ShuftiPro - get actual status from payload
        status = payload.get("status", "status_changed")
        logger.info(f"Verification status changed to: {status}")
    elif event == "request.deleted":
        status = "deleted"
    elif event == "request.data.changed":
        status = "data_changed"
        logger.info(f"Request data manually updated by client")
    # HTTP-only events (not sent to callback, but handle just in case)
    elif event == "request.invalid":
        status = "invalid"
    elif event == "request.unauthorized":
        status = "unauthorized"
    else:
        status = "unknown"
        logger.warning(f"Unknown event type: {event}")
    
    logger.info(f"Webhook event: {event} | Status: {status} | Reference: {reference}")
    
    # Extract OCR data from verification_data and additional_data (official structure)
    verification_data = payload.get("verification_data", {})
    additional_data = payload.get("additional_data", {})
    
    # Log available OCR data for debugging
    if verification_data:
        doc_data = verification_data.get("document", {})
        if doc_data:
            # Check if name exists as object or string
            name = doc_data.get("name", {})
            first_name = name.get('first_name') if isinstance(name, dict) else None
            last_name = name.get('last_name') if isinstance(name, dict) else None
            full_name = name.get('full_name') if isinstance(name, dict) else name if isinstance(name, str) else None
            
            dob = doc_data.get('dob') or doc_data.get('date_of_birth')
            doc_number = doc_data.get('document_number') or doc_data.get('number')
            
            if first_name or last_name or full_name or dob or doc_number:
                logger.info(f"OCR - Name: {first_name} {last_name} ({full_name}), DOB: {dob}, Doc#: {doc_number}")
            else:
                logger.warning(f"OCR data structure: {json.dumps(doc_data, indent=2)}")
                logger.warning("OCR fields not found in expected format - check journey configuration")
        
        addr_data = verification_data.get("address", {})
        if addr_data:
            logger.info(f"OCR - Address: {addr_data.get('full_address')}")
    
    # Also check additional_data for OCR fields
    if additional_data:
        logger.info(f"Additional data available: {list(additional_data.keys())}")
    
    # Log declined reasons if verification was declined
    if event == "verification.declined":
        declined_reason = payload.get("declined_reason")
        declined_codes = payload.get("declined_codes", [])
        services_declined_codes = payload.get("services_declined_codes", {})
        
        if declined_reason:
            logger.warning(f"Declined reason: {declined_reason}")
        if declined_codes:
            logger.warning(f"Declined codes: {declined_codes}")
        if services_declined_codes:
            logger.warning(f"Service-specific declined codes: {json.dumps(services_declined_codes)}")
    
    # Log warnings if any anomalies detected
    warnings = payload.get("warnings")
    if warnings:
        logger.warning(f"Anomalies detected: {json.dumps(warnings)}")
    
    # Log info object (geolocation, agent details)
    info = payload.get("info", {})
    if info:
        geo = info.get("geolocation", {})
        agent = info.get("agent", {})
        if geo:
            logger.info(f"User location: {geo.get('city')}, {geo.get('country_name')} (IP: {geo.get('ip')})")
        if agent:
            logger.info(f"User device: {agent.get('device_name')} | Browser: {agent.get('browser_name')}")
    
    # Log if no OCR data found
    if not verification_data.get("document", {}).get("name"):
        logger.warning(f"No OCR data in webhook - Journey may not be configured for data extraction")
        logger.info("See ENABLE_OCR_GUIDE.md for setup instructions")
    
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
    
    # Fetch proof URLs from ShuftiPro API and update database (for accepted/declined/review_pending)
    if event in ["verification.accepted", "verification.declined", "review.pending"]:
        try:
            logger.info(f"Fetching proof URLs from ShuftiPro API for {reference}")
            
            # Query ShuftiPro status endpoint
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{adapter.api_url}status",
                    headers=adapter._auth_header(),
                    json={"reference": reference}
                )
            
            if response.status_code == 200:
                shuftipro_data = response.json()
                proofs = shuftipro_data.get("proofs")
                
                if proofs:
                    # Update database with proof URLs
                    update_kyc_session_status(
                        reference=reference,
                        status=status,
                        raw_response={**payload, "proofs": proofs}
                    )
                    logger.info(f"Updated {reference} with proof URLs from ShuftiPro API")
                    
                    # Optionally download proofs to MinIO
                    try:
                        existing = get_kyc_session(reference)
                        if existing:
                            user_id = existing.get("user_id")
                            access_token = proofs.get("access_token")
                            
                            if access_token:
                                logger.info(f"Downloading proofs to MinIO for user {user_id}")
                                downloaded = await download_proof_documents(
                                    user_id=user_id,
                                    proofs=proofs,
                                    access_token=access_token
                                )
                                logger.info(f"Downloaded {len(downloaded)} proofs to MinIO: {list(downloaded.keys())}")
                            else:
                                logger.warning(f"No access_token in proofs for {reference}")
                    except Exception as e:
                        logger.warning(f"Failed to download proofs to MinIO for {reference}: {e}")
                else:
                    logger.warning(f"No proofs available in ShuftiPro response for {reference}")
            else:
                logger.warning(f"Failed to fetch proofs from ShuftiPro: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching proof URLs for {reference}: {e}")
            # Don't fail the webhook if proof fetching fails
    
    # Download documents if available (legacy)
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


@app.post("/kyc/test-webhook")
async def test_webhook(reference: str):
    """
    Test webhook endpoint - simulates a ShuftiPro verification.accepted callback.
    Use this to test the webhook processing without completing a real verification.
    
    Example: POST /kyc/test-webhook?reference=ref-user-1764924147-7023
    """
    # Create a mock verification.accepted webhook payload
    test_payload = {
        "reference": reference,
        "event": "verification.accepted",
        "email": "test@example.com",
        "country": "US",
        "verification_data": {
            "document": {
                "name": {
                    "first_name": "Test",
                    "last_name": "User",
                    "full_name": "Test User"
                },
                "dob": "1990-01-15",
                "document_number": "TEST123456",
                "expiry_date": "2030-12-31",
                "issue_date": "2020-01-01",
                "country": "US",
                "selected_type": ["passport"],
                "supported_types": ["passport", "id_card", "driving_license"]
            }
        },
        "verification_result": {
            "document": {
                "document": 1,
                "document_visibility": 1,
                "document_must_not_be_expired": 1,
                "selected_type": 1
            }
        },
        "info": {
            "agent": {
                "useragent": "Test User Agent",
                "device_name": "Test Device",
                "browser_name": "Test Browser",
                "platform_name": "Test OS",
                "is_desktop": True,
                "is_phone": False
            },
            "geolocation": {
                "ip": "127.0.0.1",
                "country_name": "Test Country",
                "country_code": "US",
                "city": "Test City",
                "timezone": "UTC"
            }
        },
        "additional_data": {
            "document": {
                "proof": {
                    "gender": "M",
                    "nationality": "US CITIZEN",
                    "place_of_birth": "Test City"
                }
            }
        }
    }
    
    # Check if session exists
    session = get_kyc_session(reference)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {reference} not found. Start a verification first.")
    
    # Update session with test data
    update_kyc_session_status(reference, "approved", test_payload)
    
    logger.info(f"Test webhook processed for {reference}")
    
    return {
        "status": "success",
        "message": f"Test webhook processed for {reference}",
        "data": test_payload
    }
