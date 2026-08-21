"""S3-compatible object storage.

Works with AWS S3, Cloudflare R2, Backblaze B2, MinIO and anything else
speaking the same API. Objects are written private; the browser receives
short-lived presigned URLs, so bucket credentials never leave the server.
"""

from __future__ import annotations

from functools import cached_property

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.base import StorageBackend, generate_key

logger = get_logger(__name__)


class S3Storage(StorageBackend):
    def __init__(self) -> None:
        self.bucket = settings.STORAGE_BUCKET

    @cached_property
    def client(self):
        import boto3
        from botocore.config import Config

        return boto3.client(
            "s3",
            endpoint_url=settings.STORAGE_ENDPOINT or None,
            region_name=settings.STORAGE_REGION,
            aws_access_key_id=settings.STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.STORAGE_SECRET_KEY,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )

    def save(self, data: bytes, *, prefix: str, content_type: str) -> str:
        key = generate_key(prefix, content_type)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="private, max-age=31536000",
        )
        return key

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            logger.warning("Could not delete object %s: %s", key, exc)

    def delete_prefix(self, prefix: str) -> None:
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix.strip("/")):
                keys = [{"Key": item["Key"]} for item in page.get("Contents", [])]
                if keys:
                    self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": keys})
        except Exception as exc:
            logger.warning("Could not delete prefix %s: %s", prefix, exc)

    def public_url(self, key: str, *, expires_in: int = 3600) -> str:
        # A CDN in front of a public bucket can skip signing entirely.
        if settings.STORAGE_PUBLIC_BASE_URL:
            return f"{settings.STORAGE_PUBLIC_BASE_URL.rstrip('/')}/{key}"
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except Exception as exc:
            logger.error("Could not sign URL for %s: %s", key, exc)
            return ""

    def read(self, key: str) -> bytes | None:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except Exception:
            return None

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False
