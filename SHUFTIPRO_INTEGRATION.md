# ShuftiPro Live Integration Guide

## ✅ Status: LIVE & WORKING

Your KYC backend is now **fully integrated with ShuftiPro's production API** at `https://api.shuftipro.com/`.

## 🎯 What's Working

- ✅ **Real API calls** to ShuftiPro
- ✅ **Live verification URLs** returned
- ✅ **Credentials** securely stored in Vault
- ✅ **Error handling** with detailed logging
- ✅ **Session storage** in DynamoDB

## 📊 Test Results

```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"real-test-user",
    "email":"test@example.com",
    "documentTypes":["passport"],
    "sides":"front_back"
  }'
```

**Response:**
```json
{
    "reference": "ref-real-test-user-3328",
    "provider": "shuftipro",
    "verification_url": "https://app.shuftipro.com/verification/process/iC3SHJKFxfNAqBsSfdSUlPPnJ31AsMCbeWIQv5Y86WLb8RGdqDPJIrduiJB56lYP",
    "error": null,
    "status_code": null
}
```

The `verification_url` is a **real ShuftiPro verification page** that users can access to complete their KYC!

## 🔄 Complete Flow

```
1. Your App → POST /kyc/start
   ↓
2. KYC Backend → Retrieves credentials from Vault
   ↓
3. KYC Backend → Calls ShuftiPro API (https://api.shuftipro.com/)
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
9. ShuftiPro → Sends webhook to callback_url (if configured)
   ↓
10. Your App → Check status via GET /kyc/status/{reference}
```

## 🔧 Configuration

### Current Setup

**Credentials:** Stored in Vault at `secret/shuftipro`
```
client_id: 161bfcd0b62b57103d3d632ad27e362d14071dab6d78346bc6d31076965b9c1e
secret_key: Ud14j6k49Wep6JGOud31bSmSh4bblLwJ
```

**API URL:** `https://api.shuftipro.com/`

**Callback URL:** Optional (currently not set)

### Adding Webhook Callbacks

To receive automatic updates when users complete verification:

1. **Register a domain in ShuftiPro dashboard:**
   - Login to [ShuftiPro](https://shuftipro.com)
   - Go to Settings → Callback URLs
   - Add your domain (e.g., `https://yourdomain.com`)

2. **Set the callback URL in docker-compose.yml:**
```yaml
environment:
  SHUFTIPRO_CALLBACK_URL: "https://yourdomain.com/kyc/shuftipro/webhook"
```

3. **Restart the app:**
```bash
docker compose up -d app
```

## 📝 API Documentation

### POST /kyc/start

**Request:**
```json
{
  "user_id": "user-123",
  "email": "user@example.com",
  "documentTypes": ["id_card", "passport", "driving_license"],
  "sides": "front_only" | "front_back"
}
```

**Supported Document Types:**
- `id_card` - National ID card
- `passport` - International passport
- `driving_license` - Driver's license
- `credit_or_debit_card` - Credit/debit card verification

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

### GET /kyc/status/{reference}

**Response:**
```json
{
  "reference": "ref-user-123-4567",
  "provider": "shuftipro",
  "status": "pending",
  "raw": { /* Full ShuftiPro response */ }
}
```

**Status Values:**
- `pending` - Verification initiated, waiting for user
- `failed` - API call failed
- `unknown` - Unexpected state

## 🔍 Logging & Debugging

The app now includes comprehensive logging:

**View logs:**
```bash
docker compose logs app -f
```

**Log levels:**
- `INFO` - Normal operations
- `WARNING` - Non-critical issues (e.g., no callback URL)
- `ERROR` - Failures and errors

**Example logs:**
```
INFO - Starting KYC verification for user: real-test-user
WARNING - No callback URL configured - webhook callbacks will not be received
INFO - Calling ShuftiPro API at https://api.shuftipro.com/
INFO - ShuftiPro API response status: 200
INFO - Verification URL obtained: https://app.shuftipro.com/...
INFO - KYC verification URL generated for user real-test-user
```

## 🎯 Testing Examples

### Test with ID Card
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"user-001",
    "email":"user001@example.com",
    "documentTypes":["id_card"],
    "sides":"front_only"
  }' | jq
```

### Test with Passport + ID Card
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"user-002",
    "email":"user002@example.com",
    "documentTypes":["passport","id_card"],
    "sides":"front_back"
  }' | jq
```

### Test with Driving License
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"user-003",
    "email":"user003@example.com",
    "documentTypes":["driving_license"],
    "sides":"front_back"
  }' | jq
```

### Check Status
```bash
# Get the reference from the start response
curl http://localhost:8181/kyc/status/ref-user-001-XXXX | jq
```

## 📱 Integration Examples

### JavaScript/React
```javascript
async function startKyc(userId, email) {
  const response = await fetch('http://localhost:8181/kyc/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      email: email,
      documentTypes: ['id_card', 'passport'],
      sides: 'front_back'
    })
  });
  
  const data = await response.json();
  
  if (data.verification_url) {
    // Redirect user to ShuftiPro
    window.location.href = data.verification_url;
    // Or open in popup/iframe
  } else {
    console.error('KYC failed:', data.error);
  }
  
  return data;
}
```

### Python
```python
import requests

def start_kyc(user_id: str, email: str):
    response = requests.post(
        'http://localhost:8181/kyc/start',
        json={
            'user_id': user_id,
            'email': email,
            'documentTypes': ['id_card', 'passport'],
            'sides': 'front_back'
        }
    )
    
    data = response.json()
    
    if data['verification_url']:
        print(f"Verification URL: {data['verification_url']}")
        # Send URL to user via email/SMS
    else:
        print(f"Error: {data['error']}")
    
    return data
```

### cURL
```bash
# Store reference
REF=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"user-123","email":"user@example.com","documentTypes":["passport"],"sides":"front_only"}' \
  | jq -r '.reference')

echo "Reference: $REF"
echo "Check status: http://localhost:8181/kyc/status/$REF"

# Later, check status
curl http://localhost:8181/kyc/status/$REF | jq
```

## 🔐 Security Notes

### Current Configuration (Development)
- ✅ Credentials stored in Vault (good)
- ✅ HTTPS to ShuftiPro API (good)
- ⚠️ Vault in dev mode (insecure for production)
- ⚠️ No API authentication (anyone can call endpoints)
- ⚠️ DynamoDB in-memory (data lost on restart)

### Production Checklist
- [ ] Use proper Vault authentication (AppRole, AWS IAM)
- [ ] Add API key/JWT authentication to endpoints
- [ ] Use AWS DynamoDB or persistent storage
- [ ] Enable HTTPS/TLS on your API
- [ ] Implement rate limiting
- [ ] Add CORS configuration
- [ ] Set up monitoring and alerting
- [ ] Configure proper callback URL
- [ ] Implement webhook signature verification
- [ ] Add audit logging

## 🚨 Common Issues

### "callback domain is not registered"
**Cause:** Callback URL not registered in ShuftiPro dashboard  
**Solution:** Remove callback URL or register it in ShuftiPro settings

### "verification_url is null"
**Cause:** API error or network issue  
**Solution:** Check `error` field in response and logs

### "Connection timeout"
**Cause:** Network issues reaching ShuftiPro  
**Solution:** Check internet connectivity, firewall rules

### "401 Unauthorized"
**Cause:** Invalid credentials  
**Solution:** Verify credentials in Vault are correct

## 📞 Support

- **ShuftiPro API Docs:** https://docs.shuftipro.com/
- **ShuftiPro Dashboard:** https://shuftipro.com/
- **API Logs:** `docker compose logs app -f`
- **Interactive API Docs:** http://localhost:8181/docs

## 🎉 Next Steps

1. **Test the verification flow** - Open a verification_url in your browser
2. **Implement webhook handler** - Receive automatic status updates
3. **Add authentication** - Secure your API endpoints
4. **Integrate with your frontend** - Send verification URLs to users
5. **Set up monitoring** - Track success/failure rates

---

**Status:** ✅ Production API Connected & Working  
**Last Updated:** 2025-12-02  
**API Version:** ShuftiPro v1
