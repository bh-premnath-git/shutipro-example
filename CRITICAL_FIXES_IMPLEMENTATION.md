# Critical Fixes Implementation Guide

This document provides step-by-step implementation for the most critical security issues.

---

## Fix #1: Add API Authentication

### Step 1: Add Authentication Module

Create `app/auth.py`:

```python
"""
API Authentication module using API keys.
"""
import os
import secrets
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

# In production, load from database or Vault
API_KEYS = {
    os.getenv("API_KEY_1", "your-secure-api-key-here"): {"name": "Production Client", "rate_limit": 100},
    os.getenv("API_KEY_2", "another-secure-key"): {"name": "Development Client", "rate_limit": 10}
}


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Verify API key from Authorization header.
    
    Usage: 
        Authorization: Bearer your-api-key-here
    """
    api_key = credentials.credentials
    
    if api_key not in API_KEYS:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return API_KEYS[api_key]


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health"
}
```

### Step 2: Update main.py

Add to `app/main.py`:

```python
from auth import verify_api_key
from fastapi import Depends

# Add authentication to protected endpoints
@app.post("/kyc/start", response_model=KycStartResponse)
async def kyc_start(
    body: KycStartRequest,
    api_key: dict = Depends(verify_api_key)  # ✅ Authentication required
):
    logger.info(f"KYC verification started by: {api_key['name']}")
    # ... existing code ...

@app.get("/kyc/status/{reference}", response_model=KycStatusResponse)
async def kyc_status(
    reference: str,
    api_key: dict = Depends(verify_api_key)  # ✅ Authentication required
):
    # ... existing code ...

@app.delete("/kyc/{reference}")
async def delete_verification(
    reference: str,
    body: KycDeleteRequest,
    api_key: dict = Depends(verify_api_key)  # ✅ Authentication required
):
    # ... existing code ...

# Webhook remains without auth (uses signature verification)
# Health check remains public
```

### Step 3: Update requirements.txt

Add:
```
python-multipart
```

### Step 4: Generate API Keys

```bash
# Run this to generate secure API keys
python3 -c "import secrets; print('API_KEY_1=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('API_KEY_2=' + secrets.token_urlsafe(32))"
```

Add to `.env`:
```bash
API_KEY_1=your-generated-key-here
API_KEY_2=another-generated-key-here
```

### Step 5: Test

```bash
# Without auth - should fail
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}'

# With auth - should work
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your-generated-key-here' \
  -d '{"email":"test@example.com"}'
```

---

## Fix #2: Add Rate Limiting

### Step 1: Install slowapi

Update `app/requirements.txt`:
```
slowapi==0.1.9
```

### Step 2: Add Rate Limiting

Update `app/main.py`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to endpoints
@app.post("/kyc/start", response_model=KycStartResponse)
@limiter.limit("10/minute")  # Max 10 verifications per minute per IP
async def kyc_start(request: Request, body: KycStartRequest, api_key: dict = Depends(verify_api_key)):
    # ... existing code ...

@app.post("/kyc/shuftipro/webhook")
@limiter.limit("100/minute")  # Higher limit for webhooks
async def shuftipro_webhook(request: Request):
    # ... existing code ...
```

### Step 3: Test Rate Limiting

```bash
# This script will trigger rate limit
for i in {1..15}; do
  curl -X POST http://localhost:8181/kyc/start \
    -H 'Authorization: Bearer your-api-key' \
    -H 'Content-Type: application/json' \
    -d '{"email":"test@example.com"}'
  echo ""
done
```

After 10 requests, you should see:
```json
{"error": "Rate limit exceeded: 10 per 1 minute"}
```

---

## Fix #3: Add IP Whitelisting for Webhooks

Update `app/main.py`:

```python
# ShuftiPro webhook IPs (from official docs)
SHUFTIPRO_IPS = {
    # Europe
    "142.132.144.101",
    "65.108.103.45",
    # United States
    "5.161.114.110",
    "5.161.87.219",
    "5.78.56.7",
    "5.78.58.196",
    # Add localhost for testing
    "127.0.0.1",
    "::1"
}

@app.post("/kyc/shuftipro/webhook")
async def shuftipro_webhook(request: Request):
    # IP whitelisting check
    client_ip = request.client.host
    
    # In production, enforce whitelist strictly
    if os.getenv("ENVIRONMENT") == "production" and client_ip not in SHUFTIPRO_IPS:
        logger.warning(f"Webhook attempt from unauthorized IP: {client_ip}")
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Invalid source IP"
        )
    
    # ... rest of webhook code ...
```

Add to `.env`:
```bash
ENVIRONMENT=development  # Change to 'production' in prod
```

---

## Fix #4: Add Health Check Endpoint

Add to `app/main.py`:

```python
from datetime import datetime

@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancer.
    Returns 200 if healthy, 503 if any dependency is down.
    """
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    
    all_healthy = True
    
    # Check Vault
    try:
        get_shuftipro_adapter()
        checks["checks"]["vault"] = "healthy"
    except Exception as e:
        checks["checks"]["vault"] = f"unhealthy: {str(e)}"
        all_healthy = False
    
    # Check DynamoDB
    try:
        table = get_table()
        table.table_status  # Force connection check
        checks["checks"]["dynamodb"] = "healthy"
    except Exception as e:
        checks["checks"]["dynamodb"] = f"unhealthy: {str(e)}"
        all_healthy = False
    
    # Check S3
    try:
        s3 = get_s3_storage()
        s3.client.head_bucket(Bucket=s3.bucket_name)
        checks["checks"]["s3"] = "healthy"
    except Exception as e:
        checks["checks"]["s3"] = f"unhealthy: {str(e)}"
        all_healthy = False
    
    if not all_healthy:
        checks["status"] = "unhealthy"
        return JSONResponse(status_code=503, content=checks)
    
    return checks

@app.get("/readiness")
async def readiness_check():
    """Kubernetes readiness probe - simpler check."""
    return {"status": "ready"}

@app.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe - just check if app is running."""
    return {"status": "alive"}
```

Test:
```bash
curl http://localhost:8181/health
curl http://localhost:8181/readiness
curl http://localhost:8181/liveness
```

---

## Fix #5: Add Request ID Tracking

Create `app/middleware.py`:

```python
"""
Request middleware for logging and tracking.
"""
import uuid
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable for request ID
request_id_var: ContextVar[str] = ContextVar('request_id', default='N/A')

class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request ID and timing to all requests."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        request_id_var.set(request_id)
        
        # Track request timing
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add headers to response
        response.headers['X-Request-ID'] = request_id
        response.headers['X-Process-Time'] = f"{duration:.3f}"
        
        # Log request
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": f"{duration * 1000:.2f}"
            }
        )
        
        return response


# Custom logging filter to add request ID
class RequestIDFilter(logging.Filter):
    """Add request ID to all log records."""
    
    def filter(self, record):
        record.request_id = request_id_var.get('N/A')
        return True
```

Update `app/main.py`:

```python
from middleware import RequestContextMiddleware, RequestIDFilter

# Add middleware
app.add_middleware(RequestContextMiddleware)

# Update logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(request_id)s] - %(name)s - %(levelname)s - %(message)s'
)

# Add filter to all handlers
for handler in logging.root.handlers:
    handler.addFilter(RequestIDFilter())
```

Now all logs will include request ID:
```
2025-12-06 10:30:15 - [abc-123-def-456] - app.main - INFO - Starting KYC verification
```

---

## Fix #6: Add Structured Error Responses

Create `app/exceptions.py`:

```python
"""
Custom exceptions and error handlers.
"""
from typing import Optional, Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class KYCException(Exception):
    """Base exception for KYC operations."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(KYCException):
    """Authentication failed."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTH_FAILED",
            status_code=401
        )


class AuthorizationError(KYCException):
    """Authorization failed."""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            status_code=403
        )


class ValidationError(KYCException):
    """Input validation error."""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class ResourceNotFoundError(KYCException):
    """Resource not found."""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            error_code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class ExternalServiceError(KYCException):
    """External service (ShuftiPro) error."""
    def __init__(self, service: str, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=f"{service} error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service, **(details or {})}
        )


async def kyc_exception_handler(request: Request, exc: KYCException):
    """Handle custom KYC exceptions."""
    logger.error(
        f"KYC exception: {exc.error_code} - {exc.message}",
        extra={"details": exc.details}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

Update `app/main.py`:

```python
from exceptions import (
    KYCException, ResourceNotFoundError, 
    kyc_exception_handler, generic_exception_handler
)

# Add exception handlers
app.add_exception_handler(KYCException, kyc_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Update endpoints to use custom exceptions
@app.get("/kyc/status/{reference}", response_model=KycStatusResponse)
async def kyc_status(reference: str, api_key: dict = Depends(verify_api_key)):
    item = get_kyc_session(reference)
    if not item:
        raise ResourceNotFoundError("KYC session", reference)  # ✅ Structured error
    
    return KycStatusResponse(...)
```

---

## Fix #7: Add Environment-Based Configuration

Create `app/settings.py`:

```python
"""
Application settings and configuration.
"""
from pydantic import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    environment: str = "development"  # development, staging, production
    debug: bool = True
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8181
    api_keys: List[str] = []
    
    # Vault
    vault_addr: str = "http://vault:8200"
    vault_token: str = "root"
    
    # DynamoDB
    dynamodb_endpoint: str = "http://dynamodb-local:8000"
    aws_region: str = "us-east-1"
    
    # S3/MinIO
    s3_endpoint: str = "http://minio:9000"
    s3_bucket_name: str = "kyc-documents"
    s3_force_path_style: bool = True
    
    # ShuftiPro
    shuftipro_callback_url: str = ""
    
    # Security
    enforce_ip_whitelist: bool = False  # Enable in production
    allowed_ips: List[str] = ["127.0.0.1", "::1"]
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Singleton settings instance
settings = Settings()
```

Update `app/main.py`:

```python
from settings import settings

# Use settings throughout app
if settings.debug:
    logger.setLevel(logging.DEBUG)

# Dynamic rate limiting
@app.post("/kyc/start")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def kyc_start(...):
    ...
```

---

## Testing the Fixes

### 1. Authentication Test
```bash
# Should fail (no auth)
curl -X POST http://localhost:8181/kyc/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}'

# Should succeed
curl -X POST http://localhost:8181/kyc/start \
  -H 'Authorization: Bearer your-api-key' \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@example.com"}'
```

### 2. Rate Limiting Test
```bash
# Run 15 times to trigger rate limit
for i in {1..15}; do
  curl -X POST http://localhost:8181/kyc/start \
    -H 'Authorization: Bearer your-api-key' \
    -H 'Content-Type: application/json' \
    -d '{"email":"test@example.com"}'
done
```

### 3. Health Check Test
```bash
curl http://localhost:8181/health | jq
```

### 4. Request ID Test
```bash
# Send with custom request ID
curl -H 'X-Request-ID: my-custom-id-123' \
  http://localhost:8181/health

# Check response headers
curl -I http://localhost:8181/health
```

---

## Deployment Checklist

Before deploying these fixes to production:

- [ ] Update `requirements.txt` with new dependencies
- [ ] Generate secure API keys (32+ characters)
- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Enable IP whitelisting (`enforce_ip_whitelist=true`)
- [ ] Test all endpoints with authentication
- [ ] Verify rate limiting works
- [ ] Check health endpoint returns correct status
- [ ] Review logs for request IDs
- [ ] Test error responses are structured
- [ ] Update API documentation with auth requirements

---

## Next Steps

After implementing these fixes:
1. Set up production Vault (non-dev mode)
2. Configure HTTPS with nginx/ALB
3. Migrate to AWS DynamoDB
4. Set up monitoring (CloudWatch, DataDog)
5. Implement automated tests
6. Conduct security audit
7. Load testing
8. Production deployment

**Estimated Implementation Time:** 2-3 days for all fixes
