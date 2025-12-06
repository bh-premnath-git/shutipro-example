# Operational Guide

Testing, OCR configuration, proof downloads, and production deployment guide.

## Table of Contents

- [Testing](#testing)
- [OCR Configuration](#ocr-configuration)
- [Proof Downloads](#proof-downloads)
- [Production Deployment](#production-deployment)

---

## Testing

### Quick Test Commands

#### Test Account Info
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

#### Start Verification
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq
```

**Save the reference:**
```bash
REF="ref-user-1764924xxx-xxxx"  # Replace with actual reference
```

#### Test Webhook (Simulate Verification)

Instead of completing real verification, use the test webhook:

```bash
curl -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF" | jq
```

This simulates a successful verification with OCR data!

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
        "document_number": "TEST123456"
      }
    }
  }
}
```

#### Check Status (Should Show OCR Data)
```bash
curl http://localhost:8181/kyc/status/$REF | jq
```

#### List Documents
```bash
USER_ID=$(echo $REF | sed 's/ref-//' | cut -d'-' -f1,2)
curl http://localhost:8181/kyc/documents/$USER_ID | jq
```

#### Delete Verification
```bash
curl -X DELETE http://localhost:8181/kyc/$REF \
  -H 'Content-Type: application/json' \
  -d '{"comment":"Testing deletion"}' | jq
```

### Complete Test Workflow

**Full End-to-End Test Script:**

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

# 3. Simulate webhook
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

### Testing with Swagger UI

**Access Swagger:**
```
http://localhost:8181/docs
```

**Test endpoints directly in browser:**
1. POST /kyc/start - Start verification
2. POST /kyc/test-webhook - Simulate successful verification
3. GET /kyc/status/{reference} - Check status and OCR data
4. GET /kyc/account - View account info
5. GET /kyc/documents/{user_id} - List documents
6. DELETE /kyc/{reference} - Delete verification

### Testing Real Verification Flow

#### 1. Start Verification
```bash
RESPONSE=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"your-email@example.com"}')

echo $RESPONSE | jq
```

#### 2. Complete Verification in Browser
```bash
URL=$(echo $RESPONSE | jq -r '.verification_url')
echo "Complete verification at: $URL"

# Open automatically
open "$URL"  # macOS
xdg-open "$URL"  # Linux
```

#### 3. Watch Webhook Logs
```bash
docker compose logs app -f | grep -E "webhook|OCR"
```

#### 4. Check Real Webhook Data
```bash
REF=$(echo $RESPONSE | jq -r '.reference')
curl http://localhost:8181/kyc/status/$REF | jq '.raw'
```

### Testing Specific Features

#### Test OCR Extraction
```bash
curl -s http://localhost:8181/kyc/status/$REF | \
  jq '.raw.verification_data.document | {name, dob, document_number}'
```

#### Test Document Download
```bash
# List documents
curl http://localhost:8181/kyc/documents/$USER_ID | jq

# Get specific document URL
DOC_URL=$(curl -s "http://localhost:8181/kyc/documents/$USER_ID/passport_front.jpg" | jq -r '.url')

# Download document
curl -o document.jpg "$DOC_URL"
```

#### Test S3 Storage
```bash
./test_s3.sh

# Or check MinIO Console
open http://localhost:9001
# Login: minioadmin / minioadmin
```

### Logs & Debugging

#### View All Logs
```bash
docker compose logs app -f
```

#### View Webhook Logs Only
```bash
docker compose logs app -f | grep webhook
```

#### View OCR Logs Only
```bash
docker compose logs app -f | grep OCR
```

#### View Error Logs
```bash
docker compose logs app -f | grep -i error
```

---

## OCR Configuration

OCR (Optical Character Recognition) extraction is **enabled by default** via API payload - no ShuftiPro dashboard configuration needed!

### How It Works

**Default Behavior (API-Based OCR):**

When you call `/kyc/start`, the system automatically:
1. Sends OCR extraction request in API payload
2. ShuftiPro extracts all document fields via OCR
3. Webhook receives complete OCR data
4. Data logged and stored in DynamoDB

**What gets extracted:**
- Personal: Name, DOB, gender, nationality, place of birth
- Document: Type, number, issue/expiry dates, country
- Address: Full address (if address verification enabled)
- Enhanced: 100+ additional fields (height, MRZ data, etc.)

### Usage Options

#### Option 1: Default (API-Based OCR) - Recommended

```bash
# OCR enabled by default
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}' | jq
```

**Advantages:**
- ✅ No journey dependency
- ✅ Works immediately
- ✅ Full OCR extraction
- ✅ 100+ additional fields
- ✅ No dashboard configuration needed
- ✅ Consistent across all verifications

#### Option 2: Journey-Based

```bash
# Use journey configuration
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "email":"user@example.com",
    "use_journey": true,
    "journey_id": "iySLIfgD1764787557"
  }' | jq
```

**When to use:**
- Journey has custom branding/settings
- Journey has OCR already configured
- Need journey-specific configuration

#### Option 3: Disable OCR

```bash
# Basic verification without OCR
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "email":"user@example.com",
    "enable_ocr": false
  }' | jq
```

### Expected Webhook Data

With OCR enabled, webhook includes:

```json
{
  "reference": "ref-user-xxx",
  "event": "verification.accepted",
  "verification_data": {
    "document": {
      "name": {
        "first_name": "John",
        "middle_name": "Carter",
        "last_name": "Doe",
        "full_name": "John Carter Doe"
      },
      "dob": "1990-01-15",
      "document_number": "AB123456",
      "issue_date": "2020-01-01",
      "expiry_date": "2030-12-31",
      "gender": "M",
      "country": "CA"
    }
  },
  "additional_data": {
    "document": {
      "proof": {
        "height": "183",
        "nationality": "CANADIAN CITIZEN",
        "place_of_birth": "Toronto",
        "personal_number": "1234567890"
      }
    }
  }
}
```

### Verify OCR is Working

#### 1. Start Verification
```bash
REF=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq -r '.reference')
```

#### 2. Test with Test Webhook
```bash
curl -X POST "http://localhost:8181/kyc/test-webhook?reference=$REF"
```

#### 3. Check Webhook Logs
```bash
docker compose logs app -f | grep "OCR"

# Expected:
# "OCR extraction enabled in API payload"
# "OCR - Name: Test User, DOB: 1990-01-15, Doc#: TEST123456"
```

#### 4. Query Status
```bash
curl http://localhost:8181/kyc/status/$REF | jq '.raw.verification_data.document'
```

**Expected output:**
```json
{
  "name": {
    "first_name": "Test",
    "last_name": "User"
  },
  "dob": "1990-01-15",
  "document_number": "TEST123456",
  "country": "US"
}
```

### Troubleshooting OCR

#### OCR Data Shows as None

**Possible Causes:**
1. Using old journey without OCR configured
2. OCR disabled via `enable_ocr: false`
3. ShuftiPro journey overriding API payload

**Solution:**
```bash
# Ensure OCR is enabled (default)
curl -X POST http://localhost:8181/kyc/start \
  -d '{"email":"user@example.com"}' | jq

# Or explicitly enable
curl -X POST http://localhost:8181/kyc/start \
  -d '{"email":"user@example.com", "enable_ocr": true}' | jq
```

#### Partial OCR Data

**Cause:** Document type has different available fields

**Note:** Different document types extract different fields:
- **Passport**: name, DOB, document_number, expiry_date, nationality
- **ID Card**: name, DOB, document_number, expiry_date, address
- **Driver's License**: name, DOB, license_number, expiry_date, address

---

## Proof Downloads

Verification proofs (documents, videos, reports) are **automatically downloaded** when webhooks are received.

### Automatic Download Workflow

When webhook arrives with `verification.accepted`, `verification.declined`, or `review.pending`:

1. **Webhook received** with verification data
2. **Store OCR data** to DynamoDB
3. **Fetch proof URLs** from ShuftiPro API
4. **Download proofs** to MinIO/S3:
   - Document proof images
   - Address proof images
   - Verification videos
   - Verification reports
5. **Update database** with proof URLs
6. **Return success** to ShuftiPro

### Storage Structure

```
s3://kyc-documents/
  ├── {user_id}/
  │   ├── document_proof.jpg
  │   ├── address_proof.jpg
  │   ├── verification_video.mp4
  │   └── verification_report.pdf
```

### Accessing Proofs

#### Option 1: From Database (Fast)
```bash
curl http://localhost:8181/kyc/status/{reference} | jq '.raw.proofs'
```

Returns proofs stored in DynamoDB (if webhook processed successfully).

#### Option 2: From MinIO Console

1. Open http://localhost:9001
2. Login: minioadmin / minioadmin
3. Browse `kyc-documents` bucket
4. Navigate to `{user_id}` folder

#### Option 3: Via API Endpoints
```bash
# List all documents for user
curl http://localhost:8181/kyc/documents/{user_id} | jq

# Get specific document URL
curl http://localhost:8181/kyc/documents/{user_id}/document_proof.jpg | jq -r '.url'

# Download
DOC_URL=$(curl -s http://localhost:8181/kyc/documents/{user_id}/document_proof.jpg | jq -r '.url')
curl -o proof.jpg "$DOC_URL"
```

### Manual Download

If automatic download fails, manually trigger:

```bash
curl -X POST http://localhost:8181/kyc/download-proofs/{reference}
```

This will:
1. Query ShuftiPro for proof URLs
2. Download all proofs
3. Upload to MinIO
4. Return S3 keys

### Proof Authentication

Proofs use Bearer token authentication:

```bash
curl -L \
  -H "Authorization: Bearer {access_token}" \
  -o document_proof.pdf \
  "https://ns.shuftipro.com/api/pea/{proof_hash}"
```

**Status:** ✅ Automatic downloads working!

### Monitoring Downloads

```bash
docker compose logs app -f | grep -E "Fetching proof URLs|Downloaded.*proofs"
```

**Expected logs:**
```
INFO - Fetching proof URLs from ShuftiPro API for ref-user-xxx
INFO - Updated ref-user-xxx with proof URLs
INFO - Downloaded 4 proofs to MinIO: ['document_proof', 'verification_video', ...]
```

---

## Production Deployment

Complete checklist for deploying to production.

### Security

#### 1. Webhook IP Whitelisting

Whitelist ShuftiPro IPs in your firewall/security groups:

**Europe:**
- `142.132.144.101`
- `65.108.103.45`

**United States:**
- `5.161.114.110`
- `5.161.87.219`
- `5.78.56.7`
- `5.78.58.196`

**AWS Security Group Example:**
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 142.132.144.101/32
```

**nginx Example:**
```nginx
geo $shufti_ip {
    default 0;
    142.132.144.101 1;
    65.108.103.45 1;
    5.161.114.110 1;
    5.161.87.219 1;
    5.78.56.7 1;
    5.78.58.196 1;
}

server {
    location /kyc/shuftipro/webhook {
        if ($shufti_ip = 0) {
            return 403;
        }
        proxy_pass http://app:8181;
    }
}
```

#### 2. Change Default Credentials

**MinIO:**
```yaml
environment:
  MINIO_ROOT_USER: "production-user"
  MINIO_ROOT_PASSWORD: "strong-password-min-32-chars"
```

**Vault:**
- Use AppRole or AWS IAM authentication
- Never use dev mode in production
- Store unseal keys in AWS Secrets Manager

#### 3. Environment Variables

Move from `.env` to secure secrets management:

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name shuftipro/credentials \
  --secret-string '{"client_id":"xxx","secret_key":"xxx"}'

# Or HashiCorp Vault
vault kv put secret/shuftipro/prod \
  client_id=xxx \
  secret_key=xxx
```

#### 4. Enable HTTPS/TLS

**API:**
```yaml
app:
  environment:
    - FORCE_HTTPS=true
```

**MinIO:**
```yaml
minio:
  command: server /data --console-address ":9001" --certs-dir /certs
  volumes:
    - ./certs:/certs:ro
```

### Rate Limiting

**ShuftiPro Limits:**
- Production: 60 requests/minute per IP
- Trial: 20 requests/minute

**Implement Application Rate Limiting:**

```python
# requirements.txt
slowapi==0.1.9

# app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/kyc/start")
@limiter.limit("50/minute")
async def kyc_start(request: Request, body: KycStartRequest):
    # ... existing code
```

### Database

#### DynamoDB Production Table

```bash
aws dynamodb create-table \
  --table-name kyc-sessions-prod \
  --attribute-definitions AttributeName=reference,AttributeType=S \
  --key-schema AttributeName=reference,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --point-in-time-recovery-specification Enabled=true \
  --tags Key=Environment,Value=Production
```

#### Migrate to AWS S3

```yaml
environment:
  S3_ENDPOINT: ""  # Empty for AWS S3
  S3_ACCESS_KEY: "${AWS_ACCESS_KEY_ID}"
  S3_SECRET_KEY: "${AWS_SECRET_ACCESS_KEY}"
  S3_BUCKET_NAME: "kyc-documents-prod"
  AWS_REGION: "us-east-1"
  S3_FORCE_PATH_STYLE: "false"
```

**Create S3 Bucket:**
```bash
# Create bucket
aws s3 mb s3://kyc-documents-prod

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket kyc-documents-prod \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket kyc-documents-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### Infrastructure

#### DNS & Domain

**Production Callback URL:**
```
https://api.yourdomain.com/kyc/shuftipro/webhook
```

Register in ShuftiPro dashboard:
1. Login to ShuftiPro
2. Settings → Callback URLs
3. Add: `api.yourdomain.com`
4. Verify domain ownership

#### Load Balancer

**AWS Application Load Balancer:**
```bash
aws elbv2 create-target-group \
  --name kyc-api-tg \
  --protocol HTTP \
  --port 8181 \
  --vpc-id vpc-xxxxx \
  --health-check-path /health
```

#### Health Check Endpoint

Add to `app/main.py`:
```python
@app.get("/health")
async def health_check():
    """Health check for load balancer"""
    try:
        get_table()  # Check DynamoDB
        get_s3_storage()  # Check S3
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

### Monitoring

#### CloudWatch Logging

```python
import watchtower
import logging

logger = logging.getLogger(__name__)
logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group="/aws/kyc-api/prod",
    stream_name="app"
))
```

#### Key Metrics to Monitor

- Request rate to `/kyc/start`
- Webhook delivery success rate
- ShuftiPro API response times
- S3 upload success rate
- DynamoDB read/write capacity
- Error rate
- Rate limit hits

#### Set Up Alerts

- Error rate > 5%
- Response time > 2s
- Webhook signature failures
- Rate limit approaching 60/min
- S3 upload failures
- DynamoDB throttling

### Pre-Launch Checklist

- [ ] Webhook IPs whitelisted in firewall
- [ ] Changed all default credentials
- [ ] Migrated to AWS S3 from MinIO
- [ ] DynamoDB production table created
- [ ] Secrets moved to AWS Secrets Manager
- [ ] HTTPS/TLS enabled
- [ ] Rate limiting implemented
- [ ] Health check endpoint added
- [ ] CloudWatch logging configured
- [ ] Alerts set up
- [ ] Load balancer configured
- [ ] Domain registered with ShuftiPro
- [ ] Production journey configured with OCR
- [ ] CI/CD pipeline set up
- [ ] Load testing completed
- [ ] Backup strategy implemented
- [ ] Documentation updated

### Launch Day

1. Update DNS to point to production
2. Monitor CloudWatch logs
3. Check webhook deliveries
4. Verify end-to-end flow
5. Monitor error rates
6. Check ShuftiPro rate limits

### Support Contacts

**ShuftiPro:**
- Rate limit adjustments: tech@shuftipro.com
- General support: support@shuftipro.com

**AWS Support:**
- Your AWS account manager
- AWS Support Center

---

**Current Status**: Development ✅  
**Production Ready**: After checklist completion ⏳  
**Estimated Setup Time**: 2-3 days
