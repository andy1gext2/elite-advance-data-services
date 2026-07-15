"""S3 / S3-compatible (Cloudflare R2, MinIO, …) storage. The only place boto3 is
imported. Drops in for production by setting STORAGE_BACKEND=s3 + credentials."""
from __future__ import annotations

from app.core.config import Settings


class S3Storage:
    name = "s3"

    def __init__(self, settings: Settings) -> None:
        import boto3  # lazy

        self._bucket = settings.s3_bucket
        self._public_base = (settings.s3_public_base or "").rstrip("/")
        self._client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )
        if self._public_base:
            return f"{self._public_base}/{key}"
        return f"https://{self._bucket}.s3.amazonaws.com/{key}"

    def load(self, key: str) -> bytes | None:
        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
            return obj["Body"].read()
        except Exception:
            return None

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
