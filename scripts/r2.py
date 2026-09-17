"""
Cloudflare R2 上傳
R2 相容 S3 API，用 boto3 操作最穩定。
需要環境變數：
  R2_ACCOUNT_ID       Cloudflare 帳號 ID（Dashboard 右下角）
  R2_ACCESS_KEY_ID    R2 API Token 的 Access Key
  R2_SECRET_ACCESS_KEY
  R2_BUCKET_NAME      bucket 名稱
  R2_PUBLIC_URL       公開訪問根 URL（含 https://，不含結尾 /）
"""
import logging, os
from pathlib import Path

import boto3
from botocore.config import Config

log = logging.getLogger(__name__)

def _client():
    acct = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{acct}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )

def upload_file(local_path: str, key: str, content_type: str) -> None:
    """上傳本地文件到 R2"""
    bucket = os.environ["R2_BUCKET_NAME"]
    size   = Path(local_path).stat().st_size
    log.info(f"   上傳 {key} ({size//1024} KB)...")
    _client().upload_file(
        local_path, bucket, key,
        ExtraArgs={
            "ContentType": content_type,
            "CacheControl": "public, max-age=86400",
        },
    )
    log.info(f"   ✓ {key}")

def upload_text(content: str, key: str, content_type: str) -> None:
    """上傳字符串到 R2（用於 feed.xml）"""
    bucket = os.environ["R2_BUCKET_NAME"]
    _client().put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType=content_type,
        CacheControl="public, max-age=300",   # RSS 5分鐘緩存
    )
    log.info(f"   ✓ {key} ({len(content)} bytes)")

def download_text(key: str) -> str | None:
    """從 R2 下載文字（用於讀取現有 feed.xml）"""
    bucket = os.environ["R2_BUCKET_NAME"]
    try:
        resp = _client().get_object(Bucket=bucket, Key=key)
        return resp["Body"].read().decode("utf-8")
    except _client().exceptions.NoSuchKey:
        return None
    except Exception as ex:
        log.warning(f"   下載 {key} 失敗: {ex}")
        return None
