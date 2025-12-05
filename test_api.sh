#!/bin/bash

API_URL="http://localhost:8181"

echo "=== KYC API Test Script ==="
echo ""

# Test 1: Start KYC verification
echo "1. Starting KYC verification..."
RESPONSE=$(curl -s -X POST "$API_URL/kyc/start" \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test-user-001",
    "email": "test@example.com",
    "documentTypes": ["id_card", "passport"],
    "sides": "front_back"
  }')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool

# Extract reference ID
REFERENCE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('reference', ''))" 2>/dev/null)

if [ -z "$REFERENCE" ]; then
    echo ""
    echo "⚠️  Failed to get reference ID. Make sure the API is running."
    exit 1
fi

echo ""
echo "Reference: $REFERENCE"
echo ""

# Test 2: Check status
echo "2. Checking KYC status..."
sleep 1
STATUS_RESPONSE=$(curl -s "$API_URL/kyc/status/$REFERENCE")

echo "Response:"
echo "$STATUS_RESPONSE" | python3 -m json.tool

echo ""
echo "=== Test Complete ==="
