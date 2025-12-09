#!/bin/bash
set -e

echo "=== KYC Backend - Vault Setup ==="
echo ""

# Check if vault service is running
if ! docker compose ps vault | grep -q "Up"; then
    echo "Starting Vault service..."
    docker compose up vault -d
    echo "Waiting for Vault to be ready..."
    sleep 5
fi

echo ""

# Try to read credentials from .env file first
if [ -f ".env" ]; then
    echo "Checking .env file for credentials..."
    CLIENT_ID=$(grep "^CLIENT_ID=" .env | cut -d '=' -f2)
    SECRET_KEY=$(grep "^SECRET_KEY=" .env | cut -d '=' -f2)
fi

# If not found in .env, prompt user
if [ -z "$CLIENT_ID" ] || [ -z "$SECRET_KEY" ]; then
    echo "Please enter your ShuftiPro credentials:"
    echo ""
    read -p "Client ID: " CLIENT_ID
    read -sp "Secret Key: " SECRET_KEY
    echo ""
    echo ""
else
    echo "✅ Found credentials in .env file"
fi

if [ -z "$CLIENT_ID" ] || [ -z "$SECRET_KEY" ]; then
    echo "Error: Both Client ID and Secret Key are required"
    exit 1
fi

echo "Enabling KV v2 secrets engine..."
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=root vault vault secrets enable -path=secret kv-v2 2>/dev/null || echo "KV v2 already enabled"

echo "Storing ShuftiPro credentials in Vault..."
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=root vault vault kv put secret/shuftipro \
  client_id="$CLIENT_ID" \
  secret_key="$SECRET_KEY"

echo ""
echo "✅ Vault setup complete!"
echo ""
echo "Verifying stored secrets..."
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=root vault vault kv get secret/shuftipro

echo ""
echo "You can now start all services with:"
echo "  docker compose up --build"
