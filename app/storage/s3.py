"""
S3/MinIO storage module for KYC documents.
"""
import os
import logging
from typing import Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Storage:
    """S3-compatible storage client (works with MinIO)."""
    
    def __init__(self):
        self.endpoint = os.getenv("S3_ENDPOINT")
        self.access_key = os.getenv("S3_ACCESS_KEY")
        self.secret_key = os.getenv("S3_SECRET_KEY")
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "kyc-documents")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.force_path_style = os.getenv("S3_FORCE_PATH_STYLE", "true").lower() == "true"
        
        # Public endpoint for presigned URLs (defaults to internal endpoint if not set)
        self.public_endpoint = os.getenv("S3_PUBLIC_ENDPOINT", self.endpoint)
        
        if not all([self.endpoint, self.access_key, self.secret_key]):
            raise ValueError("S3 configuration incomplete: S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY required")
        
        # Create S3 client for internal operations (upload, delete, list)
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(
                s3={'addressing_style': 'path'} if self.force_path_style else None,
                signature_version='s3v4'
            )
        )
        
        # Create separate client for presigned URLs with public endpoint
        self.public_client = boto3.client(
            "s3",
            endpoint_url=self.public_endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(
                s3={'addressing_style': 'path'} if self.force_path_style else None,
                signature_version='s3v4'
            )
        )
        
        logger.info(f"S3Storage initialized: endpoint={self.endpoint}, public_endpoint={self.public_endpoint}, bucket={self.bucket_name}")
    
    def upload_file(self, file_content: bytes, key: str, content_type: Optional[str] = None) -> str:
        """
        Upload file to S3/MinIO.
        
        Args:
            file_content: File content as bytes
            key: S3 object key (path)
            content_type: Optional content type
            
        Returns:
            S3 object key
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                **extra_args
            )
            
            logger.info(f"Uploaded file to S3: {key}")
            return key
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise
    
    def get_object_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate presigned URL for S3 object using public endpoint.
        
        Args:
            key: S3 object key
            expires_in: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL accessible from outside Docker network
        """
        try:
            # Use public_client for presigned URLs so they work from external access
            url = self.public_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    
    def delete_file(self, key: str) -> bool:
        """
        Delete file from S3/MinIO.
        
        Args:
            key: S3 object key
            
        Returns:
            True if successful
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.info(f"Deleted file from S3: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> list:
        """
        List files in S3 bucket with optional prefix.
        
        Args:
            prefix: Optional prefix to filter objects
            
        Returns:
            List of object keys
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            return [obj['Key'] for obj in response['Contents']]
        except ClientError as e:
            logger.error(f"Failed to list files from S3: {e}")
            return []


# Singleton instance
_s3_storage: Optional[S3Storage] = None


def get_s3_storage() -> S3Storage:
    """Get or create S3Storage singleton instance."""
    global _s3_storage
    if _s3_storage is None:
        _s3_storage = S3Storage()
    return _s3_storage
