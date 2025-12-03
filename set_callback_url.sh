#!/bin/bash
set -e

echo "=========================================="
echo "Configure ShuftiPro Callback URL"
echo "=========================================="
echo ""

# Check if URL is provided as argument
if [ -z "$1" ]; then
    read -p "Enter your localhost.run URL (e.g., abc-123.localhost.run): " TUNNEL_URL
else
    TUNNEL_URL=$1
fi

# Remove https:// or http:// if present
TUNNEL_URL=$(echo $TUNNEL_URL | sed 's|https://||' | sed 's|http://||' | sed 's|/.*||')

if [ -z "$TUNNEL_URL" ]; then
    echo "Error: URL cannot be empty"
    exit 1
fi

# Full callback URL
CALLBACK_URL="https://${TUNNEL_URL}/kyc/shuftipro/webhook"

echo ""
echo "Setting callback URL to: $CALLBACK_URL"
echo ""

# Update .env file
if grep -q "^SHUFTIPRO_CALLBACK_URL=" .env; then
    # URL already set, update it
    sed -i "s|^SHUFTIPRO_CALLBACK_URL=.*|SHUFTIPRO_CALLBACK_URL=$CALLBACK_URL|" .env
    echo "✅ Updated existing callback URL in .env"
elif grep -q "^# SHUFTIPRO_CALLBACK_URL=" .env; then
    # URL is commented, uncomment and set
    sed -i "s|^# SHUFTIPRO_CALLBACK_URL=.*|SHUFTIPRO_CALLBACK_URL=$CALLBACK_URL|" .env
    echo "✅ Uncommented and set callback URL in .env"
else
    # Add new line
    echo "SHUFTIPRO_CALLBACK_URL=$CALLBACK_URL" >> .env
    echo "✅ Added callback URL to .env"
fi

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Register domain in ShuftiPro Dashboard:"
echo "   - Login to https://shuftipro.com"
echo "   - Go to Settings → Callback URLs"
echo "   - Add domain: $TUNNEL_URL"
echo ""
echo "2. Restart the app:"
echo "   docker compose up -d app"
echo ""
echo "3. Verify it's working:"
echo "   docker compose logs app | grep -i callback"
echo ""
echo "You should see:"
echo "   INFO - Using callback URL: $CALLBACK_URL"
echo ""
echo "=========================================="
