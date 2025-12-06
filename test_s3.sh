#!/bin/bash

echo "=========================================="
echo "MinIO S3 Storage Test"
echo "=========================================="
echo ""

# Test S3 connectivity from app container
echo "1. Testing S3 connection from app container..."
docker exec kyc-api python3 -c "
from storage.s3 import get_s3_storage
try:
    s3 = get_s3_storage()
    print(f'✅ S3 client initialized: {s3.endpoint}')
    print(f'   Bucket: {s3.bucket_name}')
    
    # List buckets
    buckets = s3.client.list_buckets()
    print(f'   Available buckets: {[b[\"Name\"] for b in buckets.get(\"Buckets\", [])]}')
    
    # Upload test file
    test_key = 'test/hello.txt'
    s3.upload_file(
        file_content=b'Hello from MinIO!',
        key=test_key,
        content_type='text/plain'
    )
    print(f'✅ Uploaded test file: {test_key}')
    
    # List files
    files = s3.list_files(prefix='test/')
    print(f'   Files in test/: {files}')
    
    # Generate presigned URL
    url = s3.get_object_url(test_key)
    print(f'✅ Generated presigned URL (valid for 1 hour)')
    
    print('')
    print('✅ All S3 operations successful!')
except Exception as e:
    print(f'❌ S3 test failed: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "=========================================="
echo "2. MinIO Console Access"
echo "=========================================="
echo ""
echo "Open MinIO Console in your browser:"
echo "  URL: http://localhost:9001"
echo "  Username: minioadmin"
echo "  Password: minioadmin"
echo ""
echo "You can view/manage the 'kyc-documents' bucket there."
echo ""
echo "=========================================="
echo "3. S3 API Endpoint"
echo "=========================================="
echo ""
echo "S3 API endpoint: http://localhost:9000"
echo "Bucket: kyc-documents"
echo ""
echo "To use with AWS CLI:"
echo "  aws --endpoint-url http://localhost:9000 s3 ls s3://kyc-documents/"
echo ""
