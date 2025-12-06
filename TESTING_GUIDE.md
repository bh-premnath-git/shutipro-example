# Testing Guide

Complete guide for testing the KYC API locally.

## 🧪 Quick Test Commands

### 1. Test Account Info
```bash
curl http://localhost:8181/kyc/account | jq
```

**Expected Response:**
```json
{
  "account": {
    "name": "Your Account",
    "status": "trial",
    "balance": {
      "amount": "85.05",
      "currency": "USD"
    }
  }
}
```

### 2. Start Verification
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq
```

**Expected Response:**
```json
{
  "reference": "ref-user-1764924xxx-xxxx",
  "provider": "shuftipro",
  "verification_url": "https://app.shuftipro.com/verification/process/...",
  "error": null,
  "status_code": null
}
```

**Save the reference for next steps:**
```bash
REF="ref-user-1764924xxx-xxxx"  # Replace with actual reference
```

### 3. Test Webhook (Simulate Verification)

Instead of completing the real verification, use the test webhook:

```bash
curl -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF" | jq
```

**This simulates a successful verification with OCR data!**

**Expected Response:**
```json
{
  "status": "success",
  "message": "Test webhook processed for ref-user-...",
  "data": {
    "reference": "ref-user-...",
    "event": "verification.accepted",
    "verification_data": {
      "document": {
        "name": {
          "first_name": "Test",
          "last_name": "User"
        },
        "dob": "1990-01-15",
        "document_number": "TEST123456",
        "expiry_date": "2030-12-31"
      }
    }
  }
}
```

### 4. Check Status (Should Show OCR Data)
```bash
curl http://localhost:8181/kyc/status/$REF | jq
```

**Expected Response:**
```json
{
  "reference": "ref-user-...",
  "provider": "shuftipro",
  "status": "approved",
  "raw": {
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

### 5. List Documents
```bash
# Extract user_id from reference
USER_ID=$(echo $REF | sed 's/ref-//' | cut -d'-' -f1,2)

curl http://localhost:8181/kyc/documents/$USER_ID | jq
```

### 6. Delete Verification
```bash
curl -X DELETE http://localhost:8181/kyc/$REF \
  -H 'Content-Type: application/json' \
  -d '{"comment":"Testing deletion"}' | jq
```

---

## 🔄 Complete Test Workflow

### Full End-to-End Test Script

```bash
#!/bin/bash

echo "=== KYC API Test ==="

# 1. Check account
echo -e "\n1. Checking account..."
curl -s http://localhost:8181/kyc/account | jq -r '.account.name, .account.balance.amount'

# 2. Start verification
echo -e "\n2. Starting verification..."
RESPONSE=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}')

REF=$(echo $RESPONSE | jq -r '.reference')
echo "Reference: $REF"

# 3. Simulate webhook (test mode)
echo -e "\n3. Simulating webhook..."
curl -s -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF" | jq -r '.status'

# 4. Check status
echo -e "\n4. Checking status..."
curl -s http://localhost:8181/kyc/status/$REF | jq '.status, .raw.verification_data.document.name'

# 5. List documents
echo -e "\n5. Listing documents..."
USER_ID=$(echo $REF | sed 's/ref-//' | cut -d'-' -f1,2)
curl -s http://localhost:8181/kyc/documents/$USER_ID | jq '.count'

echo -e "\n✅ Test complete!"
```

Save as `test_workflow.sh` and run:
```bash
chmod +x test_workflow.sh
./test_workflow.sh
```

---

## 🌐 Testing with Swagger UI

### Access Swagger
```
http://localhost:8181/docs
```

### Test Each Endpoint

**1. POST /kyc/start**
```json
{
  "email": "test@example.com"
}
```

**2. POST /kyc/test-webhook**
- Use reference from step 1
- Query parameter: `reference=ref-user-xxx`
- No body needed

**3. GET /kyc/status/{reference}**
- Path parameter: reference from step 1

**4. GET /kyc/account**
- No parameters

**5. GET /kyc/documents/{user_id}**
- Path parameter: `user-1764924xxx`

**6. DELETE /kyc/{reference}**
```json
{
  "comment": "Test deletion"
}
```

### ⚠️ Important: Webhook Endpoint

**Don't test** `/kyc/shuftipro/webhook` directly in Swagger - it expects ShuftiPro payloads.

Use `/kyc/test-webhook` instead for testing!

---

## 📊 Testing Real Verification Flow

### 1. Start Verification
```bash
RESPONSE=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"your-email@example.com"}')

echo $RESPONSE | jq
```

### 2. Complete Verification in Browser
```bash
# Get URL and open in browser
URL=$(echo $RESPONSE | jq -r '.verification_url')
echo "Complete verification at: $URL"

# Or open automatically (macOS)
open "$URL"

# Or (Linux)
xdg-open "$URL"
```

### 3. Watch Webhook Logs
```bash
# In another terminal
docker compose logs app -f | grep -E "webhook|OCR"
```

### 4. Check Real Webhook Data
After completing verification in browser:
```bash
REF=$(echo $RESPONSE | jq -r '.reference')
curl http://localhost:8181/kyc/status/$REF | jq '.raw'
```

---

## 🧪 Testing Specific Features

### Test OCR Extraction

**With Real Verification:**
1. Complete a real verification
2. Check for OCR data:
```bash
curl -s http://localhost:8181/kyc/status/$REF | \
  jq '.raw.verification_data.document | {name, dob, document_number}'
```

**With Test Webhook:**
```bash
curl -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF"
curl -s http://localhost:8181/kyc/status/$REF | \
  jq '.raw.verification_data.document | {name, dob, document_number}'
```

### Test Document Download

If real documents are provided in webhook:
```bash
# List documents
curl http://localhost:8181/kyc/documents/$USER_ID | jq

# Get specific document URL
curl "http://localhost:8181/kyc/documents/$USER_ID/passport_front.jpg" | jq -r '.url'

# Download document
DOC_URL=$(curl -s "http://localhost:8181/kyc/documents/$USER_ID/passport_front.jpg" | jq -r '.url')
curl -o document.jpg "$DOC_URL"
```

### Test S3 Storage

```bash
# Run S3 test script
./test_s3.sh

# Or manually check MinIO
open http://localhost:9001
# Login: minioadmin / minioadmin
```

### Test Different Events

**Test pending event:**
```bash
# Just start verification, don't complete it
curl -X POST http://localhost:8181/kyc/start \
  -d '{"email":"test@example.com"}' | jq

# Check status (should be "pending")
curl http://localhost:8181/kyc/status/$REF | jq '.status'
```

**Test approved event:**
```bash
# Use test webhook
curl -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF"

# Check status (should be "approved")
curl http://localhost:8181/kyc/status/$REF | jq '.status'
```

---

## 📝 Logs & Debugging

### View All Logs
```bash
docker compose logs app -f
```

### View Webhook Logs Only
```bash
docker compose logs app -f | grep webhook
```

### View OCR Logs Only
```bash
docker compose logs app -f | grep OCR
```

### View Error Logs
```bash
docker compose logs app -f | grep -i error
```

### Check Service Status
```bash
docker compose ps
```

### Restart Services
```bash
docker compose restart app
```

---

## 🔍 Common Test Scenarios

### Scenario 1: Quick Smoke Test
```bash
# Start verification
REF=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq -r '.reference')

# Simulate webhook
curl -s -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF" > /dev/null

# Check status
curl -s http://localhost:8181/kyc/status/$REF | jq '.status'
```

Expected: `"approved"`

### Scenario 2: Test Full Data Flow
```bash
# 1. Start
REF=$(curl -s -X POST http://localhost:8181/kyc/start \
  -d '{"email":"test@example.com"}' | jq -r '.reference')

# 2. Test webhook
curl -s -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF" > /dev/null

# 3. Verify OCR data
curl -s http://localhost:8181/kyc/status/$REF | \
  jq '.raw.verification_data.document.name.full_name'

# 4. List documents
USER_ID=$(echo $REF | sed 's/ref-//' | cut -d'-' -f1,2)
curl -s http://localhost:8181/kyc/documents/$USER_ID | jq '.count'
```

Expected: Name should be `"Test User"`, document count may vary

### Scenario 3: Test GDPR Deletion
```bash
# Create verification
REF=$(curl -s -X POST http://localhost:8181/kyc/start \
  -d '{"email":"test@example.com"}' | jq -r '.reference')

# Complete it
curl -s -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF" > /dev/null

# Delete it
curl -s -X DELETE http://localhost:8181/kyc/$REF \
  -H 'Content-Type: application/json' \
  -d '{"comment":"User requested deletion"}' | jq

# Verify deletion
curl -s http://localhost:8181/kyc/status/$REF | jq '.status'
```

Expected: Status should be `"deleted"`

---

## ✅ Pre-Production Checklist

Before going to production, test:

- [ ] Account info retrieval
- [ ] Start verification
- [ ] Real webhook delivery (complete actual verification)
- [ ] OCR data extraction (if journey configured)
- [ ] Document storage in S3
- [ ] Status retrieval
- [ ] Document listing
- [ ] Document URL generation
- [ ] Deletion workflow
- [ ] Error handling (invalid reference, missing data)
- [ ] Signature verification
- [ ] Rate limiting (60 requests/min)

---

## 🆘 Troubleshooting

### Test Fails: "Session not found"
**Cause:** Reference doesn't exist  
**Fix:** Start a new verification first

### Test Webhook Returns Empty OCR
**Cause:** Using real webhook endpoint instead of test endpoint  
**Fix:** Use `/kyc/test-webhook?reference=XXX` not `/kyc/shuftipro/webhook`

### Documents Not Showing
**Cause:** No documents in webhook (test webhook doesn't include document URLs)  
**Fix:** Complete a real verification to get actual documents

### "Invalid JSON" Error
**Cause:** Empty body sent to webhook endpoint  
**Fix:** Use test endpoint or send valid ShuftiPro payload

---

## 📚 Additional Resources

- **API Docs**: http://localhost:8181/docs
- **ReDoc**: http://localhost:8181/redoc
- **MinIO Console**: http://localhost:9001
- **Cloudflare Tunnel**: Run `./get_tunnel_url.sh`

**Test Scripts:**
- `./test_s3.sh` - Test MinIO/S3 storage
- `./test_api.sh` - Basic API test
- `./get_tunnel_url.sh` - Get webhook URL

---

**Happy Testing!** 🎉
