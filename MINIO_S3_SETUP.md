# MinIO S3 Storage Integration

Complete guide for using MinIO as S3-compatible object storage for KYC documents.

## 🎯 Overview

**MinIO** is integrated into the Docker Compose stack to provide **S3-compatible object storage** for KYC verification documents. When webhooks are received from ShuftiPro with document URLs, the system:

1. Downloads documents from ShuftiPro
2. **Uploads to MinIO/S3** (primary storage)
3. Saves local backup copy (secondary)
4. Stores S3 keys in DynamoDB

## 🏗️ Architecture

```
ShuftiPro Webhook → App downloads documents
                  ↓
        ┌─────────┴──────────┐
        ↓                    ↓
    MinIO/S3          Local Backup
  (primary storage)   (/app/documents)
        ↓
    S3 keys stored
    in DynamoDB
```

## 📦 Services

### MinIO Server
- **Port 9000**: S3 API endpoint
- **Port 9001**: MinIO Console (web UI)
- **Volume**: `minio-data` (persistent storage)
- **Bucket**: `kyc-documents` (auto-created)

### MinIO Init Container
- Automatically creates the `kyc-documents` bucket on startup
- Sets download permissions

## 🚀 Quick Start

### 1. Start All Services
```bash
docker compose up -d
```

This starts:
- **MinIO** (S3 storage)
- **Vault** (secrets)
- **DynamoDB** (metadata)
- **KYC API** (application)
- **Cloudflare Tunnel** (webhooks)

### 2. Access MinIO Console
Open in your browser:
- **URL**: http://localhost:9001
- **Username**: `minioadmin`
- **Password**: `minioadmin`

You'll see the `kyc-documents` bucket ready to use.

### 3. Test S3 Integration
```bash
./test_s3.sh
```

This script tests:
- S3 client initialization
- Bucket creation
- File upload/download
- Presigned URL generation

## 📡 API Endpoints

### List Documents for a User
```bash
GET /kyc/documents/{user_id}
```

**Example:**
```bash
curl http://localhost:8181/kyc/documents/user-123 | jq
```

**Response:**
```json
{
  "user_id": "user-123",
  "count": 2,
  "documents": [
    {
      "key": "documents/user-123/passport_front.jpg",
      "filename": "passport_front.jpg",
      "url": "http://minio:9000/kyc-documents/documents/user-123/passport_front.jpg?...",
      "expires_in": "1 hour"
    },
    {
      "key": "documents/user-123/selfie.jpg",
      "filename": "selfie.jpg",
      "url": "http://minio:9000/kyc-documents/documents/user-123/selfie.jpg?...",
      "expires_in": "1 hour"
    }
  ]
}
```

### Get Specific Document URL
```bash
GET /kyc/documents/{user_id}/{filename}?expires_in=3600
```

**Example:**
```bash
curl "http://localhost:8181/kyc/documents/user-123/passport_front.jpg" | jq
```

**Response:**
```json
{
  "user_id": "user-123",
  "filename": "passport_front.jpg",
  "url": "http://minio:9000/kyc-documents/documents/user-123/passport_front.jpg?...",
  "expires_in_seconds": 3600
}
```

## 🔧 Configuration

### Environment Variables (in docker-compose.yml)

```yaml
environment:
  # S3/MinIO Configuration
  S3_ENDPOINT: "http://minio:9000"         # Internal Docker network
  S3_ACCESS_KEY: "minioadmin"              # Dev credentials
  S3_SECRET_KEY: "minioadmin"              # Dev credentials
  S3_BUCKET_NAME: "kyc-documents"          # Bucket name
  S3_FORCE_PATH_STYLE: "true"              # MinIO path-style URLs
```

### Storage Module (`app/storage/s3.py`)

The S3 storage module provides:
- `upload_file()` - Upload file to S3
- `get_object_url()` - Generate presigned URL
- `delete_file()` - Delete file from S3
- `list_files()` - List files with prefix

**Example usage:**
```python
from storage.s3 import get_s3_storage

s3 = get_s3_storage()

# Upload
s3.upload_file(
    file_content=b"hello",
    key="documents/user-123/test.txt",
    content_type="text/plain"
)

# Get URL
url = s3.get_object_url("documents/user-123/test.txt", expires_in=3600)

# List files
files = s3.list_files(prefix="documents/user-123/")
```

## 🔄 Document Flow

### When Webhook Arrives

1. **Webhook received** with document URLs
2. **Download** from ShuftiPro URLs
3. **Upload to S3**:
   - Key: `documents/{user_id}/{filename}`
   - Example: `documents/user-123/passport_front.jpg`
4. **Save local backup**: `/app/documents/{user_id}/{filename}`
5. **Store S3 key** in DynamoDB session

### Fallback Behavior

If S3 is unavailable:
- Falls back to **local filesystem only**
- Logs warning
- Continues operation

## 🛠️ AWS CLI Usage

### Configure AWS CLI for MinIO
```bash
aws configure set aws_access_key_id minioadmin
aws configure set aws_secret_access_key minioadmin
aws configure set default.region us-east-1
```

### List Buckets
```bash
aws --endpoint-url http://localhost:9000 s3 ls
```

### List Objects in Bucket
```bash
aws --endpoint-url http://localhost:9000 s3 ls s3://kyc-documents/
aws --endpoint-url http://localhost:9000 s3 ls s3://kyc-documents/documents/
```

### Upload File
```bash
aws --endpoint-url http://localhost:9000 s3 cp test.txt s3://kyc-documents/test/test.txt
```

### Download File
```bash
aws --endpoint-url http://localhost:9000 s3 cp s3://kyc-documents/test/test.txt downloaded.txt
```

### Delete File
```bash
aws --endpoint-url http://localhost:9000 s3 rm s3://kyc-documents/test/test.txt
```

## 🔍 MinIO Client (mc)

### Install MinIO Client
```bash
# Linux
curl https://dl.min.io/client/mc/release/linux-amd64/mc \
  --create-dirs -o $HOME/minio-binaries/mc
chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

# macOS
brew install minio/stable/mc
```

### Configure Alias
```bash
mc alias set local http://localhost:9000 minioadmin minioadmin
```

### Common Commands
```bash
# List buckets
mc ls local

# List objects
mc ls local/kyc-documents

# Copy file
mc cp test.txt local/kyc-documents/test/test.txt

# Mirror directory
mc mirror ./documents local/kyc-documents/backup/

# Get bucket size
mc du local/kyc-documents
```

## 📊 Monitoring

### Check MinIO Status
```bash
docker compose ps minio
docker compose logs minio -f
```

### View Storage Usage
Open MinIO Console: http://localhost:9001
- Dashboard shows storage usage
- Browse bucket contents
- View access logs

### API Health Check
```bash
curl http://localhost:9000/minio/health/ready
```

## 🔐 Security Notes

### Development (Current Setup)
- ⚠️ **Default credentials**: `minioadmin/minioadmin`
- ⚠️ **Public bucket**: Download access enabled
- ✅ **Local network only**: Not exposed externally

### Production Recommendations

1. **Change credentials**:
   ```yaml
   environment:
     MINIO_ROOT_USER: "your-secure-username"
     MINIO_ROOT_PASSWORD: "your-secure-password-min-8-chars"
   ```

2. **Use IAM policies**:
   - Create dedicated user for app
   - Limit bucket access
   - Enable versioning

3. **Enable TLS**:
   ```yaml
   command: server /data --console-address ":9001" --certs-dir /certs
   ```

4. **Bucket policies**:
   - Remove public download access
   - Use presigned URLs only
   - Set expiration times

## 🧹 Maintenance

### Clear All Documents
```bash
# Using mc
mc rm --recursive --force local/kyc-documents/documents/

# Using AWS CLI
aws --endpoint-url http://localhost:9000 s3 rm s3://kyc-documents/documents/ --recursive
```

### Backup Bucket
```bash
# Export to local
mc mirror local/kyc-documents ./backup-$(date +%Y%m%d)/

# Or use AWS CLI
aws --endpoint-url http://localhost:9000 s3 sync s3://kyc-documents ./backup-$(date +%Y%m%d)/
```

### Reset MinIO
```bash
# Stop services
docker compose down

# Remove volume
docker volume rm shuftipro_minio-data

# Restart
docker compose up -d
```

## 📈 Scaling

### Production S3 Migration

To migrate from MinIO to AWS S3:

1. **Update environment variables**:
   ```yaml
   S3_ENDPOINT: ""  # Leave empty for AWS S3
   S3_ACCESS_KEY: "AWS_ACCESS_KEY_ID"
   S3_SECRET_KEY: "AWS_SECRET_ACCESS_KEY"
   S3_BUCKET_NAME: "your-production-bucket"
   AWS_REGION: "us-east-1"
   S3_FORCE_PATH_STYLE: "false"
   ```

2. **Create S3 bucket**:
   ```bash
   aws s3 mb s3://your-production-bucket
   ```

3. **No code changes needed** - the app works with any S3-compatible storage!

## 🐛 Troubleshooting

### MinIO not starting
```bash
docker compose logs minio
# Check for port conflicts on 9000 or 9001
```

### App can't connect to MinIO
```bash
# Test connectivity from app container
docker exec kyc-api curl -I http://minio:9000/minio/health/ready

# Check environment variables
docker exec kyc-api env | grep S3_
```

### Files not uploading
```bash
# Check app logs
docker compose logs app -f

# Verify bucket exists
mc ls local/
```

### Bucket not created
```bash
# Check minio-init logs
docker compose logs minio-init

# Manually create bucket
docker exec kyc-api python3 -c "from storage.s3 import get_s3_storage; get_s3_storage()"
```

## 📚 Resources

- **MinIO Documentation**: https://min.io/docs/minio/linux/index.html
- **S3 API Reference**: https://docs.aws.amazon.com/s3/
- **Boto3 S3 Guide**: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3.html

---

**Quick Commands:**
```bash
# Start services
docker compose up -d

# Test S3
./test_s3.sh

# View MinIO Console
open http://localhost:9001

# List documents API
curl http://localhost:8181/kyc/documents/user-123 | jq
```
