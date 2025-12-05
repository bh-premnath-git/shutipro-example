#!/bin/bash

echo "=========================================="
echo "Cloudflare Tunnel URL Extractor"
echo "=========================================="
echo ""

# Check if cloudflared container is running
if ! docker ps --format '{{.Names}}' | grep -q "^cloudflared-tunnel$"; then
    echo "❌ Error: cloudflared-tunnel container is not running"
    echo ""
    echo "Start it with:"
    echo "  docker compose up -d cloudflared"
    exit 1
fi

echo "⏳ Waiting for Cloudflare Tunnel URL..."
echo ""

# Wait up to 30 seconds for the URL to appear in logs
TIMEOUT=30
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Extract the tunnel URL from logs
    TUNNEL_URL=$(docker logs cloudflared-tunnel 2>&1 | grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' | head -1)
    
    if [ -n "$TUNNEL_URL" ]; then
        echo "✅ Cloudflare Tunnel is active!"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Public URL: $TUNNEL_URL"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        # Extract domain without https://
        DOMAIN=$(echo $TUNNEL_URL | sed 's|https://||')
        
        echo "📋 Next Steps:"
        echo ""
        echo "1. Set the callback URL in .env:"
        echo "   ./set_callback_url.sh $DOMAIN"
        echo ""
        echo "2. Register domain in ShuftiPro Dashboard:"
        echo "   - Login: https://shuftipro.com"
        echo "   - Go to: Settings → Callback URLs"
        echo "   - Add domain: $DOMAIN"
        echo ""
        echo "3. Restart the app:"
        echo "   docker compose restart app"
        echo ""
        exit 0
    fi
    
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo -n "."
done

echo ""
echo ""
echo "⚠️  Timeout: Could not find tunnel URL in logs"
echo ""
echo "Check the logs manually:"
echo "  docker logs cloudflared-tunnel"
echo ""
