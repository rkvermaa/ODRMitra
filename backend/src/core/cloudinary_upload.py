"""Cloudinary upload utility for document storage."""

import cloudinary
import cloudinary.uploader
from io import BytesIO

from src.config import settings
from src.core.logging import log


def _configure():
    """Configure cloudinary from settings."""
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


async def upload_to_cloudinary(
    file_content: bytes,
    filename: str,
    folder: str = "odrmitra/documents",
    resource_type: str = "auto",
) -> dict:
    """Upload file to Cloudinary and return URL + metadata.

    Returns:
        dict with keys: url, public_id, resource_type, bytes, format
    """
    _configure()

    # Use "raw" for documents (PDF, DOCX, etc.) — "auto"/"image" causes 401 on download
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("pdf", "doc", "docx", "txt", "md", "csv", "xlsx", "xls"):
        resource_type = "raw"

    try:
        result = cloudinary.uploader.upload(
            BytesIO(file_content),
            folder=folder,
            public_id=filename.rsplit(".", 1)[0] if "." in filename else filename,
            resource_type=resource_type,
            overwrite=False,
            unique_filename=True,
            access_mode="public",
        )

        upload_result = {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "resource_type": result["resource_type"],
            "bytes": result["bytes"],
            "format": result.get("format", ""),
        }

        log.info(f"Uploaded to Cloudinary: {upload_result['public_id']}")
        return upload_result

    except Exception as e:
        log.error(f"Cloudinary upload failed: {e}")
        raise
