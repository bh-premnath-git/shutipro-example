# 🚀 START HERE - KYC Backend

Welcome! Your KYC backend is ready to run. Follow these steps to get started in under 5 minutes.

## ✅ What You Have

A **production-ready** backend-only KYC system with:
- ✨ **FastAPI** REST API with 3 endpoints (no frontend)
- 🔐 **HashiCorp Vault** for secure credential management
- 📦 **DynamoDB Local** for session storage with OCR data
- 🔌 **ShuftiPro** live API integration
- 🎣 **Webhook handler** with signature verification
- 📊 **OCR data extraction** (name, DOB, document number, etc.)
- 🐳 **Docker Compose** orchestration

## 🎯 Quick Start (3 Steps)

### Step 1: Get Your ShuftiPro Credentials
You need:
- `client_id` 
- `secret_key`

(If you don't have these yet, get them from [ShuftiPro](https://shuftipro.com))

### Step 2: Run Setup
```bash
cd /home/premnath/shuftipro
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

### Step 3: Test It
```bash
./test_api.sh
```

Or manually:
```bash
curl -X POST http://localhost:8080/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "user-123",
    "email": "user@example.com",
    "documentTypes": ["id_card"],
    "sides": "front_only"
  }'
```

## 🌐 Service URLs

Once running:
- **API**: http://localhost:8080
- **API Docs (Swagger)**: http://localhost:8080/docs ← **TRY THIS!**
- **Vault UI**: http://localhost:8200 (token: `root`)
- **DynamoDB Local**: http://localhost:8000

## 🔄 How It Works

```
1. You → POST /kyc/start with user details
2. Backend → Gets ShuftiPro creds from Vault
3. Backend → Calls ShuftiPro API with fetch_enhanced_data="1"
4. Backend → Saves session + OCR data to DynamoDB
5. Backend → Returns verification_url to you
6. You → Send verification_url to your user
7. User → Completes KYC on ShuftiPro's page
8. ShuftiPro → Sends webhook to /kyc/shuftipro/webhook
9. Backend → Verifies signature, extracts OCR, updates DynamoDB
10. You → Check status via GET /kyc/status/{reference}
```

## 📚 What's Included

| File/Folder | Purpose |
|-------------|---------|
| `docker-compose.yml` | Orchestrates all services |
| `app/main.py` | FastAPI endpoints |
| `app/kyc_adapter/shuftipro.py` | ShuftiPro integration |
| `app/db/dynamo.py` | DynamoDB operations |
| `app/config.py` | Vault integration |
| `Makefile` | Convenience commands |
| `README.md` | Full documentation |
| `QUICKSTART.md` | Quick reference |
| `PROJECT_OVERVIEW.md` | Architecture details |

## 🛠️ Common Commands

```bash
# View logs
make logs

# Stop services
make down

# Restart
docker compose restart app

# Clean everything (removes data)
make clean

# View running services
docker compose ps
```

## 📖 API Endpoints

### 1. Start KYC Verification
```http
POST /kyc/start
```

**Request:**
```json
{
  "user_id": "user-123",
  "email": "user@example.com",
  "documentTypes": ["passport", "id_card", "driving_license"],
  "sides": "front_back"
}
```

**Response:**
```json
{
  "reference": "ref-user-123-4567",
  "provider": "shuftipro",
  "verification_url": "https://app.shuftipro.com/verification/process/...",
  "error": null,
  "status_code": null
}
```

### 2. Check Status + OCR Data
```http
GET /kyc/status/{reference}
```

**Response:**
```json
{
  "reference": "ref-user-123-4567",
  "provider": "shuftipro",
  "status": "approved",
  "raw": {
    "document": {
      "name": {"full_name": "John Doe"},
      "dob": "1990-01-01",
      "document_number": "AB123456"
    }
  }
}
```

### 3. Webhook Handler (Auto-called by ShuftiPro)
```http
POST /kyc/shuftipro/webhook
```

**Features:**
- ✅ Signature verification
- ✅ OCR data extraction
- ✅ Status mapping
- ✅ DynamoDB updates

## 🎨 Try the Interactive Docs

Open http://localhost:8080/docs in your browser to see:
- Interactive API documentation
- Try endpoints directly in the browser
- See request/response schemas
- Test with different inputs

## 📊 View Your Data

**DynamoDB:**
```bash
# List all KYC sessions
docker exec -it dynamodb-local aws dynamodb scan \
  --table-name kyc_sessions \
  --endpoint-url http://localhost:8000 \
  --region us-east-1
```

**Vault:**
```bash
# View stored secrets
docker exec -e VAULT_TOKEN=root vault vault kv get secret/shuftipro
```

## ⚠️ Important Notes

1. **Development Mode**: This setup is for development only
   - Vault uses dev mode (not secure)
   - DynamoDB is in-memory (data lost on restart)
   - No API authentication

2. **Backend Only**: No frontend included
   - Returns URLs for users to complete KYC
   - You integrate these URLs into your app

3. **Callback URL**: Configure for webhooks (optional for testing):
   ```bash
   ./start_tunnel.sh  # Get public URL
   ./set_callback_url.sh YOUR-URL.lhr.life
   ```
   Then register domain in ShuftiPro dashboard.

## 🐛 Troubleshooting

### "Vault authentication failed"
```bash
./setup_vault.sh  # Re-run setup
```

### "Connection refused"
```bash
docker compose ps  # Check if services are running
docker compose up -d  # Start services
```

### Services won't start
```bash
docker compose down -v  # Clean everything
docker compose up --build  # Rebuild and start
```

### View detailed logs
```bash
docker compose logs -f app
docker compose logs -f vault
docker compose logs -f dynamodb-local
```

## 🚀 Next Steps

1. **Test the API** - Use Swagger UI at http://localhost:8080/docs
2. **Setup webhooks** - Follow [LOCALHOST_RUN_SETUP.md](LOCALHOST_RUN_SETUP.md) for local testing
3. **View OCR data** - Check DynamoDB for extracted document fields
4. **Integrate with your app** - Call the API from your frontend
5. **Go production** - Follow security checklist in README.md

## 📚 Documentation

- **[README.md](README.md)** - Complete system documentation
- **[SHUFTIPRO_INTEGRATION.md](SHUFTIPRO_INTEGRATION.md)** - Live API integration details
- **[OCR_DATA_FLOW.md](OCR_DATA_FLOW.md)** - How OCR data is captured and stored
- **[LOCALHOST_RUN_SETUP.md](LOCALHOST_RUN_SETUP.md)** - Webhook setup for local dev
- **[QUICKSTART.md](QUICKSTART.md)** - Quick reference guide

## 📞 Need Help?

- **Full Docs**: `README.md`
- **Quick Reference**: `QUICKSTART.md`
- **Architecture**: `PROJECT_OVERVIEW.md`
- **API Docs**: http://localhost:8080/docs (when running)

## 🎉 You're All Set!

Your KYC backend is ready. Start with:

```bash
make setup  # Setup and start everything
```

Then open http://localhost:8080/docs to explore the API!

---

**Happy Building! 🏗️**
