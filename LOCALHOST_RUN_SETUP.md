# Cloudflare Tunnel Setup Guide

Quick guide for using Cloudflare Tunnel (cloudflared) to receive ShuftiPro webhooks in local development.

**No Cloudflare account required!** This uses Quick Tunnel mode for temporary public URLs.

## 🚀 Quick Start (3 Steps)

### Step 1: Start All Services (Including Tunnel)

Cloudflare Tunnel is now integrated into Docker Compose:

```bash
cd /home/premnath/shuftipro
docker compose up -d
```

The `cloudflared` service will automatically start and create a public tunnel.

### Step 1.5: Get the Tunnel URL

Run the helper script to extract the tunnel URL:

```bash
./get_tunnel_url.sh
```

Or manually check the logs:
```bash
docker logs cloudflared-tunnel
```

**You'll see output like:**
```
INFO | Your quick Tunnel has been created! Visit it:
https://bright-cat-8273.trycloudflare.com
```

**Copy the domain:** `bright-cat-8273.trycloudflare.com` (without https://)

### Step 2: Set the Callback URL

In another terminal:

```bash
cd /home/premnath/shuftipro
./set_callback_url.sh bright-cat-8273.trycloudflare.com
```

Or manually edit `.env`:
```bash
# Uncomment and set:
SHUFTIPRO_CALLBACK_URL=https://bright-cat-8273.trycloudflare.com/kyc/shuftipro/webhook
```

### Step 3: Register in ShuftiPro & Restart

**Register the domain:**
1. Login to [ShuftiPro Dashboard](https://shuftipro.com)
2. Settings → Callback URLs
3. Add: `bright-cat-8273.trycloudflare.com`
4. Save

**Restart the app:**
```bash
docker compose up -d app
```

**Verify:**
```bash
docker compose logs app | grep -i callback
```

You should see:
```
INFO - Using callback URL: https://bright-cat-8273.trycloudflare.com/kyc/shuftipro/webhook
```

## ✅ You're Ready!

Test it:
```bash
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"test-webhook",
    "email":"test@example.com",
    "documentTypes":["passport"],
    "sides":"front_only"
  }' | jq
```

Complete the verification at the returned URL, and the webhook will be sent to your tunnel!

## 🔄 Important Notes

### ⚠️ URL Changes Each Time
Each time you restart the `cloudflared` container, you'll get a **new URL**. You'll need to:
1. Run `./get_tunnel_url.sh` to get the new URL
2. Update `.env` with new URL using `./set_callback_url.sh`
3. Update ShuftiPro dashboard with the new domain
4. Restart the app: `docker compose restart app`

### 💡 Runs as Docker Service
The tunnel runs as a Docker service - no need to keep a separate terminal open!
- Starts automatically with `docker compose up`
- Restarts automatically if it crashes
- Integrated with your development stack

### 🔍 View Tunnel Logs
You can view the tunnel status and incoming requests:
```bash
docker logs -f cloudflared-tunnel
```

## 🛠️ Troubleshooting

### "Connection closed" or Tunnel Down
The tunnel service stopped. Restart:
```bash
docker compose restart cloudflared
```
Then get the new URL:
```bash
./get_tunnel_url.sh
```
And update `.env` with the new URL.

### "callback domain is not registered"
You'll see this error if the domain isn't in ShuftiPro dashboard:
```json
{
  "error": "The given callback domain is not registered in your account."
}
```

**Fix:** Add the domain in ShuftiPro Settings → Callback URLs

### No webhooks received
1. **Check tunnel is running:**
   ```bash
   docker ps | grep cloudflared-tunnel
   ```
   
   Or check the tunnel URL:
   ```bash
   ./get_tunnel_url.sh
   ```

2. **Verify URL in .env:**
   ```bash
   cat .env | grep SHUFTIPRO_CALLBACK_URL
   ```

3. **Check app loaded it:**
   ```bash
   docker exec kyc-api env | grep SHUFTIPRO_CALLBACK_URL
   ```

4. **Restart if needed:**
   ```bash
   docker compose up -d app
   ```

## 📝 Complete Example

```bash
# Start all services (including tunnel)
docker compose up -d

# Get the tunnel URL
./get_tunnel_url.sh
# Copy the URL you see (e.g., bright-cat-8273.trycloudflare.com)

# Configure callback URL
./set_callback_url.sh bright-cat-8273.trycloudflare.com
docker compose restart app
docker compose logs app | grep callback

# Test the API
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id":"webhook-test",
    "email":"test@example.com",
    "documentTypes":["passport"],
    "sides":"front_only"
  }' | jq
```

## 🎯 Pro Tips

### Quick URL Update
When you restart the tunnel and get a new URL:
```bash
# Restart cloudflared to get new URL
docker compose restart cloudflared
sleep 5

# Get and set the new URL
./get_tunnel_url.sh
./set_callback_url.sh NEW-URL.trycloudflare.com && docker compose restart app
```

### View Real-Time Logs
```bash
docker compose logs app -f
```

### Test Without Completing KYC
Just check the status manually:
```bash
curl http://localhost:8181/kyc/status/ref-xxx | jq
```

## 🔐 Security Note

⚠️ **Cloudflare Tunnel creates a PUBLIC URL** - anyone with the URL can access your local server.

- Use only for development/testing
- The URL is random and changes each restart
- Don't share the URL publicly
- Stop the tunnel when not in use: `docker compose stop cloudflared`
- The tunnel uses Cloudflare's infrastructure for secure HTTPS

## ✨ Advantages over localhost.run

**Why Cloudflare Tunnel?**
- ✅ Integrated into Docker Compose - no separate process
- ✅ Auto-restart on failure
- ✅ Managed by Docker - start/stop with your stack
- ✅ Reliable Cloudflare infrastructure
- ✅ HTTPS by default
- ✅ No SSH keys or authentication needed
- ✅ Helper script to extract URL easily

## 🚀 Ready for Production?

For production, use your actual domain instead:

```yaml
# Production .env
SHUFTIPRO_CALLBACK_URL=https://api.yourcompany.com/kyc/shuftipro/webhook
```

No tunnel needed!

---

**Quick Reference:**
- Start services: `docker compose up -d`
- Get tunnel URL: `./get_tunnel_url.sh`
- Set callback: `./set_callback_url.sh YOUR-URL.trycloudflare.com`
- Restart app: `docker compose restart app`
- View app logs: `docker compose logs app -f`
- View tunnel logs: `docker logs -f cloudflared-tunnel`
- Stop tunnel: `docker compose stop cloudflared`
