#!/bin/bash

echo "=========================================="
echo "Starting localhost.run tunnel..."
echo "=========================================="
echo ""
echo "This will create a public URL for your local server."
echo "Keep this terminal open while testing webhooks."
echo ""
echo "Once you see the URL, copy the HTTPS version and:"
echo "1. Update .env file: SHUFTIPRO_CALLBACK_URL=https://YOUR-URL.localhost.run/kyc/shuftipro/webhook"
echo "2. Add the domain (YOUR-URL.localhost.run) to ShuftiPro dashboard"
echo "3. Restart the app: docker compose up -d app"
echo ""
echo "=========================================="
echo ""

# Start the tunnel
ssh -R 80:localhost:8080 nokey@localhost.run
