# How to Enable OCR Data Extraction

## Problem
Your webhooks show verification passed but OCR data is `None`:
```
OCR - Name: None None, DOB: None, Doc#: None
```

The webhook payload only contains:
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

But it should contain extracted OCR fields like:
```json
{
  "verification_data": {
    "document": {
      "name": {
        "first_name": "John",
        "last_name": "Doe",
        "full_name": "John Doe"
      },
      "dob": "1990-01-01",
      "document_number": "ABC123456",
      "expiry_date": "2030-12-31",
      "issue_date": "2020-01-01",
      "country": "CA"
    }
  }
}
```

## Solution: Configure Journey on ShuftiPro Dashboard

### Step 1: Login to ShuftiPro
Go to: https://shuftipro.com
Login with your credentials

### Step 2: Navigate to Journey Settings
1. Go to **"Journeys"** in the left menu
2. Find your journey: **`iySLIfgD1764787557`**
3. Click **"Edit"** or **"Configure"**

### Step 3: Enable OCR Data Extraction

In the journey configuration, ensure these settings are enabled:

#### Document Verification Settings
```
☑ Extract Name
  ☑ First Name
  ☑ Last Name
  ☑ Full Name

☑ Extract Date of Birth (DOB)

☑ Extract Document Number

☑ Extract Expiry Date

☑ Extract Issue Date (optional)

☑ Extract Document Country

☑ Extract Document Type
```

#### OCR Data Return Settings
```
☑ Return OCR data in webhook
☑ Return OCR data in verification result
☑ Include document images/proofs
```

### Step 4: Document Proof Settings (Optional)
If you want document images in the webhook:
```
☑ Return document front image URL
☑ Return document back image URL (if applicable)
☑ Return face image URL
```

### Step 5: Save and Test

1. **Save** the journey configuration
2. **Wait 1-2 minutes** for changes to propagate
3. **Test** with a new verification:

```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq
```

4. Complete the verification and check the webhook:

```bash
# Check the status with OCR data
curl http://localhost:8181/kyc/status/REFERENCE | jq '.raw.verification_data'
```

## Expected Result After Fix

### Webhook Logs Will Show:
```
INFO - OCR - Name: John Doe, DOB: 1990-01-01, Doc#: ABC123456
INFO - OCR - Address: 123 Main St, Toronto, ON
```

### API Response Will Include:
```json
{
  "reference": "ref-user-xxx",
  "status": "approved",
  "raw": {
    "verification_data": {
      "document": {
        "name": {
          "first_name": "John",
          "last_name": "Doe",
          "full_name": "John Doe"
        },
        "dob": "1990-01-01",
        "document_number": "ABC123456",
        "expiry_date": "2030-12-31",
        "country": "CA",
        "selected_type": ["passport"]
      }
    },
    "proofs": {
      "document": {
        "front": "https://shuftipro.com/documents/xxx-front.jpg",
        "back": "https://shuftipro.com/documents/xxx-back.jpg"
      }
    }
  }
}
```

## Alternative: API Request Method

If journey configuration doesn't support OCR extraction, you can also make an API request to ShuftiPro to fetch the detailed verification data:

```bash
# Fetch detailed verification result
curl -X POST https://api.shuftipro.com/status \
  -H "Authorization: Basic $(echo -n 'CLIENT_ID:SECRET_KEY' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"reference": "ref-user-xxx"}'
```

## Checking Current Journey Configuration

You can check what fields your journey is configured to extract by:

1. **Via Dashboard**: 
   - Journeys → Your Journey → View Configuration

2. **Via API** (if available):
   ```bash
   curl https://api.shuftipro.com/journeys/iySLIfgD1764787557 \
     -H "Authorization: Basic $(echo -n 'CLIENT_ID:SECRET_KEY' | base64)"
   ```

## Common Issues

### Issue 1: OCR Still Shows None
**Cause**: Journey changes haven't propagated yet
**Solution**: Wait 2-5 minutes and test again

### Issue 2: Partial OCR Data
**Cause**: Some fields weren't enabled in journey
**Solution**: Go back to journey settings and enable all required fields

### Issue 3: No Document Images
**Cause**: Document proof return not enabled
**Solution**: Enable "Return document images" in journey settings

### Issue 4: Different Document Types Have Different Fields
**Note**: Passport, ID Card, and Driver's License have different OCR fields:
- **Passport**: name, DOB, document_number, expiry_date, nationality
- **ID Card**: name, DOB, document_number, expiry_date, address
- **Driver's License**: name, DOB, license_number, expiry_date, issue_date, address

Make sure your journey is configured for all document types you accept.

## Support

If OCR data is still not showing after configuration:
1. Contact ShuftiPro support: support@shuftipro.com
2. Reference your journey ID: `iySLIfgD1764787557`
3. Mention you need OCR data extraction enabled in webhooks

---

**Quick Test Command:**
```bash
# After configuring journey, test immediately:
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq

# Complete verification, then check:
docker compose logs app -f | grep "OCR"
```
