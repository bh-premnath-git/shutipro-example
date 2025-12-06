# API Documentation

Complete API reference for the KYC backend with all endpoints, webhook events, and response structures.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
- [Webhook Events](#webhook-events)
- [Response Structures](#response-structures)
- [Error Responses](#error-responses)
- [Feature Coverage](#feature-coverage)

---

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

Start a new KYC verification session with automatic OCR extraction.

**Endpoint:** `POST /kyc/start`

**Request Body:**
```json
{
  "email": "user@example.com",
  "user_id": "optional-user-id",
  "journey_id": "optional-journey-id",
  "enable_ocr": true,
  "use_journey": false
}
```

**Parameters:**
- `email` (required): User's email address
- `user_id` (optional): Custom user ID. Auto-generated if not provided
- `journey_id` (optional): ShuftiPro journey ID. Defaults to `iySLIfgD1764787557`
- `enable_ocr` (optional): Enable OCR extraction via API payload (default: true)
- `use_journey` (optional): Use journey configuration instead of API payload (default: false)

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

Get the current status and OCR data for a verification.

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
        "country": "US"
      }
    },
    "proofs": {
      "document": {"proof": "https://..."},
      "access_token": "xxx",
      "verification_video": "https://...",
      "verification_report": "https://..."
    }
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
- `status_changed` - Status updated
- `data_changed` - Data manually updated

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

```json
{
  "account": {
    "name": "Your Account Name",
    "status": "trial",
    "balance": {
      "amount": "85.05",
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

### 7. Test Webhook

Simulate a successful verification without completing a real one (for testing only).

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
REF=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq -r '.reference')

curl -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF" | jq
```

---

### 8. Webhook Endpoint

Receive ShuftiPro webhook callbacks (internal use only - called by ShuftiPro).

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

**Response:** `200 OK`
```json
{
  "status": "processed",
  "reference": "ref-user-xxx"
}
```

---

## Webhook Events

### Automatic Webhook Processing

When ShuftiPro sends a webhook, the system automatically:

1. **Verifies signature** - Validates webhook authenticity
2. **Stores OCR data** - Extracts and saves all document fields
3. **Fetches proof URLs** - Queries ShuftiPro for document/video URLs
4. **Downloads proofs** - Saves documents to MinIO/S3
5. **Updates database** - Merges all data into DynamoDB

### Supported Events

All 12 ShuftiPro webhook events are handled:

| Event | Status Mapped | Triggers Proof Fetch | Notes |
|-------|---------------|---------------------|-------|
| `request.pending` | `pending` | No | Request valid, URL generated |
| `request.received` | `pending` | No | Request received |
| `verification.accepted` | `approved` | **Yes** | Verification passed |
| `verification.declined` | `declined` | **Yes** | Verification failed |
| `verification.cancelled` | `cancelled` | No | User cancelled |
| `request.timeout` | `timeout` | No | 60min timeout |
| `review.pending` | `review_pending` | **Yes** | Manual review required |
| `verification.status.changed` | `status_changed` | No | Status updated |
| `request.deleted` | `deleted` | No | Request deleted |
| `request.data.changed` | `data_changed` | No | Data manually updated |
| `request.invalid` | `invalid` | No | Invalid parameters |
| `request.unauthorized` | `unauthorized` | No | Auth failed |

### Webhook Workflow

```
1. ShuftiPro → POST /kyc/shuftipro/webhook
   ↓
2. Verify Signature (SHA256 double-hash)
   ↓
3. Store webhook data to DynamoDB
   ↓
4. Extract OCR data (40+ fields)
   ↓
5. If approved/declined/review → Fetch proof URLs
   ↓
6. Download proofs to MinIO/S3
   ↓
7. Update DynamoDB with proof URLs
   ↓
8. Return 200 OK to ShuftiPro
```

### Logging

**Every Webhook:**
```
INFO - Received webhook for reference: ref-xxx
INFO - Signature verified for ref-xxx
INFO - Webhook event: verification.accepted | Status: approved
INFO - User location: Toronto, Canada (IP: 2409:...)
INFO - User device: Windows 10 | Browser: Chrome 142.0
```

**With OCR Data:**
```
INFO - OCR - Name: John Doe, DOB: 1990-01-15, Doc#: ABC123456
INFO - OCR - Address: 123 Main St, Toronto, ON
```

**When Declined:**
```
WARNING - Declined reason: Document expired
WARNING - Declined codes: [1001, 1002]
```

**Proof Downloads:**
```
INFO - Fetching proof URLs from ShuftiPro API
INFO - Updated ref-xxx with proof URLs
INFO - Downloaded 4 proofs to MinIO: ['document_proof', 'verification_video', ...]
```

---

## Response Structures

### Verification Data

Complete verification data from ShuftiPro:

```json
{
  "verification_data": {
    "document": {
      "name": {
        "first_name": "John",
        "last_name": "Doe",
        "middle_name": "Carter",
        "full_name": "John Carter Doe"
      },
      "dob": "1990-01-15",
      "document_number": "ABC123456",
      "expiry_date": "2030-12-31",
      "issue_date": "2020-01-01",
      "country": "CA",
      "selected_type": ["passport"],
      "gender": "M"
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

### Additional Data

Extra OCR extracted fields (100+ fields with `fetch_enhanced_data`):

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
        "personal_number": "1234567890",
        "signature": "335,300,435,400"    // Coordinates
      }
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

### Proofs Object

Document proofs and verification media:

```json
{
  "proofs": {
    "document": {
      "proof": "https://ns.shuftipro.com/api/pea/...",
      "front": "https://ns.shuftipro.com/api/pea/...",
      "back": "https://ns.shuftipro.com/api/pea/..."
    },
    "address": {
      "proof": "https://ns.shuftipro.com/api/pea/..."
    },
    "access_token": "8a171080ef38f9c7ac5deec331d9ffa1...",
    "verification_video": "https://ns.shuftipro.com/api/pea/...",
    "verification_report": "https://ns.shuftipro.com/api/pea/..."
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

## Feature Coverage

### Core API: 100%

| Feature | Status | Endpoint |
|---------|--------|----------|
| Start Verification | ✅ | `POST /kyc/start` |
| Get Status | ✅ | `GET /kyc/status/{ref}` |
| Delete Request | ✅ | `DELETE /kyc/{ref}` |
| Account Info | ✅ | `GET /kyc/account` |
| Webhook Handler | ✅ | `POST /kyc/shuftipro/webhook` |
| List Documents | ✅ | `GET /kyc/documents/{user_id}` |
| Get Document URL | ✅ | `GET /kyc/documents/{user_id}/{filename}` |
| Test Webhook | ✅ | `POST /kyc/test-webhook` |

### Webhook Events: 100%

All 12 ShuftiPro callback events are handled and mapped to appropriate statuses.

### Response Parameters: 100%

All documented ShuftiPro response parameters are extracted and stored:
- ✅ Core verification data
- ✅ OCR fields (40+ fields)
- ✅ Additional enhanced data (100+ fields)
- ✅ User info (device, geolocation)
- ✅ Verification results
- ✅ Document proofs
- ✅ Declined reasons
- ✅ Warnings

### OCR Extraction: 100%

**Enabled by default via API payload** - no journey configuration needed!

Extracted fields:
- Name (first, middle, last, full)
- Date of birth
- Document number
- Issue/expiry dates
- Gender
- Country
- Document type
- Address (if applicable)
- 100+ enhanced fields (nationality, place of birth, height, etc.)

### Storage: 100%

| Component | Status |
|-----------|--------|
| Session Storage | ✅ DynamoDB |
| Document Storage | ✅ MinIO/S3 |
| Backup Storage | ✅ Local filesystem |
| Presigned URLs | ✅ S3 compatible |

### Security: 85%

| Feature | Status |
|---------|--------|
| Signature Verification | ✅ SHA256 double-hash |
| Vault Secrets | ✅ HashiCorp Vault |
| IP Whitelisting | 📋 Documented for production |
| TLS/HTTPS | 📋 Documented for production |

---

## Rate Limits

**Production Account:**
- 60 requests/minute per IP

**Trial Account:**
- 20 requests/minute

---

## Interactive Documentation

**Swagger UI:**
```
http://localhost:8181/docs
```

**ReDoc:**
```
http://localhost:8181/redoc
```

---

## Complete Workflow Example

```bash
# 1. Start Verification
RESPONSE=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}')

echo $RESPONSE | jq

# 2. Extract Reference and URL
REF=$(echo $RESPONSE | jq -r '.reference')
URL=$(echo $RESPONSE | jq -r '.verification_url')

echo "Reference: $REF"
echo "Verification URL: $URL"

# 3. User Completes Verification (or use test webhook)
curl -s -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF"

# 4. Check Status (with OCR data)
curl http://localhost:8181/kyc/status/$REF | jq

# 5. List Documents
USER_ID=$(echo $REF | sed 's/ref-//' | cut -d'-' -f1,2)
curl http://localhost:8181/kyc/documents/$USER_ID | jq

# 6. Get Document URL
DOC_URL=$(curl -s http://localhost:8181/kyc/documents/$USER_ID/passport_front.jpg | jq -r '.url')
echo "Document URL: $DOC_URL"

# 7. Delete (if needed)
curl -X DELETE http://localhost:8181/kyc/$REF \
  -H 'Content-Type: application/json' \
  -d '{"comment":"User requested deletion"}' | jq
```

---

**API Version:** 1.0.0  
**Last Updated:** December 2025  
**Coverage:** 100% of ShuftiPro features
