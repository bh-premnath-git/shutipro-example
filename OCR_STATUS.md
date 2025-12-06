# OCR Data Extraction Status

## ❌ Current Issue

Your webhook is **NOT receiving OCR data** from ShuftiPro. The webhook only shows:

```json
{
  "verification_data": {
    "document": {
      "country": "CA",
      "selected_type": ["passport"]
    }
  }
}
```

**Missing OCR fields:**
- ❌ Name (first_name, last_name)
- ❌ Date of Birth (DOB)
- ❌ Document Number
- ❌ Expiry Date
- ❌ Issue Date
- ❌ Address (if applicable)

## ✅ What IS Working

- ✅ Webhook delivery (callbacks received)
- ✅ Signature verification (secure)
- ✅ Status updates (pending → approved)
- ✅ Document type detection (passport)
- ✅ Country detection (Canada)
- ✅ DynamoDB storage
- ✅ MinIO/S3 integration ready

## 🔧 Root Cause

**Your ShuftiPro journey (`iySLIfgD1764787557`) is NOT configured to extract OCR data.**

When using Journey-based verification:
- Journey defines ALL verification settings
- OCR extraction must be **explicitly enabled** in journey configuration
- Without enabling, ShuftiPro only returns pass/fail, not extracted data

## 📋 Action Required

### Option 1: Enable OCR in Journey (Recommended)

1. **Login to ShuftiPro Dashboard**: https://shuftipro.com

2. **Navigate to Journeys**:
   - Click "Journeys" in left menu
   - Find journey: `iySLIfgD1764787557`
   - Click "Edit" or "Configure"

3. **Enable OCR Extraction**:
   ```
   Document Settings:
   ☑ Extract Name
   ☑ Extract Date of Birth
   ☑ Extract Document Number
   ☑ Extract Expiry Date
   ☑ Extract Issue Date
   
   Webhook Settings:
   ☑ Return OCR data in webhook
   ☑ Include document proofs/images
   ```

4. **Save** and wait 2 minutes for propagation

5. **Test** with new verification:
   ```bash
   curl -X POST http://localhost:8181/kyc/start \
     -H 'Content-Type: application/json' \
     -d '{"email":"test@example.com"}' | jq
   ```

### Option 2: Contact ShuftiPro Support

If you can't find OCR settings in journey:
- **Email**: support@shuftipro.com
- **Request**: Enable OCR data extraction for journey `iySLIfgD1764787557`
- **Mention**: Need name, DOB, document_number, expiry_date in webhooks

## 📊 Expected Result After Fix

### Webhook Will Include:
```json
{
  "verification_data": {
    "document": {
      "name": {
        "first_name": "John",
        "last_name": "Doe",
        "full_name": "John Doe"
      },
      "dob": "1990-01-15",
      "document_number": "ABC123456",
      "expiry_date": "2030-12-31",
      "issue_date": "2020-01-01",
      "country": "CA",
      "selected_type": ["passport"]
    }
  },
  "proofs": {
    "document": {
      "front": "https://shuftipro.com/documents/xxx-front.jpg"
    }
  }
}
```

### App Logs Will Show:
```
INFO - OCR - Name: John Doe (John Doe), DOB: 1990-01-15, Doc#: ABC123456
INFO - Uploaded document_front for user user-xxx to S3: documents/user-xxx/document_front.jpg
```

### API Response Will Include:
```bash
$ curl http://localhost:8181/kyc/status/ref-xxx | jq '.raw.verification_data.document'

{
  "name": {
    "first_name": "John",
    "last_name": "Doe"
  },
  "dob": "1990-01-15",
  "document_number": "ABC123456",
  "country": "CA"
}
```

## 🧪 Testing After Configuration

```bash
# 1. Start new verification
RESPONSE=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}')

echo $RESPONSE | jq

# 2. Get reference
REF=$(echo $RESPONSE | jq -r '.reference')

# 3. Complete the verification_url in browser

# 4. Check webhook logs for OCR data
docker compose logs app -f | grep "OCR"

# 5. Check status API
curl http://localhost:8181/kyc/status/$REF | jq '.raw.verification_data'
```

## 🔍 Debugging

### Check What's in Webhook
```bash
# Watch for webhooks
docker compose logs app -f | grep -E "webhook|OCR"
```

### View Raw Webhook Data
```bash
# After verification completes
curl http://localhost:8181/kyc/status/REFERENCE | jq '.raw' > webhook_data.json
cat webhook_data.json
```

### Expected vs Current

**Current** (No OCR):
```json
{
  "verification_data": {
    "document": {
      "country": "CA",
      "selected_type": ["passport"]
    }
  }
}
```

**Expected** (With OCR):
```json
{
  "verification_data": {
    "document": {
      "name": {"first_name": "...", "last_name": "..."},
      "dob": "1990-01-15",
      "document_number": "ABC123",
      "country": "CA",
      "selected_type": ["passport"]
    }
  }
}
```

## 📚 Documentation

- **Setup Guide**: See `ENABLE_OCR_GUIDE.md` for detailed instructions
- **Webhook Flow**: See `LOCALHOST_RUN_SETUP.md` for webhook setup
- **Integration**: See `SHUFTIPRO_INTEGRATION.md` for API details

## ⚡ Quick Summary

**Problem**: Journey not configured for OCR extraction
**Solution**: Enable OCR settings in ShuftiPro dashboard for journey `iySLIfgD1764787557`
**Timeline**: 2-5 minutes after configuration
**Test**: Run new verification and check webhook logs

---

**Current Status**: ❌ OCR data extraction **DISABLED** in journey  
**Next Step**: Configure journey in ShuftiPro dashboard to enable OCR extraction
