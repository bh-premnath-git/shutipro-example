"""
Storage module for KYC documents.
Supports both local filesystem and S3/MinIO storage.
"""
from .s3 import S3Storage, get_s3_storage

__all__ = ["S3Storage", "get_s3_storage"]
