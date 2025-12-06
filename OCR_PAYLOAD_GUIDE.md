# ShuftiPro OCR Extraction via API Payload

## ✅ **Solution Implemented**

Your API now **automatically enables OCR extraction** by including extraction fields directly in the API payload!

---

## 🎯 **How It Works**

### **Before (Journey-Based)**
```json
{
  "reference": "ref-user-xxx",
  "journey_id": "iySLIfgD1764787557",  // Journey controls everything
  "email": "user@example.com"
}
```
**Problem:** If journey doesn't have OCR enabled, no OCR data is extracted.

### **After (API-Based with OCR)**
```json
{
  "reference": "ref-user-xxx",
  "email": "user@example.com",
  "document": {
    "supported_types": ["passport", "id_card", "driving_license"],
    "name": {
      "first_name": "",      // Empty string = extract via OCR
      "last_name": "",       // Empty string = extract via OCR
      "middle_name": ""      // Empty string = extract via OCR
    },
    "dob": "",               // Empty string = extract via OCR
    "document_number": "",   // Empty string = extract via OCR
    "issue_date": "",        // Empty string = extract via OCR
    "expiry_date": "",       // Empty string = extract via OCR
    "gender": "",            // Empty string = extract via OCR
    "fetch_enhanced_data": "1"  // Extract 100+ additional fields
  },
  "callback_url": "https://your-domain.com/kyc/shuftipro/webhook"
}
```

**Key Insight:** Setting fields to `""` (empty string) tells ShuftiPro to **extract them via OCR**!

---

## 📊 **Usage Options**

### **1. Default: API-Based with OCR (Recommended)**

```bash
# Start verification with automatic OCR extraction
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}' | jq
```

**What happens:**
- ✅ OCR extraction enabled by default
- ✅ Extracts: name, DOB, document number, dates, gender
- ✅ Extracts 100+ additional fields (nationality, place of birth, etc.)
- ✅ No journey dependency

### **2. Use Journey Instead**

```bash
# Use journey-based verification
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "email":"user@example.com",
    "use_journey": true,
    "journey_id": "iySLIfgD1764787557"
  }' | jq
```

**When to use:**
- Journey has custom branding/settings you need
- Journey has OCR already enabled
- You want journey-specific configuration

### **3. Disable OCR (Basic Verification)**

```bash
# Verification without OCR extraction
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "email":"user@example.com",
    "enable_ocr": false
  }' | jq
```

---

## 🎉 **What You'll Get in Webhook**

After completing verification with OCR enabled:

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
      "country": "CA",
      "selected_type": ["passport"]
    }
  },
  "additional_data": {
    "document": {
      "proof": {
        "height": "183",
        "nationality": "CANADIAN CITIZEN",
        "place_of_birth": "Toronto",
        "country_code": "CAN",
        "document_type": "P",
        "personal_number": "1234567890"
      }
    }
  },
  "proofs": {
    "document": {
      "proof": "https://ns.shuftipro.com/api/pea/..."
    },
    "access_token": "xxx",
    "verification_video": "https://ns.shuftipro.com/api/pea/...",
    "verification_report": "https://ns.shuftipro.com/api/pea/..."
  }
}
```

---

## 🔍 **Verify It's Working**

### **1. Start New Verification**

```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"your-email@example.com"}' | jq

# Save the reference
REF="ref-user-xxx"
```

### **2. Complete Verification**

Open the `verification_url` in browser and complete the verification with a real document.

### **3. Check Webhook Logs**

```bash
docker compose logs app -f | grep "OCR"

# You should see:
# "OCR extraction enabled in API payload"
# "OCR - Name: John Doe (John Doe), DOB: 1990-01-15, Doc#: AB123456"
```

### **4. Query Status**

```bash
curl http://localhost:8181/kyc/status/$REF | jq '.raw.verification_data.document'
```

**Expected output:**
```json
{
  "name": {
    "first_name": "John",
    "last_name": "Doe"
  },
  "dob": "1990-01-15",
  "document_number": "AB123456",
  "country": "CA"
}
```

---

## 📋 **What Changed**

### **File: `app/kyc_adapter/shuftipro.py`**

```python
def _build_payload(self, body: Dict[str, Any]) -> Dict[str, Any]:
    # NEW: OCR enabled by default
    enable_ocr = body.get("enable_ocr", True)  
    use_journey = body.get("use_journey", False)
    
    if enable_ocr:
        # Add document service with OCR extraction
        payload["document"] = {
            "supported_types": ["passport", "id_card", "driving_license"],
            "name": {
                "first_name": "",   # Extract via OCR
                "last_name": "",
                "middle_name": ""
            },
            "dob": "",
            "document_number": "",
            "issue_date": "",
            "expiry_date": "",
            "gender": "",
            "fetch_enhanced_data": "1"  # 100+ fields
        }
```

### **Default Behavior**

| Option | Default | Description |
|--------|---------|-------------|
| `enable_ocr` | `True` | Extract OCR data via API payload |
| `use_journey` | `False` | Use journey configuration instead |

---

## 🎯 **Benefits**

### **API-Based OCR (Current Default)**

✅ **No journey dependency** - works immediately  
✅ **Full OCR extraction** - all fields  
✅ **100+ additional fields** - via `fetch_enhanced_data`  
✅ **No dashboard configuration needed**  
✅ **Consistent across all verifications**

### **Journey-Based (Optional)**

✅ **Custom branding** - journey controls UI  
✅ **Pre-configured settings** - set once in dashboard  
✅ **Multiple journey types** - different configs per use case

---

## 🚀 **Test Now**

```bash
# 1. Start verification (OCR auto-enabled)
REF=$(curl -s -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}' | jq -r '.reference')

echo "Reference: $REF"

# 2. Get verification URL
URL=$(curl -s http://localhost:8181/kyc/status/$REF | jq -r '.raw.verification_url')
echo "Complete verification at: $URL"

# 3. After completing, check OCR data
curl -s http://localhost:8181/kyc/status/$REF | \
  jq '.raw.verification_data.document | {name, dob, document_number}'
```

---

## 📚 **API Reference**

### **POST /kyc/start**

**Request Body:**
```json
{
  "email": "user@example.com",        // Required
  "enable_ocr": true,                 // Optional (default: true)
  "use_journey": false,               // Optional (default: false)
  "journey_id": "xxx"                 // Optional (if use_journey=true)
}
```

**Response:**
```json
{
  "reference": "ref-user-xxx",
  "provider": "shuftipro",
  "verification_url": "https://app.shuftipro.com/...",
  "error": null
}
```

---

## ✅ **Summary**

**Problem:** Journey didn't have OCR enabled → No OCR data in webhook  
**Solution:** Request OCR extraction directly in API payload  
**Result:** OCR data automatically extracted and sent to webhook  

**Your code now:**
1. ✅ Sends OCR extraction request in API payload
2. ✅ ShuftiPro extracts all document fields via OCR
3. ✅ Webhook receives complete OCR data
4. ✅ Data logged and stored in DynamoDB
5. ✅ All fields accessible via `/kyc/status` endpoint

**No journey configuration needed!** 🎉
