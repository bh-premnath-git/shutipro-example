# ShuftiPro KYC Backend

A production-ready KYC (Know Your Customer) verification backend built with FastAPI, integrated with ShuftiPro's API for identity verification and document OCR.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Development](#development)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

## Overview

This is a backend-only KYC verification system that integrates with ShuftiPro's identity verification API. It provides RESTful endpoints for initiating KYC verifications, receiving webhook callbacks, and querying verification status with OCR data.

### Key Capabilities

- **Identity Verification**: Multi-document KYC verification (ID cards, passports, driving licenses)
- **OCR Data Extraction**: Automatic extraction of name, DOB, document numbers, addresses, and more
- **Document Management**: Automatic download and storage of verification documents
- **Secure Credential Storage**: HashiCorp Vault integration for API credentials
- **Persistent Storage**: DynamoDB for session and OCR data storage
- **Webhook Support**: Real-time verification status updates via webhooks
- **Signature Verification**: Cryptographic verification of ShuftiPro webhook callbacks

## Features

### Core Functionality

- ✅ **FastAPI REST API** - Modern, async Python web framework
- ✅ **ShuftiPro Integration** - Live API integration with `https://api.shuftipro.com/`
- ✅ **Vault Security** - Secure credential management with HashiCorp Vault
- ✅ **DynamoDB Storage** - Session and OCR data persistence
- ✅ **Webhook Handler** - Automatic status updates with signature verification
- ✅ **OCR Extraction** - Parse and normalize document fields (40+ fields supported)
- ✅ **Document Download** - Automatic download of verification documents
- ✅ **Docker Compose** - Easy local development setup
- ✅ **Interactive API Docs** - Swagger UI at `/docs`

### Supported Document Types

- National ID Cards
- Passports
- Driving Licenses
- Credit/Debit Cards
- Address Proof Documents

### Extracted OCR Fields

**Personal Information:**
- First name, last name, full name
- Date of birth
- Gender
- Nationality
- Place of birth

**Document Information:**
- Document type
- Document number
- Issue date
- Expiry date
- Country of issue

**Address Information:**
- Full address
- City, state, postal code
- Country

**Additional Data:**
- Email, phone number
- Height
- Geolocation
- Document images (front, back, photo)
- Face/selfie image

## Architecture

```
┌─────────────────┐
│   Your App      │
│   (Frontend)    │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────────────────┐
│  KYC Backend (FastAPI)                              │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │   Endpoints  │  │  Webhook     │  │  Config  │ │
│  │  /kyc/start  │  │  Handler     │  │  (Vault) │ │
│  │  /kyc/status │  │  /webhook    │  │          │ │
│  └──────┬───────┘  └──────┬───────┘  └────┬─────┘ │
│         │                 │                │       │
│         └─────────┬───────┘                │       │
│                   ↓                        ↓       │
│         ┌──────────────────┐    ┌─────────────┐   │
│         │  ShuftiPro       │    │  HashiCorp  │   │
│         │  Adapter         │    │  Vault      │   │
│         └─────────┬────────┘    └─────────────┘   │
│                   │                                │
└───────────────────┼────────────────────────────────┘
                    │
         ┌──────────┼──────────┐
         ↓                     ↓
┌─────────────────┐   ┌────────────────┐
│  ShuftiPro API  │   │   DynamoDB     │
│  (External)     │   │   (Storage)    │
└─────────────────┘   └────────────────┘
```

### Components

1. **FastAPI Application** (`app/main.py`)
   - REST API endpoints
   - Request/response models
   - Webhook handler with signature verification

2. **KYC Adapter** (`app/kyc_adapter/`)
   - Abstract base class for KYC providers
   - ShuftiPro implementation with API client
   - Extensible for additional providers

3. **Database Layer** (`app/db/dynamo.py`)
   - DynamoDB operations
   - OCR field extraction (40+ fields)
   - Document download and storage

4. **Configuration** (`app/config.py`)
   - Vault integration
   - Credential management
   - Environment configuration

5. **Infrastructure** (`docker-compose.yml`)
   - HashiCorp Vault (dev mode)
   - DynamoDB Local
   - FastAPI application container

## Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **ShuftiPro Account** with API credentials ([Sign up](https://shuftipro.com))
- **Linux/macOS** or Windows with WSL2

## Quick Start

### 1. Clone and Navigate

```bash
cd /home/premnath/shuftipro
```

### 2. Setup Vault and Credentials

Run the setup script to configure Vault with your ShuftiPro credentials:

```bash
./setup_vault.sh
```

You'll be prompted to enter:
- ShuftiPro Client ID
- ShuftiPro Secret Key

### 3. Start All Services

```bash
docker compose up --build -d
```

This starts:
- **Vault** on port 8200
- **DynamoDB Local** on port 8000
- **KYC API** on port 8181 (using 8181 instead of 8080 to avoid conflicts with nginx)

### 4. Verify Services

```bash
docker compose ps
```

Expected output:
```
NAME            STATUS
vault           Up
dynamodb-local  Up (healthy)
kyc-api         Up
```

### 5. Test the API

```bash
./test_api.sh
```

Or manually:
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test-user-001",
    "email": "test@example.com",
    "journey_id": "default"
  }'
```

### 6. Access Interactive Docs

Open [http://localhost:8181/docs](http://localhost:8181/docs) in your browser to explore the API with Swagger UI.

## API Documentation

### Base URL

```
http://localhost:8181
```

### Endpoints

#### 1. Start KYC Verification

**`POST /kyc/start`**

Initiate a KYC verification session.

**Request:**
```json
{
  "user_id": "user-123",
  "email": "user@example.com",
  "journey_id": "default"
}
```

**Response (Success):**
```json
{
  "reference": "ref-user-123-4567",
  "provider": "shuftipro",
  "verification_url": "https://app.shuftipro.com/verification/process/...",
  "error": null,
  "status_code": null
}
```

**Response (Error):**
```json
{
  "reference": "ref-user-123-4567",
  "provider": "shuftipro",
  "verification_url": null,
  "error": "The given callback domain is not registered",
  "status_code": 400
}
```

#### 2. Check Verification Status

**`GET /kyc/status/{reference}`**

Retrieve the current status and OCR data for a verification session.

**Response:**
```json
{
  "reference": "ref-user-123-4567",
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
        "dob": "1990-01-01",
        "document_number": "AB123456",
        "expiry_date": "2030-12-31",
        "country": "US"
      }
    }
  }
}
```

**Status Values:**
- `pending` - Verification initiated, waiting for user
- `approved` - Verification accepted
- `declined` - Verification declined
- `cancelled` - User cancelled verification
- `review_pending` - Under manual review
- `timeout` - Verification timed out
- `failed` - API call failed
- `unknown` - Unexpected state

#### 3. Webhook Handler

**`POST /kyc/shuftipro/webhook`**

Receives callbacks from ShuftiPro with verification results. This endpoint is called automatically by ShuftiPro - you don't need to call it directly.

**Features:**
- ✅ Signature verification for security
- ✅ Status mapping from ShuftiPro events
- ✅ OCR data extraction and normalization
- ✅ Automatic document download
- ✅ DynamoDB updates

**Supported Events:**
- `verification.accepted` → `approved`
- `verification.declined` → `declined`
- `verification.cancelled` → `cancelled`
- `review.pending` → `review_pending`
- `request.pending` → `pending`
- `request.timeout` → `timeout`

## Configuration

### Environment Variables

Create or edit `.env` file in the project root:

```bash
# Optional: Callback URL for webhooks
# SHUFTIPRO_CALLBACK_URL=https://your-domain.com/kyc/shuftipro/webhook

# Vault Configuration (set in docker-compose.yml)
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=root

# DynamoDB Configuration
DYNAMODB_ENDPOINT=http://dynamodb-local:8000
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
```

### Vault Secrets

ShuftiPro credentials are stored in Vault at `secret/shuftipro`:

```bash
# View secrets
docker exec -e VAULT_TOKEN=root vault vault kv get secret/shuftipro

# Update secrets
docker exec -e VAULT_TOKEN=root vault vault kv put secret/shuftipro \
  client_id="YOUR_CLIENT_ID" \
  secret_key="YOUR_SECRET_KEY"
```

### Webhook Configuration (Optional)

For local development with webhooks:

1. **Start tunnel (integrated into Docker Compose):**
   ```bash
   docker compose up -d cloudflared
   ```

2. **Get tunnel URL:**
   ```bash
   ./get_tunnel_url.sh
   ```

3. **Set callback URL:**
   ```bash
   ./set_callback_url.sh YOUR-URL.trycloudflare.com
   ```

4. **Register domain in ShuftiPro:**
   - Login to [ShuftiPro Dashboard](https://shuftipro.com)
   - Go to Settings → Callback URLs
   - Add your domain

5. **Restart app:**
   ```bash
   docker compose restart app
   ```

See [LOCALHOST_RUN_SETUP.md](LOCALHOST_RUN_SETUP.md) for detailed webhook setup with Cloudflare Tunnel.

## Development

### Project Structure

```
/home/premnath/shuftipro/
├── app/                          # FastAPI application
│   ├── main.py                   # API endpoints and webhook handler
│   ├── config.py                 # Vault integration
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile                # App container image
│   ├── kyc_adapter/              # KYC provider adapters
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract base class
│   │   └── shuftipro.py          # ShuftiPro implementation
│   └── db/                       # Database layer
│       ├── __init__.py
│       └── dynamo.py             # DynamoDB operations & OCR extraction
├── app_scripts/                  # Initialization scripts
│   └── init_dynamodb.sh          # DynamoDB table creation
├── documents/                    # Downloaded verification documents
├── docker-compose.yml            # Service orchestration
├── .env                          # Environment configuration
├── .gitignore                    # Git ignore rules
├── setup_vault.sh                # Vault setup script
├── test_api.sh                   # API testing script
├── start_tunnel.sh               # Cloudflare Tunnel helper
├── get_tunnel_url.sh             # Extract tunnel URL from logs
├── set_callback_url.sh           # Configure callback URL
├── README.md                     # This file
├── START_HERE.md                 # Quick start guide
├── SHUFTIPRO_INTEGRATION.md      # Integration details
└── LOCALHOST_RUN_SETUP.md        # Webhook setup guide
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

# Restart single service
docker compose restart app

# Clean everything (removes volumes)
docker compose down -v

# Check service status
docker compose ps

# Execute command in container
docker compose exec app bash
```

### Adding New KYC Providers

1. Create new adapter in `app/kyc_adapter/`:
   ```python
   from .base import KYCProvider
   
   class NewProviderAdapter(KYCProvider):
       async def start_verification(self, payload):
           # Implementation
           pass
   ```

2. Update `app/kyc_adapter/__init__.py`

3. Add provider configuration in `app/config.py`

### Database Schema

**DynamoDB Table:** `kyc_sessions`

**Primary Key:** `reference` (String)

**Attributes:**
```python
{
    "reference": "ref-user-123-4567",      # Primary key
    "user_id": "user-123",                 # User identifier
    "provider": "shuftipro",               # KYC provider name
    "status": "approved",                  # Verification status
    "updated_at": "2024-12-05T...",        # Last update timestamp
    "raw": { ... },                        # Full ShuftiPro response
    "fields": {                            # Extracted OCR fields
        "first_name": "John",
        "last_name": "Doe",
        "dob": "1990-01-01",
        "document_number": "AB123456",
        "document_urls": {
            "document_front": "https://...",
            "document_back": "https://...",
            "face_photo": "https://..."
        },
        // ... 40+ more fields
    }
}
```

### Testing

#### Unit Testing

```bash
# Run tests (when implemented)
docker compose exec app pytest
```

#### Manual Testing

```bash
# Test start endpoint
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"test","email":"test@example.com","journey_id":"default"}'

# Test status endpoint
curl http://localhost:8181/kyc/status/ref-test-1234

# View DynamoDB data
docker exec -it dynamodb-local aws dynamodb scan \
  --table-name kyc_sessions \
  --endpoint-url http://localhost:8000 \
  --region us-east-1
```

## Production Deployment

### Security Checklist

- [ ] **Use production Vault** - Replace dev mode Vault with proper Vault cluster
- [ ] **Enable API authentication** - Add JWT/API key authentication to endpoints
- [ ] **Use AWS DynamoDB** - Replace local DynamoDB with AWS DynamoDB
- [ ] **Enable HTTPS/TLS** - Use reverse proxy (nginx) with SSL certificates
- [ ] **Configure CORS** - Set proper CORS policies for frontend integration
- [ ] **Implement rate limiting** - Protect against abuse
- [ ] **Add monitoring** - Set up logging, metrics, and alerting
- [ ] **Configure webhooks properly** - Use production domain and verify signatures
- [ ] **Enable audit logging** - Log all KYC operations
- [ ] **Secure environment variables** - Use secrets management (AWS Secrets Manager, etc.)
- [ ] **Set up backup** - Regular DynamoDB backups
- [ ] **Configure auto-scaling** - Handle variable load

### Production Configuration

**Vault:**
```bash
# Use AppRole authentication
export VAULT_ADDR=https://vault.yourcompany.com
export VAULT_ROLE_ID=...
export VAULT_SECRET_ID=...
```

**DynamoDB:**
```python
# Use AWS DynamoDB
DYNAMODB_ENDPOINT=  # Empty for AWS
AWS_REGION=us-east-1
# Use IAM roles instead of access keys
```

**API Configuration:**
```yaml
# Add authentication middleware
# Add rate limiting
# Enable HTTPS
# Configure production logging
```

### Deployment Options

1. **AWS ECS/Fargate**
   - Deploy containers to AWS
   - Use AWS DynamoDB
   - Use AWS Secrets Manager
   - ALB for load balancing

2. **Kubernetes**
   - Deploy to EKS, GKE, or AKS
   - Use Vault operator
   - External Secrets Operator
   - Ingress for HTTPS

3. **Traditional VMs**
   - Deploy with systemd
   - Use external Vault
   - Configure nginx reverse proxy

## Troubleshooting

### Services Won't Start

**Problem:** Docker containers fail to start

**Solution:**
```bash
# Check logs
docker compose logs

# Clean and rebuild
docker compose down -v
docker compose up --build
```

### Vault Authentication Failed

**Problem:** `RuntimeError: Vault authentication failed`

**Solution:**
```bash
# Re-run Vault setup
./setup_vault.sh

# Verify Vault is running
docker compose ps vault

# Check Vault secrets
docker exec -e VAULT_TOKEN=root vault vault kv get secret/shuftipro
```

### Connection Refused

**Problem:** Cannot connect to API

**Solution:**
```bash
# Check if services are running
docker compose ps

# Check API logs
docker compose logs app

# Restart services
docker compose restart
```

### Webhook Not Receiving Callbacks

**Problem:** Webhooks not being received

**Solution:**
1. **Verify tunnel is running:**
   ```bash
   docker ps | grep cloudflared-tunnel
   ```
   
   Or get the URL:
   ```bash
   ./get_tunnel_url.sh
   ```

2. **Check callback URL:**
   ```bash
   docker compose logs app | grep -i callback
   ```

3. **Verify domain registration:**
   - Check ShuftiPro dashboard
   - Ensure domain matches tunnel URL

4. **Test webhook manually:**
   ```bash
   curl -X POST http://localhost:8181/kyc/shuftipro/webhook \
     -H 'Content-Type: application/json' \
     -d '{"reference":"test","event":"verification.accepted"}'
   ```

### ShuftiPro API Errors

**Problem:** `callback domain is not registered`

**Solution:** Register your callback domain in ShuftiPro dashboard or remove the callback URL to test without webhooks.

**Problem:** `401 Unauthorized`

**Solution:** Verify credentials in Vault are correct.

**Problem:** `Connection timeout`

**Solution:** Check internet connectivity and firewall rules.

### DynamoDB Issues

**Problem:** Cannot access DynamoDB

**Solution:**
```bash
# Check DynamoDB health
docker compose ps dynamodb-local

# Test DynamoDB connection
docker exec -it dynamodb-local aws dynamodb list-tables \
  --endpoint-url http://localhost:8000 \
  --region us-east-1
```

### Performance Issues

**Problem:** Slow API response

**Solution:**
- Check ShuftiPro API response times in logs
- Monitor container resource usage: `docker stats`
- Scale up container resources in docker-compose.yml

## Additional Documentation

- **[START_HERE.md](START_HERE.md)** - Quick start guide and overview
- **[SHUFTIPRO_INTEGRATION.md](SHUFTIPRO_INTEGRATION.md)** - Detailed ShuftiPro integration guide
- **[LOCALHOST_RUN_SETUP.md](LOCALHOST_RUN_SETUP.md)** - Local webhook setup with Cloudflare Tunnel (cloudflared)
- **[API Docs (Swagger)](http://localhost:8181/docs)** - Interactive API documentation (when running)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is proprietary software. All rights reserved.

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review the additional documentation
- Check ShuftiPro [API Documentation](https://docs.shuftipro.com/)
- Review application logs: `docker compose logs -f app`

---

**Built with ❤️ using FastAPI, ShuftiPro, Vault, and DynamoDB**
