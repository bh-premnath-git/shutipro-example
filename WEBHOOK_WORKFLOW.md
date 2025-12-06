# Webhook Workflow - Automatic Proof Fetching

## 🔄 **Complete Webhook Processing Flow**

When ShuftiPro sends a webhook callback, your system now automatically:

### **1. Receive Webhook** ✅
```
POST /kyc/shuftipro/webhook
```
- Verifies signature
- Parses JSON payload
- Extracts event type and status

### **2. Store Initial Data** ✅
```
→ DynamoDB (kyc_sessions table)
```
Stores:
- Reference
- Status
- OCR data (name, DOB, document number, etc.)
- Additional data (place of birth, MRZ, nationality, etc.)
- Verification results
- User info (geolocation, device, IP)

### **3. Fetch Proof URLs** ✅ NEW!
```
→ POST https://api.shuftipro.com/status
```
**Triggers automatically for:**
- `verification.accepted`
- `verification.declined`
- `review.pending`

Fetches:
- Document proof URLs
- Address proof URLs  
- Verification video URL
- Verification report URL
- Access token

### **4. Update Database with Proofs** ✅ NEW!
```
→ DynamoDB (update existing record)
```
Merges proof URLs into the stored webhook data:
```json
{
  "event": "verification.accepted",
  "verification_data": { ... },
  "proofs": {
    "document": {
      "proof": "https://ns.shuftipro.com/api/pea/..."
    },
    "address": {
      "proof": "https://ns.shuftipro.com/api/pea/..."
    },
    "access_token": "xxx",
    "verification_video": "https://ns.shuftipro.com/api/pea/...",
    "verification_report": "https://ns.shuftipro.com/api/pea/..."
  }
}
```

### **5. Download Proofs to MinIO** ✅ NEW!
```
→ MinIO/S3 Storage
```
**Automatically downloads:**
- Document proof images
- Address proof images
- Verification videos
- Verification reports

**Storage structure:**
```
s3://kyc-documents/
  ├── {user_id}/
  │   ├── document_proof.jpg
  │   ├── address_proof.jpg
  │   ├── verification_video.mp4
  │   └── verification_report.pdf
```

---

## 📊 **What Gets Stored in Database**

### **Before (Old Behavior)**
```json
{
  "reference": "ref-user-xxx",
  "status": "approved",
  "raw": {
    "event": "verification.accepted",
    "verification_data": { ... },
    "additional_data": { ... }
    // ❌ NO proofs
  }
}
```

### **After (New Behavior)**
```json
{
  "reference": "ref-user-xxx",
  "status": "approved",
  "raw": {
    "event": "verification.accepted",
    "verification_data": { ... },
    "additional_data": { ... },
    "proofs": {                          // ✅ Automatically added
      "document": {
        "proof": "https://..."
      },
      "address": {
        "proof": "https://..."
      },
      "access_token": "xxx",
      "verification_video": "https://...",
      "verification_report": "https://..."
    }
  }
}
```

---

## 🔍 **Query Proof URLs**

### **Option 1: From Database (Fast)**
```bash
curl http://localhost:8181/kyc/status/{reference} | jq '.raw.proofs'
```

Returns proofs stored in DynamoDB (if webhook processed successfully).

### **Option 2: From ShuftiPro API (Fresh)**
```bash
curl -X POST http://localhost:8181/kyc/query-status/{reference} | jq '.shuftipro_data.proofs'
```

Always queries ShuftiPro API for latest data.

---

## 🎯 **Events That Trigger Proof Fetching**

| Event | Proof Fetching | Download to MinIO |
|-------|----------------|-------------------|
| `request.pending` | ❌ No | ❌ No |
| `request.received` | ❌ No | ❌ No |
| `verification.accepted` | ✅ **Yes** | ✅ **Yes** |
| `verification.declined` | ✅ **Yes** | ✅ **Yes** |
| `review.pending` | ✅ **Yes** | ✅ **Yes** |
| `verification.cancelled` | ❌ No | ❌ No |
| `request.timeout` | ❌ No | ❌ No |

---

## ⚙️ **Configuration**

### **Automatic Downloads**
By default, proofs are automatically downloaded to MinIO when webhook is received.

To disable automatic downloads, modify `app/main.py`:

```python
# Line ~583: Comment out download logic
# try:
#     existing = get_kyc_session(reference)
#     if existing:
#         ...download_proof_documents...
# except Exception as e:
#     ...
```

### **Error Handling**
- If proof fetching fails: Webhook still succeeds ✅
- If MinIO download fails: Webhook still succeeds ✅
- Errors are logged but don't break the webhook flow

---

## 📝 **Logs to Monitor**

```bash
docker compose logs app -f | grep -E "Fetching proof URLs|Updated.*with proof URLs|Downloading proofs to MinIO"
```

**Expected logs:**
```
INFO - Fetching proof URLs from ShuftiPro API for ref-user-xxx
INFO - Updated ref-user-xxx with proof URLs from ShuftiPro API
INFO - Downloading proofs to MinIO for user user-xxx
INFO - Downloaded 4 proofs to MinIO: ['document_proof', 'address_proof', 'verification_video', 'verification_report']
```

---

## 🚀 **Testing the Workflow**

### **1. Start New Verification**
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq

# Save reference
REF="ref-user-xxx"
```

### **2. Complete Verification**
Open the verification URL in browser and complete it.

### **3. Check Webhook Logs**
```bash
docker compose logs app -f | grep "$REF"
```

Look for:
- ✅ "Fetching proof URLs from ShuftiPro API"
- ✅ "Updated ref-user-xxx with proof URLs"
- ✅ "Downloading proofs to MinIO"

### **4. Verify Database Has Proofs**
```bash
curl http://localhost:8181/kyc/status/$REF | jq '.raw.proofs'
```

Expected:
```json
{
  "document": {"proof": "https://..."},
  "address": {"proof": "https://..."},
  "access_token": "xxx",
  "verification_video": "https://...",
  "verification_report": "https://..."
}
```

### **5. Verify MinIO Has Files**
```bash
# List MinIO buckets
curl http://localhost:9000/kyc-documents/{user_id}/

# Or use MinIO console
http://localhost:9001
```

---

## 🎉 **Benefits**

### **Automatic Proof Storage**
✅ No manual API calls needed  
✅ Proofs stored immediately after verification  
✅ Available in database for quick access  
✅ Backed up to S3/MinIO automatically

### **Complete Audit Trail**
✅ All verification data in one place  
✅ Proof URLs never expire from database  
✅ Local backup in MinIO if ShuftiPro URLs expire

### **Error Resilient**
✅ Webhook succeeds even if proof download fails  
✅ Can retry downloads later if needed  
✅ Manual download endpoint still available

---

## 🔧 **Manual Proof Download**

If automatic download fails, you can manually trigger:

```bash
curl -X POST http://localhost:8181/kyc/download-proofs/{reference}
```

This will:
1. Query ShuftiPro for proof URLs
2. Download all proofs
3. Upload to MinIO
4. Return S3 keys

---

## 📊 **API Endpoints Summary**

| Endpoint | Purpose | Proof URLs |
|----------|---------|------------|
| `POST /kyc/shuftipro/webhook` | Receive webhook | Fetches automatically |
| `GET /kyc/status/{ref}` | Get from database | ✅ Included |
| `POST /kyc/query-status/{ref}` | Query ShuftiPro | ✅ Included |
| `POST /kyc/download-proofs/{ref}` | Manual download | Downloads to MinIO |

---

## ✅ **Summary**

**Old Workflow:**
1. Webhook → Store OCR data
2. ❌ Missing proof URLs
3. Manual query needed

**New Workflow:**
1. Webhook → Store OCR data
2. ✅ **Auto-fetch proof URLs from ShuftiPro**
3. ✅ **Update database with proofs**
4. ✅ **Download to MinIO automatically**
5. Done! Everything in one place 🎉
