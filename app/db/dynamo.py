import os
import boto3
from typing import Optional, Dict, Any
from datetime import datetime


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
    """Extract normalized OCR fields from ShuftiPro response."""
    fields = {}
    
    # Extract email and phone from top level
    if "email" in raw_response:
        fields["email"] = raw_response.get("email")
    if "phone_number" in raw_response or "phone" in raw_response:
        fields["phone"] = raw_response.get("phone_number") or raw_response.get("phone")
    
    # Extract from document
    if "document" in raw_response and isinstance(raw_response["document"], dict):
        doc = raw_response["document"]
        fields["full_name"] = doc.get("name", {}).get("full_name") or doc.get("name")
        fields["first_name"] = doc.get("name", {}).get("first_name")
        fields["last_name"] = doc.get("name", {}).get("last_name")
        fields["dob"] = doc.get("dob")
        fields["document_number"] = doc.get("document_number")
        fields["expiry_date"] = doc.get("expiry_date")
        fields["issue_date"] = doc.get("issue_date")
        fields["document_type"] = doc.get("selected_type") or doc.get("supported_types", [None])[0]
        fields["country"] = doc.get("country")
        fields["gender"] = doc.get("gender")
        
    # Extract from document_two if present
    if "document_two" in raw_response and isinstance(raw_response["document_two"], dict):
        doc2 = raw_response["document_two"]
        if not fields.get("full_name"):
            fields["full_name"] = doc2.get("name", {}).get("full_name") or doc2.get("name")
        fields["document_two_number"] = doc2.get("document_number")
        fields["document_two_type"] = doc2.get("selected_type")
    
    # Extract from address if present
    if "address" in raw_response and isinstance(raw_response["address"], dict):
        addr = raw_response["address"]
        fields["address_full"] = addr.get("full_address")
        fields["address_country"] = addr.get("country")
        fields["address_city"] = addr.get("city")
        fields["address_state"] = addr.get("state")
        fields["address_postal_code"] = addr.get("postal_code") or addr.get("zip_code")
        
    # Remove None values
    return {k: v for k, v in fields.items() if v is not None}


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
