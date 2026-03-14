import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

# 로컬 .env 로드 (Streamlit Cloud에서는 무시됨)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)


def _get_secret(key: str) -> str:
    """Streamlit secrets → 환경변수 순으로 값을 읽음"""
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, "")


@st.cache_resource
def get_supabase() -> Client:
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_ANON_KEY")
    if not url or not key:
        st.error("⚠️ SUPABASE_URL과 SUPABASE_ANON_KEY를 설정하세요.")
        st.stop()
    return create_client(url, key)


@st.cache_resource
def get_supabase_admin() -> Client:
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return get_supabase()
    return create_client(url, key)
