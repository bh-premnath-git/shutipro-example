# Quick Start - Testing Proof Downloads

## The Fix
✅ **Fixed**: Proof download authentication now uses POST with access_token in JSON body  
✅ **Fixed**: Now handles ALL proof types (document, address, video, report, etc.)

## Quick Test

### 1. Start the Services
```bash
cd /home/premnath/shuftipro
docker-compose up -d
```

### 2. Option A: Test with Existing Proof Data
If you have proof URLs from a previous verification:

```bash
docker exec -it kyc-api python /home/premnath/shuftipro/download_proofs_now.py
```

Expected output:
```
Found 4 proof URLs to download: ['document_proof', 'address_proof', 'verification_video', 'verification_report']
Downloading document_proof for user user-1764934158 from https://ns.shuftipro.com/api/pea/...
Downloaded document_proof: 45231 bytes, type: image/jpeg
...
✅ Downloaded 4 files:
  - document_proof: documents/user-1764934158/document_proof.jpg
  - address_proof: documents/user-1764934158/address_proof.jpg
  - verification_video: documents/user-1764934158/verification_video.mp4
  - verification_report: documents/user-1764934158/verification_report.pdf
```

### 2. Option B: Test with Live Verification

#### Step 1: Start a verification
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "journey_id": "your_journey_id"
  }'
```

Save the `reference` from the response.

#### Step 2: Complete the verification
Visit the `verification_url` from the response and complete the verification through Shuftipro.

#### Step 3: Download the proofs
```bash
# Replace {reference} with your actual reference
curl -X POST http://localhost:8181/kyc/download-proofs/{reference}
```

Response:
```json
{
  "reference": "ref-user-1234567890-abcd",
  "user_id": "user-1234567890",
  "downloaded": {
    "document_proof": "documents/user-1234567890/document_proof.jpg",
    "address_proof": "documents/user-1234567890/address_proof.jpg",
    "verification_video": "documents/user-1234567890/verification_video.mp4",
    "verification_report": "documents/user-1234567890/verification_report.pdf"
  },
  "count": 4,
  "message": "Successfully downloaded 4 proof files to MinIO"
}
```

### 3. Verify Files in MinIO

Access MinIO console:
```
http://localhost:9001
```

Login:
- Username: `minioadmin`
- Password: `minioadmin`

Check the `kyc-documents` bucket for downloaded files.

## What Changed

### Before (Broken)
```python
# ❌ Wrong: GET request with Bearer token
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.get(url, headers=headers)

# ❌ Only handled 3 hardcoded proof types
urls_to_download["document_proof"] = proofs["document"]["proof"]
urls_to_download["verification_video"] = proofs["verification_video"]
urls_to_download["verification_report"] = proofs["verification_report"]
```

### After (Fixed)
```python
# ✅ Correct: POST request with access_token in body
payload = {"access_token": access_token}
response = await client.post(url, json=payload)

# ✅ Dynamically handles ALL proof types
for key, value in proofs.items():
    if isinstance(value, dict) and "proof" in value:
        urls_to_download[f"{key}_proof"] = value["proof"]
    elif isinstance(value, str) and value.startswith("http"):
        urls_to_download[key] = value
```

## Supported Proof Types (All Automatically Detected)

- ✅ `document.proof` - Document verification image
- ✅ `address.proof` - Address verification document (**NOW WORKS!**)
- ✅ `verification_video` - Liveness video
- ✅ `verification_report` - Verification PDF report
- ✅ Any future proof types Shuftipro adds

## Troubleshooting

### Issue: "Failed to download proofs"
**Check**: Access token and proof URLs are only valid for 15 minutes
**Solution**: Query the status endpoint again to get fresh URLs

### Issue: "No access_token found"
**Check**: The verification must be completed (status: verification.accepted or verification.declined)
**Solution**: Wait for the webhook or query the status endpoint after completion

### Issue: Files not in MinIO
**Check**: MinIO service is running
```bash
docker ps | grep minio
```

**Check**: MinIO bucket exists
```bash
docker exec -it minio-init mc ls local/
```

## Files Changed

- `/home/premnath/shuftipro/app/db/dynamo.py` - Fixed `download_proof_documents()` function

## Documentation

- `PROOF_DOWNLOAD_FIX.md` - Detailed explanation of the fix
- `verify_fix.py` - Verification script (already passed ✅)

---

**Need Help?** Check the logs:
```bash
docker logs kyc-api
```
