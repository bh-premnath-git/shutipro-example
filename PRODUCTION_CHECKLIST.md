# Production Deployment Checklist

Complete checklist for deploying the KYC backend to production.

## 🔐 Security

### 1. Webhook IP Whitelisting

**ShuftiPro Webhook IPs** - Whitelist these IPs in your firewall/security groups:

**Europe:**
- `142.132.144.101`
- `65.108.103.45`

**United States:**
- `5.161.114.110`
- `5.161.87.219`
- `5.78.56.7`
- `5.78.58.196`

**Action Required:**
```bash
# Example: AWS Security Group
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 142.132.144.101/32

# Example: nginx
# Add to your nginx.conf
geo $shufti_ip {
    default 0;
    142.132.144.101 1;
    65.108.103.45 1;
    5.161.114.110 1;
    5.161.87.219 1;
    5.78.56.7 1;
    5.78.58.196 1;
}

server {
    location /kyc/shuftipro/webhook {
        if ($shufti_ip = 0) {
            return 403;
        }
        proxy_pass http://app:8181;
    }
}
```

### 2. Change Default Credentials

**MinIO:**
```yaml
# docker-compose.yml
environment:
  MINIO_ROOT_USER: "production-user"           # Change from minioadmin
  MINIO_ROOT_PASSWORD: "strong-password-min-32-chars"  # Change from minioadmin
```

**Vault:**
```bash
# Unseal keys and root token should be stored in AWS Secrets Manager or similar
# Never commit to git
```

### 3. Environment Variables

Move from `.env` to secure secrets management:
```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name shuftipro/credentials \
  --secret-string '{"client_id":"xxx","secret_key":"xxx"}'

# Or HashiCorp Vault (already using)
vault kv put secret/shuftipro/prod \
  client_id=xxx \
  secret_key=xxx
```

### 4. Enable HTTPS/TLS

**API:**
```yaml
# docker-compose.yml
app:
  environment:
    - FORCE_HTTPS=true
```

**MinIO:**
```yaml
minio:
  command: server /data --console-address ":9001" --certs-dir /certs
  volumes:
    - ./certs:/certs:ro
```

### 5. Signature Verification

Already implemented ✅ - but ensure it's enforced:
```python
# app/main.py - line 189
if signature:
    # Verify signature
    if signature != calculated_sig:
        raise HTTPException(status_code=401, detail="Invalid signature")
```

## ⚡ Rate Limiting

### ShuftiPro API Limits

**Production Account:**
- 60 requests per minute per IP
- Plan accordingly for high-volume scenarios

**Trial Account:**
- 20 requests per minute
- Sufficient for testing only

### Implement Application Rate Limiting

Add rate limiting to your API:

```python
# requirements.txt
slowapi==0.1.9

# app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/kyc/start")
@limiter.limit("50/minute")  # Below ShuftiPro's 60/min limit
async def kyc_start(request: Request, body: KycStartRequest):
    # ... existing code
```

## 🗄️ Database

### DynamoDB

**Production Table:**
```bash
# Create production table with proper capacity
aws dynamodb create-table \
  --table-name kyc-sessions-prod \
  --attribute-definitions \
    AttributeName=reference,AttributeType=S \
  --key-schema \
    AttributeName=reference,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --point-in-time-recovery-specification Enabled=true \
  --tags Key=Environment,Value=Production
```

**Backup Strategy:**
- Enable Point-in-Time Recovery ✅
- Enable DynamoDB Streams for audit trail
- Configure daily backups to S3

### MinIO/S3

**Migrate to AWS S3:**
```yaml
# docker-compose.yml or environment
environment:
  S3_ENDPOINT: ""  # Empty for AWS S3
  S3_ACCESS_KEY: "${AWS_ACCESS_KEY_ID}"
  S3_SECRET_KEY: "${AWS_SECRET_ACCESS_KEY}"
  S3_BUCKET_NAME: "kyc-documents-prod"
  AWS_REGION: "us-east-1"
  S3_FORCE_PATH_STYLE: "false"
```

**S3 Bucket Configuration:**
```bash
# Create bucket
aws s3 mb s3://kyc-documents-prod

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket kyc-documents-prod \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket kyc-documents-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Lifecycle policy (delete after 90 days)
aws s3api put-bucket-lifecycle-configuration \
  --bucket kyc-documents-prod \
  --lifecycle-configuration file://lifecycle.json
```

## 🌐 Infrastructure

### DNS & Domain

**Callback URL:**
```
Production: https://api.yourdomain.com/kyc/shuftipro/webhook
Development: https://cloudflare-tunnel-url/kyc/shuftipro/webhook
```

### Load Balancer

**AWS Application Load Balancer:**
```bash
# Create target group
aws elbv2 create-target-group \
  --name kyc-api-tg \
  --protocol HTTP \
  --port 8181 \
  --vpc-id vpc-xxxxx \
  --health-check-path /health

# Create ALB
aws elbv2 create-load-balancer \
  --name kyc-api-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxx \
  --scheme internet-facing
```

### Container Orchestration

**ECS/Fargate:**
```yaml
# task-definition.json
{
  "family": "kyc-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "your-ecr-repo/kyc-api:latest",
      "portMappings": [{"containerPort": 8181}],
      "secrets": [
        {
          "name": "SHUFTIPRO_CLIENT_ID",
          "valueFrom": "arn:aws:secretsmanager:..."
        }
      ]
    }
  ]
}
```

**Or Kubernetes:**
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kyc-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kyc-api
  template:
    spec:
      containers:
      - name: app
        image: your-registry/kyc-api:latest
        ports:
        - containerPort: 8181
        env:
        - name: SHUFTIPRO_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: shuftipro-creds
              key: client_id
```

## 📊 Monitoring

### Logging

**CloudWatch Logs:**
```python
# Add structured logging
import watchtower
import logging

logger = logging.getLogger(__name__)
logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group="/aws/kyc-api/prod",
    stream_name="app"
))
```

**Key Metrics to Monitor:**
- Request rate to `/kyc/start`
- Webhook delivery success rate
- ShuftiPro API response times
- S3 upload success rate
- DynamoDB read/write capacity

### Alerts

**Set up alerts for:**
- Error rate > 5%
- Response time > 2s
- Webhook signature failures
- Rate limit hits (approaching 60/min)
- S3 upload failures
- DynamoDB throttling

### Health Check Endpoint

Add to `app/main.py`:
```python
@app.get("/health")
async def health_check():
    """Health check for load balancer"""
    try:
        # Check DynamoDB
        get_table()
        # Check S3
        get_s3_storage()
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

## 🔄 CI/CD

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker image
        run: docker build -t kyc-api:${{ github.sha }} ./app
      
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REPO
          docker tag kyc-api:${{ github.sha }} $ECR_REPO:latest
          docker push $ECR_REPO:latest
      
      - name: Deploy to ECS
        run: aws ecs update-service --cluster prod --service kyc-api --force-new-deployment
```

## 🧪 Testing

### Load Testing

```bash
# Using k6
k6 run --vus 10 --duration 1m load-test.js

# load-test.js
import http from 'k6/http';

export default function() {
  const payload = JSON.stringify({
    email: `test-${__VU}-${__ITER}@example.com`
  });
  
  http.post('https://api.yourdomain.com/kyc/start', payload, {
    headers: { 'Content-Type': 'application/json' }
  });
}
```

### Webhook Testing

```bash
# Test webhook endpoint with ShuftiPro IPs
curl -X POST https://api.yourdomain.com/kyc/shuftipro/webhook \
  -H "Content-Type: application/json" \
  -H "Signature: xxx" \
  -d '{"reference":"test","event":"verification.accepted",...}'
```

## 📝 Documentation

### Update Configuration

1. Journey ID → Production journey
2. Callback URL → Production domain
3. Client credentials → Production credentials
4. Enable OCR extraction in production journey

### Register Callback Domain

In ShuftiPro dashboard:
1. Settings → Callback URLs
2. Add: `api.yourdomain.com`
3. Verify domain ownership

## ✅ Pre-Launch Checklist

- [ ] Webhook IPs whitelisted in firewall
- [ ] Changed all default credentials
- [ ] Migrated to AWS S3 from MinIO
- [ ] DynamoDB production table created
- [ ] Secrets moved to AWS Secrets Manager
- [ ] HTTPS/TLS enabled
- [ ] Rate limiting implemented
- [ ] Health check endpoint added
- [ ] CloudWatch logging configured
- [ ] Alerts set up
- [ ] Load balancer configured
- [ ] Domain registered with ShuftiPro
- [ ] Production journey configured with OCR
- [ ] CI/CD pipeline set up
- [ ] Load testing completed
- [ ] Backup strategy implemented
- [ ] Documentation updated

## 🚀 Launch Day

1. Update DNS to point to production
2. Monitor CloudWatch logs
3. Check webhook deliveries
4. Verify end-to-end flow
5. Monitor error rates
6. Check ShuftiPro rate limits

## 📞 Support Contacts

**ShuftiPro:**
- Rate limit adjustments: tech@shuftipro.com
- General support: support@shuftipro.com

**AWS Support:**
- Your AWS account manager
- AWS Support Center

---

**Current Status**: Development ✅  
**Production Ready**: After checklist completion ⏳  
**Estimated Setup Time**: 2-3 days
