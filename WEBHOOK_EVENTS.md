# ShuftiPro Webhook Events Coverage

Complete coverage of all ShuftiPro webhook events and response parameters.

## ✅ Events Coverage

### Callback Events (Received via Webhook)

| Event | Status Mapped | Logged | Notes |
|-------|---------------|--------|-------|
| `request.pending` | ✅ `pending` | ✅ | Request valid, URL generated |
| `request.received` | ✅ `pending` | ✅ | Request received |
| `verification.accepted` | ✅ `approved` | ✅ | Verification passed |
| `verification.declined` | ✅ `declined` | ✅ | Verification failed |
| `verification.cancelled` | ✅ `cancelled` | ✅ | User cancelled |
| `request.timeout` | ✅ `timeout` | ✅ | 60min timeout |
| `review.pending` | ✅ `review_pending` | ✅ | Manual review required |
| `verification.status.changed` | ✅ `status_changed` | ✅ | Status updated |
| `request.deleted` | ✅ `deleted` | ✅ | Request deleted |
| `request.data.changed` | ✅ `data_changed` | ✅ | Data manually updated |

### HTTP-Only Events (Not in Callback)

| Event | Status Mapped | Notes |
|-------|---------------|-------|
| `request.invalid` | ✅ `invalid` | Invalid request parameters |
| `request.unauthorized` | ✅ `unauthorized` | Auth header invalid |

**All 12 ShuftiPro events are handled!** ✅

## 📊 Response Parameters Extracted

### Core Parameters

| Parameter | Extracted | Logged | Stored |
|-----------|-----------|--------|--------|
| `reference` | ✅ | ✅ | ✅ DynamoDB |
| `event` | ✅ | ✅ | ✅ DynamoDB |
| `email` | ✅ | ✅ | ✅ DynamoDB |
| `verification_url` | ✅ | ✅ | ✅ DynamoDB |
| `country` | ✅ | ❌ | ✅ DynamoDB |
| `error` | ✅ | ✅ | ✅ DynamoDB |

### Verification Data

| Parameter | Extracted | Logged | Stored |
|-----------|-----------|--------|--------|
| `verification_data` | ✅ | ✅ | ✅ DynamoDB |
| `verification_data.document.name` | ✅ | ✅ | ✅ DynamoDB |
| `verification_data.document.dob` | ✅ | ✅ | ✅ DynamoDB |
| `verification_data.document.document_number` | ✅ | ✅ | ✅ DynamoDB |
| `verification_data.document.country` | ✅ | ✅ | ✅ DynamoDB |
| `verification_data.document.selected_type` | ✅ | ✅ | ✅ DynamoDB |
| `verification_data.address` | ✅ | ✅ | ✅ DynamoDB |

### Verification Result

| Parameter | Extracted | Stored |
|-----------|-----------|--------|
| `verification_result` | ✅ | ✅ DynamoDB |
| `verification_result.document.*` | ✅ | ✅ DynamoDB |

### Additional Data

| Parameter | Extracted | Logged | Stored |
|-----------|-----------|--------|--------|
| `additional_data` | ✅ | ✅ | ✅ DynamoDB |
| All nested fields | ✅ | ✅ | ✅ DynamoDB |

### Info Object

| Parameter | Extracted | Logged | Stored |
|-----------|-----------|--------|--------|
| `info.agent` | ✅ | ✅ | ✅ DynamoDB |
| `info.agent.useragent` | ✅ | ❌ | ✅ DynamoDB |
| `info.agent.device_name` | ✅ | ✅ | ✅ DynamoDB |
| `info.agent.browser_name` | ✅ | ✅ | ✅ DynamoDB |
| `info.geolocation` | ✅ | ✅ | ✅ DynamoDB |
| `info.geolocation.ip` | ✅ | ✅ | ✅ DynamoDB |
| `info.geolocation.city` | ✅ | ✅ | ✅ DynamoDB |
| `info.geolocation.country_name` | ✅ | ✅ | ✅ DynamoDB |

### Declined Verification

| Parameter | Extracted | Logged | Stored |
|-----------|-----------|--------|--------|
| `declined_reason` | ✅ | ✅ | ✅ DynamoDB |
| `declined_codes` | ✅ | ✅ | ✅ DynamoDB |
| `services_declined_codes` | ✅ | ✅ | ✅ DynamoDB |

### Anomalies & Warnings

| Parameter | Extracted | Logged | Stored |
|-----------|-----------|--------|--------|
| `warnings` | ✅ | ✅ | ✅ DynamoDB |

### Document Proofs/Images

| Parameter | Extracted | Downloaded | Stored |
|-----------|-----------|------------|--------|
| `proofs` | ✅ | ✅ | ✅ MinIO/S3 |
| `proofs.document.front` | ✅ | ✅ | ✅ MinIO/S3 |
| `proofs.document.back` | ✅ | ✅ | ✅ MinIO/S3 |
| `proofs.face` | ✅ | ✅ | ✅ MinIO/S3 |

## 🔍 Logging Details

### What Gets Logged

**Every Webhook:**
```
INFO - Received webhook for reference: ref-xxx
INFO - Signature verified for ref-xxx
INFO - Webhook event: verification.accepted | Status: approved | Reference: ref-xxx
INFO - User location: Chhindwara, India (IP: 2409:40f4...)
INFO - User device: Windows NT 10.0 | Browser: Chrome 142.0.0.0
```

**When OCR Data Present:**
```
INFO - OCR - Name: John Doe (John Doe), DOB: 1990-01-15, Doc#: ABC123456
INFO - OCR - Address: 123 Main St, Toronto, ON
```

**When OCR Data Missing:**
```
WARNING - No OCR data in webhook - Journey may not be configured for data extraction
INFO - See ENABLE_OCR_GUIDE.md for setup instructions
```

**When Verification Declined:**
```
WARNING - Declined reason: Document expired
WARNING - Declined codes: [1001, 1002]
WARNING - Service-specific declined codes: {"document": [1001], "face": [2003]}
```

**When Anomalies Detected:**
```
WARNING - Anomalies detected: {"metadata_altered": true, "image_manipulated": false}
```

**When Documents Downloaded:**
```
INFO - Uploaded document_front for user user-xxx to S3: documents/user-xxx/document_front.jpg
INFO - Uploaded document_back for user user-xxx to S3: documents/user-xxx/document_back.jpg
```

## 📋 Event Flow Examples

### Successful Verification Flow

```
1. POST /kyc/start → verification_url generated
   ↓
2. Webhook: request.pending
   Log: "Webhook event: request.pending | Status: pending"
   ↓
3. User completes verification
   ↓
4. Webhook: verification.accepted
   Log: "Webhook event: verification.accepted | Status: approved"
   Log: "OCR - Name: John Doe, DOB: 1990-01-15, Doc#: ABC123"
   Log: "User location: Toronto, Canada"
   Log: "Uploaded document_front to S3: documents/user-xxx/passport_front.jpg"
   ↓
5. GET /kyc/status/ref-xxx → returns full verification data
```

### Declined Verification Flow

```
1. POST /kyc/start → verification_url generated
   ↓
2. Webhook: request.pending
   ↓
3. User submits invalid/expired document
   ↓
4. Webhook: verification.declined
   Log: "Webhook event: verification.declined | Status: declined"
   Log: "Declined reason: Document expired"
   Log: "Declined codes: [1001]"
   ↓
5. GET /kyc/status/ref-xxx → returns declined status with reason
```

### Manual Review Flow

```
1. POST /kyc/start
   ↓
2. Webhook: request.pending
   ↓
3. User submits borderline document
   ↓
4. Webhook: review.pending
   Log: "Webhook event: review.pending | Status: review_pending"
   ↓
5. Manual review by ShuftiPro team
   ↓
6. Webhook: verification.status.changed
   Log: "Verification status changed to: approved"
   ↓
7. Webhook: verification.accepted
```

## 🧪 Testing All Events

### Test request.pending
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq

# Check logs immediately
docker compose logs app -f | grep "request.pending"
```

### Test verification.accepted
```bash
# Complete the verification URL in browser with valid document
# Watch logs
docker compose logs app -f | grep "verification.accepted"
```

### Test verification.declined
```bash
# Complete verification with invalid/expired document
docker compose logs app -f | grep "verification.declined"
```

### Test verification.cancelled
```bash
# Start verification but disagree to terms
docker compose logs app -f | grep "verification.cancelled"
```

### Test request.timeout
```bash
# Start verification but don't complete within 60 minutes
# After 60 min:
docker compose logs app -f | grep "request.timeout"
```

## 📚 Related Documentation

- **OCR Setup**: `ENABLE_OCR_GUIDE.md`
- **Webhook Setup**: `LOCALHOST_RUN_SETUP.md`
- **Integration Guide**: `SHUFTIPRO_INTEGRATION.md`
- **MinIO/S3 Setup**: `MINIO_S3_SETUP.md`

## 🎯 Summary

**Event Coverage**: ✅ 12/12 events (100%)  
**Parameter Extraction**: ✅ All documented parameters  
**Logging**: ✅ Comprehensive with context  
**Storage**: ✅ DynamoDB + MinIO/S3  
**Error Handling**: ✅ Declined reasons, warnings  

Your webhook handler is **production-ready** and handles all ShuftiPro events! 🚀
