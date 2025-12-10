import os
import boto3
import httpx
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging
from storage.s3 import get_s3_storage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT", "http://dynamodb-local:8000")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DOCUMENT_BACKUP_PATH = os.getenv("DOCUMENT_BACKUP_PATH", "/app/documents")
ALLOW_LOCAL_FALLBACK = os.getenv("ALLOW_LOCAL_FALLBACK", "true").lower() == "true"
MIN_FILE_SIZE_BYTES = int(os.getenv("MIN_FILE_SIZE_BYTES", "100"))  # Minimum valid file size


def get_table():
    resource = boto3.resource(
        "dynamodb",
        endpoint_url=DYNAMODB_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "dummy"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "dummy"),
    )
    return resource.Table("kyc_sessions")


def extract_ocr_fields(raw_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract normalized OCR fields from ShuftiPro webhook response.
    
    Per official docs, OCR data is in verification_data and additional_data:
    - verification_data: Main OCR fields (name, dob, document_number, address, etc.)
    - additional_data: Extra fields (nationality, place_of_birth, height, etc.)
    """
    fields = {}
    
    # Extract from verification_data (this is where ShuftiPro puts OCR data)
    verification_data = raw_response.get("verification_data", {})
    additional_data = raw_response.get("additional_data", {})
    
    # Extract email and phone from top level
    if "email" in raw_response:
        fields["email"] = raw_response.get("email")
    if "phone_number" in raw_response or "phone" in raw_response:
        fields["phone"] = raw_response.get("phone_number") or raw_response.get("phone")
    
    # Extract from verification_data.document
    if "document" in verification_data and isinstance(verification_data["document"], dict):
        doc = verification_data["document"]
        name_obj = doc.get("name", {})
        if isinstance(name_obj, dict):
            fields["first_name"] = name_obj.get("first_name")
            fields["last_name"] = name_obj.get("last_name")
            fields["full_name"] = name_obj.get("full_name")
        elif isinstance(name_obj, str):
            fields["full_name"] = name_obj
            
        fields["dob"] = doc.get("dob")
        fields["document_number"] = doc.get("document_number")
        fields["expiry_date"] = doc.get("expiry_date")
        fields["issue_date"] = doc.get("issue_date")
        
        selected = doc.get("selected_type")
        if isinstance(selected, list) and len(selected) > 0:
            fields["document_type"] = selected[0]
        elif isinstance(selected, str):
            fields["document_type"] = selected
            
        fields["country"] = doc.get("country")
        fields["gender"] = doc.get("gender")
    
    # Extract from verification_data.document_two if present
    if "document_two" in verification_data and isinstance(verification_data["document_two"], dict):
        doc2 = verification_data["document_two"]
        if not fields.get("full_name"):
            name_obj = doc2.get("name", {})
            if isinstance(name_obj, dict):
                fields["full_name"] = name_obj.get("full_name")
            elif isinstance(name_obj, str):
                fields["full_name"] = name_obj
        fields["document_two_number"] = doc2.get("document_number")
        fields["document_two_type"] = doc2.get("selected_type")
    
    # Extract from verification_data.address
    if "address" in verification_data and isinstance(verification_data["address"], dict):
        addr = verification_data["address"]
        fields["address_full"] = addr.get("full_address")
        fields["address_country"] = addr.get("country")
        fields["address_city"] = addr.get("city")
        fields["address_state"] = addr.get("state")
        fields["address_postal_code"] = addr.get("postal_code") or addr.get("zip_code")
    
    # Extract from additional_data.document.proof (extra OCR fields)
    if "document" in additional_data and isinstance(additional_data["document"], dict):
        doc_extra = additional_data["document"].get("proof", {})
        if isinstance(doc_extra, dict):
            fields["nationality"] = doc_extra.get("nationality")
            fields["place_of_birth"] = doc_extra.get("place_of_birth")
            fields["height"] = doc_extra.get("height")
            # Additional fields may override or supplement
            if not fields.get("gender"):
                fields["gender"] = doc_extra.get("gender")
    
    # Extract geolocation from info
    info = raw_response.get("info", {})
    if info:
        geo = info.get("geolocation", {})
        if geo:
            fields["country_code"] = geo.get("country_code")
    
    # Extract document image URLs from verification_data
    document_urls = {}
    if "document" in verification_data and isinstance(verification_data["document"], dict):
        doc = verification_data["document"]
        # ShuftiPro sends document images in various fields
        if "photo" in doc:
            document_urls["document_photo"] = doc["photo"]
        if "front" in doc:
            document_urls["document_front"] = doc["front"]
        if "back" in doc:
            document_urls["document_back"] = doc["back"]
    
    # Extract document_two images if present
    if "document_two" in verification_data and isinstance(verification_data["document_two"], dict):
        doc2 = verification_data["document_two"]
        if "photo" in doc2:
            document_urls["document_two_photo"] = doc2["photo"]
        if "front" in doc2:
            document_urls["document_two_front"] = doc2["front"]
        if "back" in doc2:
            document_urls["document_two_back"] = doc2["back"]
    
    # Extract face/selfie image
    if "face" in verification_data and isinstance(verification_data["face"], dict):
        face = verification_data["face"]
        if "proof" in face:
            document_urls["face_photo"] = face["proof"]
    
    # Extract address document
    if "address" in verification_data and isinstance(verification_data["address"], dict):
        addr = verification_data["address"]
        if "proof" in addr:
            document_urls["address_proof"] = addr["proof"]
    
    # Store document URLs if any found
    if document_urls:
        fields["document_urls"] = document_urls
        
    # Remove None values
    return {k: v for k, v in fields.items() if v is not None}


async def download_proof_documents(user_id: str, proofs: Dict[str, Any], access_token: str, base_path: Optional[str] = None) -> Dict[str, str]:
    """
    Download proof documents and videos from ShuftiPro using access token.
    Handles document proofs, verification videos, and reports with retry logic and validation.

    Args:
        user_id: User identifier for S3 key prefix
        proofs: Dict containing proof URLs (document.proof, address.proof, verification_video, verification_report, etc.)
        access_token: Access token for authenticating with ShuftiPro proof URLs
        base_path: Base directory for local backup (uses DOCUMENT_BACKUP_PATH env var if not provided)

    Returns:
        Dict of {proof_type: s3_key}
    """
    # Get S3 storage client
    try:
        s3 = get_s3_storage()
        use_s3 = True
    except Exception as e:
        error_msg = f"S3 storage initialization failed: {e}"
        if not ALLOW_LOCAL_FALLBACK:
            logger.error(f"{error_msg} - Local fallback not allowed in production mode")
            raise RuntimeError(f"S3 storage required but unavailable: {e}")
        logger.warning(f"{error_msg} - Falling back to local storage")
        use_s3 = False

    # Use configured path or provided path
    if base_path is None:
        base_path = DOCUMENT_BACKUP_PATH

    # Create user directory for local backup
    user_dir = Path(base_path) / user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    downloaded_files = {}

    # Extract URLs from nested structure - dynamically handle all proof types
    urls_to_download = {}

    # Handle nested proof objects (document, address, etc.)
    for key, value in proofs.items():
        if key == "access_token":
            continue  # Skip access_token field
            
        if isinstance(value, dict) and "proof" in value:
            # Nested proof object like {"document": {"proof": "url"}}
            proof_url = value.get("proof")
            if proof_url:
                urls_to_download[f"{key}_proof"] = proof_url
        elif isinstance(value, str) and value.startswith("http"):
            # Direct URL like {"verification_video": "url"}
            urls_to_download[key] = value

    logger.info(f"Found {len(urls_to_download)} proof URLs to download: {list(urls_to_download.keys())}")

    # Helper function with retry logic
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError))
    )
    async def download_with_retry(client: httpx.AsyncClient, url: str, payload: dict) -> httpx.Response:
        """Download file with retry logic for transient failures using POST method."""
        response = await client.post(url, json=payload, follow_redirects=True)
        response.raise_for_status()
        return response

    async with httpx.AsyncClient(timeout=60.0) as client:
        for proof_type, url in urls_to_download.items():
            if not url:
                continue

            try:
                logger.info(f"Downloading {proof_type} for user {user_id} from {url}")

                # Use POST method with access_token in body (per Shuftipro documentation)
                payload = {"access_token": access_token}
                response = await download_with_retry(client, url, payload)

                # Determine file extension
                content_type = response.headers.get("content-type", "")
                if "video" in content_type or "mp4" in content_type or proof_type == "verification_video":
                    ext = ".mp4"
                elif "pdf" in content_type or proof_type == "verification_report":
                    ext = ".pdf"
                elif "jpeg" in content_type or "jpg" in content_type:
                    ext = ".jpg"
                elif "png" in content_type:
                    ext = ".png"
                else:
                    ext = ".bin"  # Unknown type

                filename = f"{proof_type}{ext}"
                file_content = response.content

                # Validate file size
                file_size = len(file_content)
                if file_size < MIN_FILE_SIZE_BYTES:
                    logger.error(f"File {proof_type} is too small ({file_size} bytes), likely corrupted or empty")
                    continue

                # Validate content type matches expected type
                if proof_type == "verification_video" and "video" not in content_type:
                    logger.warning(f"Content type mismatch for {proof_type}: expected video, got {content_type}")
                elif proof_type == "verification_report" and "pdf" not in content_type:
                    logger.warning(f"Content type mismatch for {proof_type}: expected PDF, got {content_type}")

                logger.info(f"Downloaded {proof_type}: {file_size} bytes, type: {content_type}")

                # Save locally as backup
                local_path = user_dir / filename
                with open(local_path, "wb") as f:
                    f.write(file_content)
                logger.info(f"Saved local backup: {local_path}")

                # Upload to S3/MinIO if available
                if use_s3:
                    try:
                        s3_key = f"documents/{user_id}/{filename}"
                        s3.upload_file(
                            file_content=file_content,
                            key=s3_key,
                            content_type=content_type or "application/octet-stream"
                        )
                        logger.info(f"Uploaded {proof_type} to S3: {s3_key}")
                        downloaded_files[proof_type] = s3_key
                    except Exception as s3_error:
                        logger.error(f"S3 upload failed for {proof_type}: {s3_error}")
                        if not ALLOW_LOCAL_FALLBACK:
                            raise  # Re-raise if fallback not allowed
                        # Use local path if S3 fails and fallback is allowed
                        downloaded_files[proof_type] = str(local_path)
                        logger.warning(f"Using local path for {proof_type} due to S3 failure")
                else:
                    downloaded_files[proof_type] = str(local_path)

            except Exception as e:
                logger.error(f"Failed to download {proof_type} from {url} after retries: {e}")
                continue

    return downloaded_files


async def download_documents(user_id: str, document_urls: Dict[str, str], base_path: str = "/app/documents") -> Dict[str, str]:
    """
    Download documents from ShuftiPro URLs and upload to S3/MinIO.
    Also saves a local backup copy.
    
    Args:
        user_id: User identifier for S3 key prefix
        document_urls: Dict of {document_type: url}
        base_path: Base directory for local backup (optional)
        
    Returns:
        Dict of {document_type: s3_key}
    """
    # Get S3 storage client
    try:
        s3 = get_s3_storage()
        use_s3 = True
    except Exception as e:
        logger.warning(f"S3 storage not available, falling back to local: {e}")
        use_s3 = False
    
    # Create user directory for local backup
    user_dir = Path(base_path) / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded_files = {}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for doc_type, url in document_urls.items():
            if not url:
                continue
                
            try:
                # Download the file
                response = await client.get(url)
                response.raise_for_status()
                
                # Determine file extension from URL or content-type
                content_type = response.headers.get("content-type", "")
                if "jpeg" in content_type or "jpg" in content_type or url.endswith((".jpg", ".jpeg")):
                    ext = ".jpg"
                elif "png" in content_type or url.endswith(".png"):
                    ext = ".png"
                elif "pdf" in content_type or url.endswith(".pdf"):
                    ext = ".pdf"
                else:
                    ext = ".jpg"  # default
                
                filename = f"{doc_type}{ext}"
                
                # Upload to S3/MinIO
                if use_s3:
                    try:
                        # S3 key: documents/{user_id}/{filename}
                        s3_key = f"documents/{user_id}/{filename}"
                        s3.upload_file(
                            file_content=response.content,
                            key=s3_key,
                            content_type=content_type
                        )
                        downloaded_files[doc_type] = s3_key
                        logger.info(f"Uploaded {doc_type} for user {user_id} to S3: {s3_key}")
                    except Exception as s3_error:
                        logger.error(f"Failed to upload {doc_type} to S3: {s3_error}")
                        use_s3 = False  # Fall back to local for remaining files
                
                # Save local backup copy
                if not use_s3:
                    file_path = user_dir / filename
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    downloaded_files[doc_type] = str(file_path)
                    logger.info(f"Saved {doc_type} for user {user_id} locally: {file_path}")
                else:
                    # Also save local backup even when using S3
                    file_path = user_dir / filename
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    logger.debug(f"Local backup saved: {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to download {doc_type} for user {user_id}: {e}")
                continue
    
    return downloaded_files


def save_kyc_session(
    reference: str,
    user_id: str,
    provider: str,
    status: str,
    raw_response: Dict[str, Any],
    fields: Optional[Dict[str, Any]] = None,
):
    """Save or update KYC session in DynamoDB."""
    table = get_table()

    # Extract OCR fields if not provided
    if fields is None:
        fields = extract_ocr_fields(raw_response)

    # Check if this is a new session or update
    existing = table.get_item(Key={"reference": reference}).get("Item")

    now = datetime.utcnow().isoformat()
    item = {
        "reference": reference,
        "user_id": user_id,
        "provider": provider,
        "status": status,
        "raw": raw_response,
        "created_at": existing.get("created_at") if existing else now,  # Preserve original created_at
        "updated_at": now,
    }

    # Only add fields if there are any
    if fields:
        item["fields"] = fields

    table.put_item(Item=item)


def update_kyc_session_status(
    reference: str,
    status: str,
    raw_response: Dict[str, Any],
):
    """Update existing KYC session with new status and data (for webhooks)."""
    table = get_table()
    
    # Get existing session to preserve user_id
    existing = get_kyc_session(reference)
    if not existing:
        # If session doesn't exist, create minimal entry
        save_kyc_session(
            reference=reference,
            user_id="unknown",
            provider="shuftipro",
            status=status,
            raw_response=raw_response,
        )
        return
    
    # Extract OCR fields from webhook data
    fields = extract_ocr_fields(raw_response)
    
    # Update the session
    save_kyc_session(
        reference=reference,
        user_id=existing["user_id"],
        provider=existing["provider"],
        status=status,
        raw_response=raw_response,
        fields=fields,
    )


def get_kyc_session(reference: str) -> Optional[Dict[str, Any]]:
    """Retrieve a KYC session by reference."""
    table = get_table()
    
    response = table.get_item(Key={"reference": reference})
    return response.get("Item")


def list_kyc_sessions(limit: int = 50) -> list:
    """List all KYC sessions (most recent first)."""
    table = get_table()
    
    response = table.scan(Limit=limit)
    items = response.get("Items", [])
    
    # Sort by created_at descending (most recent first)
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return items
