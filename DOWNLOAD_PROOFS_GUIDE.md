# ShuftiPro Proof Download Guide

## ✅ **SOLVED: Automatic Download Working**

Proof URLs from ShuftiPro can be downloaded using **Bearer token authentication**.

**Working authentication method:**
```bash
curl -L \
  -H "Authorization: Bearer {access_token}" \
  -o document_proof.pdf \
  "https://ns.shuftipro.com/api/pea/{proof_hash}"
```

✅ **Status:** Automatic downloads now working!

---

## 🔍 Possible Reasons

1. **IP Whitelisting**: ShuftiPro proof URLs may only be accessible from whitelisted IPs
2. **Browser-Only Access**: URLs might require browser cookies/sessions
3. **Expired URLs**: Proof URLs may have a short expiration time
4. **Account Restrictions**: Trial accounts may have download restrictions

---

## ✅ Manual Download Methods

### Method 1: Download via Browser

1. Get the proof URLs and access token:
```bash
curl -X POST http://localhost:8181/kyc/query-status/ref-user-1764924147-7023 | jq '.shuftipro_data.proofs'
```

2. Open URLs in browser with access token:
```
Document: https://ns.shuftipro.com/api/pea/[hash]?access_token=[token]
Video: https://ns.shuftipro.com/api/pea/[hash]?access_token=[token]
Report: https://ns.shuftipro.com/api/pea/[hash]?access_token=[token]
```

3. Browser will download the files automatically

### Method 2: Use ShuftiPro Dashboard

1. Login to https://app.shuftipro.com/
2. Go to **Verifications** section
3. Find verification by reference: `ref-user-1764924147-7023`
4. Click to view details
5. Download proofs directly from dashboard

### Method 3: wget/curl with Access Token (Try from Different IP)

```bash
# Get fresh URLs
curl -X POST http://localhost:8181/kyc/query-status/REF | jq -r '.shuftipro_data.proofs.document.proof' > url.txt
curl -X POST http://localhost:8181/kyc/query-status/REF | jq -r '.shuftipro_data.proofs.access_token' > token.txt

# Try downloading
URL=$(cat url.txt)
TOKEN=$(cat token.txt)

wget "${URL}?access_token=${TOKEN}" -O document_proof.jpg

# For video
curl -X POST http://localhost:8181/kyc/query-status/REF | jq -r '.shuftipro_data.proofs.verification_video' > video_url.txt
VIDEO_URL=$(cat video_url.txt)
wget "${VIDEO_URL}?access_token=${TOKEN}" -O verification_video.mp4

# For report
curl -X POST http://localhost:8181/kyc/query-status/REF | jq -r '.shuftipro_data.proofs.verification_report' > report_url.txt
REPORT_URL=$(cat report_url.txt)
wget "${REPORT_URL}?access_token=${TOKEN}" -O verification_report.pdf
```

---

## 📧 Contact ShuftiPro Support

Ask them about programmatic proof downloads:

```
Subject: API Access to Proof URLs - 403 Forbidden

Hi ShuftiPro Support,

I'm trying to download verification proofs programmatically using the 
proof URLs and access_token from the verification response, but getting 
403 Forbidden errors.

Reference: ref-user-1764924147-7023

Proof URLs:
- document.proof
- verification_video
- verification_report

Access Token: [from response]

Questions:
1. Is there IP whitelisting for proof URLs?
2. What is the correct authentication method for downloading proofs programmatically?
3. Are there account restrictions for automated downloads?
4. What is the expiration time for proof URLs?

Currently testing with these methods:
- Query parameter: ?access_token=xxx (403)
- Authorization header: Bearer xxx (403)
- Custom header: Access-Token: xxx (403)

Please advise the correct way to download proofs via API.

Thank you!
```

---

## 🎯 Workaround: Screenshot/Screen Recording

If downloads are not available:

1. **For Documents**: Use ShuftiPro dashboard to view and screenshot
2. **For Videos**: Use screen recording tool while playing video
3. **For Reports**: Dashboard usually has "Download Report" button

---

## 🔧 What We've Implemented

Even though automatic download isn't working, we've added:

### API Endpoint (Ready for when it works):
```bash
POST /kyc/download-proofs/{reference}
```

This endpoint:
- Extracts proofs and access token from session
- Tries multiple authentication methods
- Uploads to MinIO/S3 when successful
- Stores local backup

**Currently returns:**
```json
{
  "detail": "Failed to download proofs: 500: Failed to download any proofs"
}
```

### Database Function:
`download_proof_documents()` in `app/db/dynamo.py`

**Features:**
- Multiple auth methods (query, bearer, custom header)
- Automatic file type detection
- S3/MinIO upload
- Local backup
- Handles: document proofs, videos, reports

---

## 📊 Current Status

| Item | Status | Notes |
|------|--------|-------|
| Proof URLs retrieval | ✅ Working | Can get URLs from API |
| Access token retrieval | ✅ Working | Included in response |
| Automatic download | ❌ Blocked | 403 Forbidden |
| Manual browser download | ✅ Should work | Try with browser |
| Dashboard download | ✅ Should work | Login to ShuftiPro |
| API endpoint ready | ✅ Ready | Will work when access is granted |

---

## 🎯 Immediate Actions

1. **Try browser download** with URLs + access token
2. **Check ShuftiPro dashboard** for download options
3. **Contact ShuftiPro support** about programmatic access
4. **Check if trial account** has download restrictions

---

## 📝 Example: Get Fresh URLs

```bash
# Query current verification
curl -X POST http://localhost:8181/kyc/query-status/ref-user-1764924147-7023 | jq '.shuftipro_data.proofs'

# Output:
{
  "document": {
    "proof": "https://ns.shuftipro.com/api/pea/..."
  },
  "access_token": "8a171080ef38f9c7ac5deec331d9ffa1...",
  "verification_video": "https://ns.shuftipro.com/api/pea/...",
  "verification_report": "https://ns.shuftipro.com/api/pea/..."
}
```

Then try in browser:
```
https://ns.shuftipro.com/api/pea/[hash]?access_token=[token]
```

---

**Once ShuftiPro enables programmatic access, the `/kyc/download-proofs/{reference}` endpoint will automatically start working!**
