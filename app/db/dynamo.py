import os
import boto3
import httpx
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


DYNAMODB_ENDPOINT = os.getenv("DYNAMODB_ENDPOINT", "http://dynamodb-local:8000")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


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


async def download_documents(user_id: str, document_urls: Dict[str, str], base_path: str = "/app/documents") -> Dict[str, str]:
    """
    Download documents from ShuftiPro URLs and save them to user-specific directory.
    
    Args:
        user_id: User identifier for directory name
        document_urls: Dict of {document_type: url}
        base_path: Base directory for storing documents
        
    Returns:
        Dict of {document_type: local_file_path}
    """
    # Create user directory
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
                
                # Save file
                filename = f"{doc_type}{ext}"
                file_path = user_dir / filename
                
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                downloaded_files[doc_type] = str(file_path)
                logger.info(f"Downloaded {doc_type} for user {user_id} to {file_path}")
                
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
    
    item = {
        "reference": reference,
        "user_id": user_id,
        "provider": provider,
        "status": status,
        "raw": raw_response,
        "updated_at": datetime.utcnow().isoformat(),
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
    table = get_table()
    resp = table.get_item(Key={"reference": reference})
    return resp.get("Item")
