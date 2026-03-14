"""입고분류 동적 관리 - DB에서 로드, 없으면 기본값 사용"""
import streamlit as st

DEFAULT_TYPES = [
    {"name": "용답매입",      "is_insurance": False},
    {"name": "용답데모",      "is_insurance": False},
    {"name": "일반-삼성보험", "is_insurance": True},
    {"name": "일반-KB보험",   "is_insurance": True},
    {"name": "일반-현대보험", "is_insurance": True},
    {"name": "일반-DB보험",   "is_insurance": True},
    {"name": "일반(자비)",    "is_insurance": False},
]


def get_intake_types(sb) -> list[dict]:
    """DB에서 입고분류 목록 로드. 테이블 없으면 기본값 반환."""
    try:
        rows = sb.table("intake_types") \
            .select("name, is_insurance, sort_order") \
            .eq("is_active", True) \
            .order("sort_order") \
            .execute().data or []
        return rows if rows else DEFAULT_TYPES
    except Exception:
        return DEFAULT_TYPES


def get_type_names(sb) -> list[str]:
    return [t["name"] for t in get_intake_types(sb)]


def is_insurance_type(sb, name: str) -> bool:
    types = get_intake_types(sb)
    for t in types:
        if t["name"] == name:
            return t.get("is_insurance", False)
    return "보험" in name


def add_intake_type(sb, name: str, is_insurance: bool) -> bool:
    """새 입고분류 추가. 성공 True, 중복 False."""
    try:
        existing = sb.table("intake_types").select("id").eq("name", name).execute().data
        if existing:
            return False
        max_order = sb.table("intake_types").select("sort_order").order("sort_order", desc=True).limit(1).execute().data
        next_order = (max_order[0]["sort_order"] + 1) if max_order else 10
        sb.table("intake_types").insert({
            "name": name,
            "is_insurance": is_insurance,
            "sort_order": next_order,
            "is_active": True,
        }).execute()
        return True
    except Exception as e:
        st.error(f"추가 실패: {e}")
        return False


def deactivate_intake_type(sb, name: str):
    """입고분류 비활성화 (삭제 대신)"""
    sb.table("intake_types").update({"is_active": False}).eq("name", name).execute()


def activate_intake_type(sb, name: str):
    """비활성화된 입고분류 재활성화"""
    sb.table("intake_types").update({"is_active": True}).eq("name", name).execute()


def get_inactive_types(sb) -> list[str]:
    """비활성화된 입고분류 목록 반환"""
    try:
        rows = sb.table("intake_types") \
            .select("name") \
            .eq("is_active", False) \
            .order("name") \
            .execute().data or []
        return [r["name"] for r in rows]
    except Exception:
        return []
