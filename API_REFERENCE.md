# KYC API Reference

Complete API reference for the KYC backend with all available endpoints.

## Base URL

```
Development: http://localhost:8181
Production: https://your-domain.com
```

## Authentication

All requests to ShuftiPro are authenticated via the backend. No authentication required for client API calls in development.

---

## Endpoints

### 1. Start KYC Verification

Start a new KYC verification session.

**Endpoint:** `POST /kyc/start`

**Request Body:**
```json
{
  "email": "user@example.com",
  "user_id": "optional-user-id",
  "journey_id": "optional-journey-id"
}
```

**Parameters:**
- `email` (required): User's email address
- `user_id` (optional): Custom user ID. Auto-generated if not provided
- `journey_id` (optional): ShuftiPro journey ID. Defaults to `iySLIfgD1764787557`

**Response:** `200 OK`
```json
{
  "reference": "ref-user-1764924147-7023",
  "provider": "shuftipro",
  "verification_url": "https://app.shuftipro.com/verification/process/...",
  "error": null,
  "status_code": null
}
```

**Example:**
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}' | jq
```

---

### 2. Get Verification Status

Get the current status of a verification.

**Endpoint:** `GET /kyc/status/{reference}`

**Path Parameters:**
- `reference`: Verification reference ID

**Response:** `200 OK`
```json
{
  "reference": "ref-user-1764924147-7023",
  "provider": "shuftipro",
  "status": "approved",
  "raw": {
    "event": "verification.accepted",
    "verification_data": { ... },
    "verification_result": { ... },
    "info": { ... },
    "additional_data": { ... }
  }
}
```

**Status Values:**
- `pending` - Verification initiated
- `approved` - Verification accepted
- `declined` - Verification declined
- `cancelled` - User cancelled
- `timeout` - Verification timed out
- `review_pending` - Manual review required
- `deleted` - Verification deleted

**Example:**
```bash
curl http://localhost:8181/kyc/status/ref-user-1764924147-7023 | jq
```

---

### 3. Delete Verification

Delete verification data from ShuftiPro and local database (GDPR compliance).

**Endpoint:** `DELETE /kyc/{reference}`

**Path Parameters:**
- `reference`: Verification reference ID

**Request Body:**
```json
{
  "comment": "User requested deletion"
}
```

**Parameters:**
- `comment` (required): Reason for deletion (5-100 characters)

**Response:** `200 OK`
```json
{
  "reference": "ref-user-1764924147-7023",
  "event": "request.deleted",
  "comment": "User requested deletion"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8181/kyc/ref-user-1764924147-7023 \
  -H 'Content-Type: application/json' \
  -d '{"comment":"User requested GDPR deletion"}' | jq
```

---

### 4. Get Account Info

Get ShuftiPro account information including balance and subscription details.

**Endpoint:** `GET /kyc/account`

**Response:** `200 OK`

**Trial Account:**
```json
{
  "account": {
    "name": "Your Account Name",
    "status": "trial",
    "balance": {
      "amount": "85.05",
      "currency": "USD"
    }
  }
}
```

**Production Account with Subscription:**
```json
{
  "account": {
    "name": "Your Account Name",
    "status": "production",
    "balance": {
      "amount": "99.85",
      "currency": "USD"
    },
    "subscription_plan_details": {
      "kyc": [
        {
          "total_requests": 100,
          "used_requests": 25,
          "remaining_requests": 75,
          "start_date": "2025-12-01",
          "end_date": "2025-12-31"
        }
      ]
    }
  }
}
```

**Example:**
```bash
curl http://localhost:8181/kyc/account | jq
```

---

### 5. List User Documents

List all documents for a user from S3/MinIO storage.

**Endpoint:** `GET /kyc/documents/{user_id}`

**Path Parameters:**
- `user_id`: User identifier

**Response:** `200 OK`
```json
{
  "user_id": "user-123",
  "count": 2,
  "documents": [
    {
      "key": "documents/user-123/passport_front.jpg",
      "filename": "passport_front.jpg",
      "url": "http://minio:9000/kyc-documents/...?presigned",
      "expires_in": "1 hour"
    },
    {
      "key": "documents/user-123/selfie.jpg",
      "filename": "selfie.jpg",
      "url": "http://minio:9000/kyc-documents/...?presigned",
      "expires_in": "1 hour"
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8181/kyc/documents/user-123 | jq
```

---

### 6. Get Document URL

Get a presigned URL for a specific document.

**Endpoint:** `GET /kyc/documents/{user_id}/{filename}`

**Path Parameters:**
- `user_id`: User identifier
- `filename`: Document filename

**Query Parameters:**
- `expires_in` (optional): URL expiration in seconds (default: 3600)

**Response:** `200 OK`
```json
{
  "user_id": "user-123",
  "filename": "passport_front.jpg",
  "url": "http://minio:9000/kyc-documents/documents/user-123/passport_front.jpg?...",
  "expires_in_seconds": 3600
}
```

**Example:**
```bash
curl "http://localhost:8181/kyc/documents/user-123/passport_front.jpg?expires_in=7200" | jq
```

---

### 7. Test Webhook (For Testing)

Simulate a successful verification without completing a real one.

**Endpoint:** `POST /kyc/test-webhook?reference={reference}`

**Query Parameters:**
- `reference` (required): Verification reference ID from `/kyc/start`

**Response:** `200 OK`
```json
{
  "status": "success",
  "message": "Test webhook processed for ref-user-xxx",
  "data": {
    "reference": "ref-user-xxx",
    "event": "verification.accepted",
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
        "country": "US"
      }
    }
  }
}
```

**Example:**
```bash
# Start verification
REF=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq -r '.reference')

# Simulate successful verification
curl -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF" | jq

# Check status (will show OCR data)
curl http://localhost:8181/kyc/status/$REF | jq
```

**Use Case:**
- Testing webhook processing without completing real verification
- Populating test data with OCR fields
- Development and integration testing

---

### 8. Webhook Endpoint (ShuftiPro Only)

Receive ShuftiPro webhook callbacks (internal use only).

**Endpoint:** `POST /kyc/shuftipro/webhook`

**Headers:**
- `Signature`: SHA256 signature for verification

**Request Body:** (varies by event)
```json
{
  "reference": "ref-user-xxx",
  "event": "verification.accepted",
  "verification_data": { ... },
  "verification_result": { ... },
  "info": { ... }
}
```

**Events Handled:**
- `request.pending`
- `request.received`
- `verification.accepted`
- `verification.declined`
- `verification.cancelled`
- `request.timeout`
- `review.pending`
- `verification.status.changed`
- `request.deleted`
- `request.data.changed`

**Response:** `200 OK`
```json
{
  "status": "processed",
  "reference": "ref-user-xxx"
}
```

---

## Response Data Structures

### Verification Data

Complete verification data from ShuftiPro webhook:

```json
{
  "verification_data": {
    "document": {
      "name": {
        "first_name": "John",
        "last_name": "Doe",
        "full_name": "John Doe"
      },
      "dob": "1990-01-15",
      "document_number": "ABC123456",
      "expiry_date": "2030-12-31",
      "issue_date": "2020-01-01",
      "country": "CA",
      "selected_type": ["passport"]
    },
    "address": {
      "full_address": "123 Main St, Toronto, ON",
      "issue_date": "2024-01-01"
    }
  }
}
```

### Verification Result

Pass/fail status for each check:

```json
{
  "verification_result": {
    "document": {
      "document": 1,                      // 1=pass, 0=fail, null=not checked
      "document_visibility": 1,
      "document_must_not_be_expired": 1,
      "selected_type": 1
    }
  }
}
```

### Info Object

User device and location information:

```json
{
  "info": {
    "agent": {
      "useragent": "Mozilla/5.0...",
      "device_name": "Windows NT 10.0",
      "browser_name": "Chrome 142.0.0.0",
      "platform_name": "Windows 10",
      "is_desktop": true,
      "is_phone": false
    },
    "geolocation": {
      "ip": "2409:40f4:...",
      "country_name": "India",
      "country_code": "IN",
      "region_name": "Madhya Pradesh",
      "city": "Chhindwara",
      "latitude": "22.057399749756",
      "longitude": "78.938201904297",
      "timezone": "Asia/Kolkata"
    }
  }
}
```

### Additional Data

Extra OCR extracted fields:

```json
{
  "additional_data": {
    "document": {
      "proof": {
        "gender": "M",
        "height": "183",
        "nationality": "BRITISH CITIZEN",
        "place_of_birth": "BRISTOL",
        "authority": "HMPO",
        "signature": "335,300,435,400"    // Coordinates
      }
    }
  }
}
```

### Declined Information

When verification is declined:

```json
{
  "declined_reason": "Document expired",
  "declined_codes": [1001, 1002],
  "services_declined_codes": {
    "document": [1001],
    "face": [2003]
  }
}
```

### Warnings

Detected anomalies:

```json
{
  "warnings": {
    "document": {
      "png_format_detected": "The image is in PNG format...",
      "metadata_alteration_detected": "The image metadata is incomplete..."
    }
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Bad Request: one or more parameter is invalid or missing."
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid signature"
}
```

### 404 Not Found
```json
{
  "detail": "KYC session not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to update session"
}
```

---

## Rate Limits

**Production Account:**
- 60 requests/minute per IP

**Trial Account:**
- 20 requests/minute

---

## Interactive API Documentation

### Swagger UI
```
http://localhost:8181/docs
```

### ReDoc
```
http://localhost:8181/redoc
```

---

## Complete Workflow Example

### 1. Start Verification
```bash
RESPONSE=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}')

echo $RESPONSE | jq
```

### 2. Extract Reference and URL
```bash
REF=$(echo $RESPONSE | jq -r '.reference')
URL=$(echo $RESPONSE | jq -r '.verification_url')

echo "Reference: $REF"
echo "Verification URL: $URL"
```

### 3. User Completes Verification
User clicks the `verification_url` and completes KYC.

### 4. Check Status
```bash
curl http://localhost:8181/kyc/status/$REF | jq
```

### 5. List Documents
```bash
# Get user_id from reference (e.g., ref-user-1764924147-7023 → user-1764924147)
USER_ID=$(echo $REF | sed 's/ref-//' | cut -d'-' -f1,2)

curl http://localhost:8181/kyc/documents/$USER_ID | jq
```

### 6. Download Document
```bash
# Get presigned URL
DOC_URL=$(curl -s http://localhost:8181/kyc/documents/$USER_ID/passport_front.jpg | jq -r '.url')

# Download
curl -o passport.jpg "$DOC_URL"
```

### 7. Delete (if needed)
```bash
curl -X DELETE http://localhost:8181/kyc/$REF \
  -H 'Content-Type: application/json' \
  -d '{"comment":"User requested deletion"}' | jq
```

---

## Webhook Signature Verification

ShuftiPro signs all webhooks with SHA256:

```python
import hashlib

# For accounts registered after March 15, 2023
secret_hash = hashlib.sha256(secret_key.encode()).hexdigest()
calculated_sig = hashlib.sha256(f"{response_body}{secret_hash}".encode()).hexdigest()

if request_signature == calculated_sig:
    # Signature valid
    process_webhook(payload)
```

---

## S3/MinIO Storage Structure

Documents are stored with this key pattern:

```
documents/{user_id}/{document_type}.{ext}

Examples:
documents/user-1764924147/passport_front.jpg
documents/user-1764924147/passport_back.jpg
documents/user-1764924147/selfie.jpg
```

---

## Support

**Issues:** Check application logs
```bash
docker compose logs app -f
```

**Webhook debugging:**
```bash
docker compose logs app | grep webhook
```

**ShuftiPro support:**
- Email: support@shuftipro.com
- Tech support: tech@shuftipro.com

---

**API Version:** 1.0.0  
**Last Updated:** December 2025
