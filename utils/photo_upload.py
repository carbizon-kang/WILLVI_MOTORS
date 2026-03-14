"""Supabase Storage 사진 업로드"""
import uuid
from database.connection import get_supabase

BUCKET = "repair-photos"


def upload_photo(file_bytes: bytes, file_name: str, vehicle_id: str) -> str:
    """사진 업로드 → 공개 URL 반환"""
    sb = get_supabase()
    ext = file_name.split(".")[-1].lower()
    path = f"{vehicle_id}/{uuid.uuid4()}.{ext}"
    sb.storage.from_(BUCKET).upload(
        path, file_bytes, {"content-type": f"image/{ext}"}
    )
    public_url = sb.storage.from_(BUCKET).get_public_url(path)
    return public_url


def delete_photo(file_url: str):
    """Storage에서 사진 삭제"""
    sb = get_supabase()
    path = file_url.split(f"{BUCKET}/")[-1]
    sb.storage.from_(BUCKET).remove([path])
