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
echo "Please enter your ShuftiPro credentials:"
echo ""

read -p "Client ID: " CLIENT_ID
read -sp "Secret Key: " SECRET_KEY
echo ""
echo ""

if [ -z "$CLIENT_ID" ] || [ -z "$SECRET_KEY" ]; then
    echo "Error: Both Client ID and Secret Key are required"
    exit 1
fi

export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=root

echo "Enabling KV v2 secrets engine..."
docker exec vault vault secrets enable -path=secret kv-v2 2>/dev/null || echo "KV v2 already enabled"

echo "Storing ShuftiPro credentials in Vault..."
docker exec -e VAULT_TOKEN=root vault vault kv put secret/shuftipro \
  client_id="$CLIENT_ID" \
  secret_key="$SECRET_KEY"

echo ""
echo "✅ Vault setup complete!"
echo ""
echo "Verifying stored secrets..."
docker exec -e VAULT_TOKEN=root vault vault kv get secret/shuftipro

echo ""
echo "You can now start all services with:"
echo "  docker compose up --build"
