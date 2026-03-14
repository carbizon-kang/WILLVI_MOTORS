import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

# 프로젝트 루트의 .env 파일을 명시적으로 로드
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

@st.cache_resource
def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        st.error("⚠️ .env 파일에 SUPABASE_URL과 SUPABASE_KEY를 설정하세요.")
        st.stop()
    return create_client(url, key)
