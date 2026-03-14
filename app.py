"""WILLVI MOTORS VMS - 메인 진입점"""
import importlib
import streamlit as st
from utils.styles import apply_global_style

st.set_page_config(
    page_title="WILLVI MOTORS VMS",
    page_icon="assets/favicon.ico" if False else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_style()

PAGES = {
    "대시보드":      "modules.p01_dashboard",
    "차량 입고 등록": "modules.p02_vehicle_intake",
    "차량 현황":     "modules.p03_vehicle_list",
    "작업지시서":    "modules.p04_work_orders",
    "매출 관리":     "modules.p05_sales_report",
    "보험 청구":     "modules.p06_insurance_claims",
    "고객 관리":     "modules.p07_customers",
    "부품 재고":     "modules.p08_parts",
    "사진 관리":     "modules.p09_photos",
}

ICONS = {
    "대시보드":      "◈",
    "차량 입고 등록": "↓",
    "차량 현황":     "≡",
    "작업지시서":    "✎",
    "매출 관리":     "₩",
    "보험 청구":     "■",
    "고객 관리":     "◉",
    "부품 재고":     "▦",
    "사진 관리":     "▣",
}

# ── 사이드바
with st.sidebar:
    st.markdown("""
    <div style='padding:20px 16px 12px'>
        <div style='font-size:11px;color:#4A6FA5;font-weight:700;letter-spacing:2px;margin-bottom:4px'>
            WILLVI GROUP
        </div>
        <div style='font-size:18px;color:#FFFFFF;font-weight:800;letter-spacing:1px'>
            WILLVI MOTORS
        </div>
        <div style='font-size:11px;color:#718096;margin-top:2px'>차량 통합 관리 시스템</div>
    </div>
    <hr style='border:none;border-top:1px solid #2D4070;margin:0 16px 12px'>
    """, unsafe_allow_html=True)

    _page_list = list(PAGES.keys())
    _default_idx = 0
    if "_goto_page" in st.session_state:
        _goto = st.session_state.pop("_goto_page")
        if _goto in _page_list:
            _default_idx = _page_list.index(_goto)

    selected = st.radio(
        "메뉴",
        _page_list,
        index=_default_idx,
        label_visibility="collapsed",
        format_func=lambda x: f"  {ICONS.get(x,'')}  {x}",
    )

    st.markdown("""
    <hr style='border:none;border-top:1px solid #2D4070;margin:16px 16px 8px'>
    <div style='padding:0 16px 16px;font-size:11px;color:#4A5568'>
        v1.0.0 &nbsp;|&nbsp; WILLVI RPA<br>
        <span style='color:#2D4070'>© 2026 WILLVI GROUP</span>
    </div>
    """, unsafe_allow_html=True)

# ── 페이지 렌더링
mod_name = PAGES[selected]
try:
    mod = importlib.import_module(mod_name)
    mod.render()
except Exception as e:
    st.error(f"페이지 오류: {e}")
    st.exception(e)
