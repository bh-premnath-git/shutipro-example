# localhost.run Setup Guide

Quick guide for using localhost.run to receive ShuftiPro webhooks in local development.

## 🚀 Quick Start (3 Steps)

### Step 1: Start the Tunnel

Open a **new terminal** and run:

```bash
cd /home/premnath/shuftipro
./start_tunnel.sh
```

Or manually:
```bash
ssh -R 80:localhost:8080 nokey@localhost.run
```

**You'll see output like:**
```
Connect to http://abc-123-xyz.localhost.run or https://abc-123-xyz.localhost.run

** your connection id is abc-123-xyz-lhr.a.localhost.run, please mention it if you send me a message about an issue. **

** Warning: This is a public url and may be visible to external parties. Use at your own risk. **
```

**Copy the URL:** `abc-123-xyz.localhost.run` (without http/https)

### Step 2: Set the Callback URL

In another terminal:

```bash
cd /home/premnath/shuftipro
./set_callback_url.sh abc-123-xyz.localhost.run
```

Or manually edit `.env`:
```bash
# Uncomment and set:
SHUFTIPRO_CALLBACK_URL=https://abc-123-xyz.localhost.run/kyc/shuftipro/webhook
```

### Step 3: Register in ShuftiPro & Restart

**Register the domain:**
1. Login to [ShuftiPro Dashboard](https://shuftipro.com)
2. Settings → Callback URLs
3. Add: `abc-123-xyz.localhost.run`
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
INFO - Using callback URL: https://abc-123-xyz.localhost.run/kyc/shuftipro/webhook
```

## ✅ You're Ready!

Test it:
```bash
curl -X POST http://localhost:8080/kyc/start \
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
Each time you restart the SSH tunnel, you'll get a **new URL**. You'll need to:
1. Update `.env` with new URL
2. Update ShuftiPro dashboard
3. Restart the app

### 💡 Keep Terminal Open
The terminal running `ssh -R 80:localhost:8080 nokey@localhost.run` must stay open for webhooks to work.

### 🔍 View Webhook Requests
In the terminal running the tunnel, you'll see all incoming requests in real-time!

## 🛠️ Troubleshooting

### "Connection closed"
The tunnel disconnected. Restart:
```bash
./start_tunnel.sh
```
Then update `.env` with the new URL.

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
   ps aux | grep "localhost.run"
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
# Terminal 1: Start tunnel
./start_tunnel.sh
# Copy the URL you see (e.g., abc-123.localhost.run)

# Terminal 2: Configure and test
./set_callback_url.sh abc-123.localhost.run
docker compose up -d app
docker compose logs app | grep callback

# Test the API
curl -X POST http://localhost:8080/kyc/start \
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
./set_callback_url.sh NEW-URL.localhost.run && docker compose up -d app
```

### View Real-Time Logs
```bash
docker compose logs app -f
```

### Test Without Completing KYC
Just check the status manually:
```bash
curl http://localhost:8080/kyc/status/ref-xxx | jq
```

## 🔐 Security Note

⚠️ **localhost.run creates a PUBLIC URL** - anyone with the URL can access your local server.

- Use only for development/testing
- The URL is random and changes each session
- Don't share the URL publicly
- Stop the tunnel when not in use (Ctrl+C)

## 🚀 Ready for Production?

For production, use your actual domain instead:

```yaml
# Production .env
SHUFTIPRO_CALLBACK_URL=https://api.yourcompany.com/kyc/shuftipro/webhook
```

No tunnel needed!

---

**Quick Reference:**
- Start tunnel: `./start_tunnel.sh`
- Set callback: `./set_callback_url.sh YOUR-URL.localhost.run`
- Restart app: `docker compose up -d app`
- View logs: `docker compose logs app -f`
