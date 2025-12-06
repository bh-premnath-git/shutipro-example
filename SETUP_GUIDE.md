# Setup & Configuration Guide

Complete guide for setting up and configuring the KYC backend.

## Table of Contents

- [Quick Start](#quick-start)
- [Local Development Setup](#local-development-setup)
- [Webhook Configuration](#webhook-configuration)
- [MinIO/S3 Storage](#minios3-storage)
- [ShuftiPro Integration](#shuftipro-integration)
- [Configuration Reference](#configuration-reference)

---

## Quick Start

Get up and running in under 5 minutes.

### What You Need

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **ShuftiPro Account** with API credentials ([Sign up](https://shuftipro.com))
- Your ShuftiPro `client_id` and `secret_key`

### 3-Step Setup

#### Step 1: Navigate to Project
```bash
cd /home/premnath/shuftipro
```

#### Step 2: Run Setup
```bash
make setup
```

This will:
1. Start Vault
2. Ask for your ShuftiPro credentials
3. Store them securely in Vault
4. Build and start all services

**Alternative (manual)**:
```bash
./setup_vault.sh              # Configure secrets
docker compose up --build -d  # Start services
```

#### Step 3: Test It
```bash
./test_api.sh
```

Or manually:
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq
```

### Service URLs

Once running:
- **API**: http://localhost:8181
- **API Docs (Swagger)**: http://localhost:8181/docs
- **Vault UI**: http://localhost:8200 (token: `root`)
- **DynamoDB Local**: http://localhost:8000
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

### Verify Services

```bash
docker compose ps
```

Expected output:
```
NAME            STATUS
vault           Up
dynamodb-local  Up (healthy)
kyc-api         Up
minio           Up
cloudflared     Up
```

---

## Local Development Setup

### Directory Structure

```
/home/premnath/shuftipro/
├── app/                          # FastAPI application
│   ├── main.py                   # API endpoints
│   ├── config.py                 # Vault integration
│   ├── kyc_adapter/              # Provider adapters
│   └── db/                       # Database layer
├── documents/                    # Downloaded verification docs
├── docker-compose.yml            # Service orchestration
├── .env                          # Environment configuration
└── setup_vault.sh                # Vault setup script
```

### Environment Variables

Create or edit `.env` file:

```bash
# Optional: Callback URL for webhooks
# SHUFTIPRO_CALLBACK_URL=https://your-domain.com/kyc/shuftipro/webhook

# Vault Configuration
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=root

# DynamoDB Configuration
DYNAMODB_ENDPOINT=http://dynamodb-local:8000
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy

# S3/MinIO Configuration
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=kyc-documents
S3_FORCE_PATH_STYLE=true
```

### Common Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f app

# Rebuild and restart
docker compose up --build -d

# Clean everything (removes data)
docker compose down -v

# Check service status
docker compose ps
```

### Managing Vault Secrets

**View secrets:**
```bash
docker exec -e VAULT_TOKEN=root vault vault kv get secret/shuftipro
```

**Update secrets:**
```bash
docker exec -e VAULT_TOKEN=root vault vault kv put secret/shuftipro \
  client_id="YOUR_CLIENT_ID" \
  secret_key="YOUR_SECRET_KEY"
```

**Re-run setup:**
```bash
./setup_vault.sh
```

---

## Webhook Configuration

Set up webhook callbacks to receive real-time verification status updates.

### Using Cloudflare Tunnel (Development)

Cloudflare Tunnel is integrated into Docker Compose for easy webhook testing.

#### Step 1: Start Tunnel

The tunnel starts automatically with Docker Compose:
```bash
docker compose up -d
```

#### Step 2: Get Tunnel URL

```bash
./get_tunnel_url.sh
```

Or manually check logs:
```bash
docker logs cloudflared-tunnel
```

You'll see:
```
INFO | Your quick Tunnel has been created! Visit it:
https://bright-cat-8273.trycloudflare.com
```

Copy the domain: `bright-cat-8273.trycloudflare.com` (without https://)

#### Step 3: Set Callback URL

```bash
./set_callback_url.sh bright-cat-8273.trycloudflare.com
```

Or manually edit `.env`:
```bash
SHUFTIPRO_CALLBACK_URL=https://bright-cat-8273.trycloudflare.com/kyc/shuftipro/webhook
```

#### Step 4: Register in ShuftiPro

1. Login to [ShuftiPro Dashboard](https://shuftipro.com)
2. Go to Settings → Callback URLs
3. Add: `bright-cat-8273.trycloudflare.com`
4. Save

#### Step 5: Restart App

```bash
docker compose restart app
```

Verify:
```bash
docker compose logs app | grep -i callback
```

You should see:
```
INFO - Using callback URL: https://bright-cat-8273.trycloudflare.com/kyc/shuftipro/webhook
```

### Important Notes

#### URL Changes Each Restart
Each time you restart `cloudflared`, you get a new URL. You'll need to:
1. Run `./get_tunnel_url.sh`
2. Update `.env` with new URL
3. Update ShuftiPro dashboard
4. Restart app: `docker compose restart app`

#### View Tunnel Logs
```bash
docker logs -f cloudflared-tunnel
```

#### Stop Tunnel
```bash
docker compose stop cloudflared
```

### Troubleshooting Webhooks

#### "callback domain is not registered"
**Cause:** Domain not added in ShuftiPro dashboard  
**Solution:** Add domain in ShuftiPro Settings → Callback URLs

#### No webhooks received
1. Check tunnel is running:
   ```bash
   docker ps | grep cloudflared-tunnel
   ./get_tunnel_url.sh
   ```

2. Verify URL in .env:
   ```bash
   cat .env | grep SHUFTIPRO_CALLBACK_URL
   ```

3. Check app loaded it:
   ```bash
   docker exec kyc-api env | grep SHUFTIPRO_CALLBACK_URL
   ```

4. Restart if needed:
   ```bash
   docker compose restart app
   ```

---

## MinIO/S3 Storage

MinIO provides S3-compatible object storage for KYC documents.

### Architecture

```
ShuftiPro Webhook → App downloads documents
                  ↓
        ┌─────────┴──────────┐
        ↓                    ↓
    MinIO/S3          Local Backup
  (primary storage)   (/app/documents)
        ↓
    S3 keys stored
    in DynamoDB
```

### MinIO Services

**MinIO Server:**
- Port 9000: S3 API endpoint
- Port 9001: MinIO Console (web UI)
- Volume: `minio-data` (persistent storage)
- Bucket: `kyc-documents` (auto-created)

**MinIO Init:**
- Automatically creates `kyc-documents` bucket
- Sets download permissions

### Access MinIO Console

Open in browser:
- **URL**: http://localhost:9001
- **Username**: `minioadmin`
- **Password**: `minioadmin`

### Test S3 Integration

```bash
./test_s3.sh
```

This tests:
- S3 client initialization
- Bucket creation
- File upload/download
- Presigned URL generation

### API Endpoints

#### List Documents for User
```bash
GET /kyc/documents/{user_id}
```

**Example:**
```bash
curl http://localhost:8181/kyc/documents/user-123 | jq
```

**Response:**
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

#### Get Specific Document URL
```bash
GET /kyc/documents/{user_id}/{filename}?expires_in=3600
```

**Example:**
```bash
curl "http://localhost:8181/kyc/documents/user-123/passport_front.jpg" | jq
```

### AWS CLI Usage

#### Configure for MinIO
```bash
aws configure set aws_access_key_id minioadmin
aws configure set aws_secret_access_key minioadmin
aws configure set default.region us-east-1
```

#### Common Commands
```bash
# List buckets
aws --endpoint-url http://localhost:9000 s3 ls

# List objects
aws --endpoint-url http://localhost:9000 s3 ls s3://kyc-documents/

# Upload file
aws --endpoint-url http://localhost:9000 s3 cp test.txt s3://kyc-documents/test/

# Download file
aws --endpoint-url http://localhost:9000 s3 cp s3://kyc-documents/test/test.txt downloaded.txt

# Delete file
aws --endpoint-url http://localhost:9000 s3 rm s3://kyc-documents/test/test.txt
```

### Storage Structure

Documents stored with this key pattern:
```
documents/{user_id}/{document_type}.{ext}

Examples:
documents/user-1764924147/passport_front.jpg
documents/user-1764924147/passport_back.jpg
documents/user-1764924147/selfie.jpg
```

### Maintenance

#### Clear All Documents
```bash
aws --endpoint-url http://localhost:9000 s3 rm s3://kyc-documents/documents/ --recursive
```

#### Backup Bucket
```bash
aws --endpoint-url http://localhost:9000 s3 sync s3://kyc-documents ./backup-$(date +%Y%m%d)/
```

#### Reset MinIO
```bash
docker compose down
docker volume rm shuftipro_minio-data
docker compose up -d
```

---

## ShuftiPro Integration

### API Configuration

**API URL**: `https://api.shuftipro.com/`

**Credentials**: Stored in Vault at `secret/shuftipro`
- `client_id`
- `secret_key`

### Complete Flow

```
1. Your App → POST /kyc/start
   ↓
2. KYC Backend → Retrieves credentials from Vault
   ↓
3. KYC Backend → Calls ShuftiPro API
   ↓
4. ShuftiPro → Returns verification URL
   ↓
5. KYC Backend → Saves session to DynamoDB
   ↓
6. Your App ← Returns reference + verification_url
   ↓
7. User → Opens verification_url in browser
   ↓
8. User → Completes KYC on ShuftiPro's page
   ↓
9. ShuftiPro → Sends webhook to callback_url
   ↓
10. Your App → Check status via GET /kyc/status/{reference}
```

### OCR Data Extraction

OCR extraction is **enabled by default** via API payload.

**What gets extracted:**
- Personal Information: Name, DOB, gender, nationality
- Document Information: Type, number, issue/expiry dates
- Address Information: Full address
- Additional Data: 100+ enhanced fields

**API-Based OCR (Default):**
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}' | jq
```

**Journey-Based (Optional):**
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "email":"user@example.com",
    "use_journey": true,
    "journey_id": "iySLIfgD1764787557"
  }' | jq
```

### Supported Document Types

- National ID Cards
- Passports
- Driving Licenses
- Credit/Debit Cards
- Address Proof Documents

### Testing Integration

**Test Account Info:**
```bash
curl http://localhost:8181/kyc/account | jq
```

**Start Verification:**
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "email":"test@example.com",
    "user_id":"test-001"
  }' | jq
```

**Check Status:**
```bash
curl http://localhost:8181/kyc/status/ref-test-001-XXXX | jq
```

---

## Configuration Reference

### Vault Secrets

**Path:** `secret/shuftipro`

**Required Fields:**
- `client_id` - ShuftiPro client ID
- `secret_key` - ShuftiPro secret key

### Environment Variables

**Application:**
- `SHUFTIPRO_CALLBACK_URL` - Webhook callback URL (optional)

**Vault:**
- `VAULT_ADDR` - Vault server address (default: http://vault:8200)
- `VAULT_TOKEN` - Vault access token (dev: root)

**DynamoDB:**
- `DYNAMODB_ENDPOINT` - DynamoDB endpoint (default: http://dynamodb-local:8000)
- `AWS_REGION` - AWS region (default: us-east-1)
- `AWS_ACCESS_KEY_ID` - AWS access key (dev: dummy)
- `AWS_SECRET_ACCESS_KEY` - AWS secret key (dev: dummy)

**S3/MinIO:**
- `S3_ENDPOINT` - S3 endpoint (default: http://minio:9000)
- `S3_ACCESS_KEY` - S3 access key (dev: minioadmin)
- `S3_SECRET_KEY` - S3 secret key (dev: minioadmin)
- `S3_BUCKET_NAME` - S3 bucket name (default: kyc-documents)
- `S3_FORCE_PATH_STYLE` - Force path-style URLs (default: true)

### Security Notes

**Development (Current):**
- ✅ Credentials in Vault
- ✅ HTTPS to ShuftiPro API
- ⚠️ Vault in dev mode (insecure for production)
- ⚠️ No API authentication
- ⚠️ DynamoDB in-memory (data lost on restart)

**Production Requirements:**
- Use proper Vault authentication (AppRole, AWS IAM)
- Add API key/JWT authentication
- Use AWS DynamoDB or persistent storage
- Enable HTTPS/TLS on API
- Implement rate limiting
- Configure CORS
- Set up monitoring and alerting

### Troubleshooting

#### Services Won't Start
```bash
docker compose logs
docker compose down -v
docker compose up --build
```

#### Vault Authentication Failed
```bash
./setup_vault.sh
docker compose ps vault
docker exec -e VAULT_TOKEN=root vault vault kv get secret/shuftipro
```

#### Connection Refused
```bash
docker compose ps
docker compose logs app
docker compose restart
```

#### MinIO Not Accessible
```bash
docker compose logs minio
docker exec kyc-api curl -I http://minio:9000/minio/health/ready
docker exec kyc-api env | grep S3_
```

---

**Status:** ✅ Development Setup Complete  
**Next Steps:** See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for API reference
