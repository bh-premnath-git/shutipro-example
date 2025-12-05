#!/bin/bash

echo "=========================================="
echo "Starting Cloudflare Tunnel..."
echo "=========================================="
echo ""
echo "ℹ️  NOTE: Cloudflare Tunnel is now integrated into Docker Compose!"
echo ""
echo "The tunnel service starts automatically with:"
echo "  docker compose up -d"
echo ""
echo "=========================================="
echo ""

# Check if cloudflared is already running
if docker ps --format '{{.Names}}' | grep -q "^cloudflared-tunnel$"; then
    echo "✅ Cloudflare Tunnel is already running!"
    echo ""
    echo "Getting the tunnel URL..."
    echo ""
    ./get_tunnel_url.sh
else
    echo "Starting Cloudflare Tunnel service..."
    docker compose up -d cloudflared
    
    echo ""
    echo "⏳ Waiting for tunnel to start..."
    sleep 5
    echo ""
    
    ./get_tunnel_url.sh
fi
