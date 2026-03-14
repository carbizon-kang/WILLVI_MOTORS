"""공통 CSS 스타일 - 전문 기업용 UI"""
import streamlit as st


def apply_global_style():
    st.markdown("""
    <style>
    /* ── 전체 배경 */
    .stApp { background-color: #F4F6F9; }

    /* ── 사이드바 */
    [data-testid="stSidebar"] {
        background-color: #1B2B4B !important;
        border-right: none;
    }
    [data-testid="stSidebar"] * { color: #CBD5E0 !important; }
    [data-testid="stSidebar"] .sidebar-title {
        color: #FFFFFF !important;
        font-size: 16px;
        font-weight: 700;
        padding: 16px 0 4px 0;
        border-bottom: 1px solid #2D4070;
        margin-bottom: 12px;
    }
    /* 라디오 버튼 메뉴 스타일 */
    [data-testid="stSidebar"] label {
        color: #CBD5E0 !important;
        font-size: 14px !important;
        padding: 6px 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {
        gap: 2px;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: transparent;
        border-radius: 6px;
        padding: 8px 12px !important;
        width: 100%;
        display: block;
        transition: background 0.15s;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(255,255,255,0.08) !important;
    }
    [data-testid="stSidebar"] [aria-checked="true"] + div label,
    [data-testid="stSidebar"] input:checked ~ label {
        background: rgba(27,143,255,0.2) !important;
        color: #FFFFFF !important;
    }

    /* ── 메인 콘텐츠 패딩 */
    .block-container { padding: 1.5rem 2rem !important; max-width: 1400px; }

    /* ── 페이지 제목 */
    .page-header {
        background: #FFFFFF;
        border-left: 4px solid #1B4F8A;
        padding: 14px 20px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .page-header h2 {
        margin: 0; font-size: 20px;
        color: #1B2B4B; font-weight: 700;
    }
    .page-header p { margin: 2px 0 0; font-size: 13px; color: #718096; }

    /* ── 카드 */
    .card {
        background: #FFFFFF;
        border-radius: 8px;
        padding: 18px 20px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
        margin-bottom: 16px;
    }
    .card-title {
        font-size: 13px; font-weight: 600;
        color: #718096; text-transform: uppercase;
        letter-spacing: 0.5px; margin-bottom: 8px;
    }

    /* ── 지표 카드 */
    .metric-card {
        background: #FFFFFF;
        border-radius: 8px;
        padding: 16px 18px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
        border-top: 3px solid #1B4F8A;
    }
    .metric-card.orange { border-top-color: #E67E22; }
    .metric-card.red    { border-top-color: #E53E3E; }
    .metric-card.green  { border-top-color: #38A169; }
    .metric-card.gray   { border-top-color: #A0AEC0; }
    .metric-label {
        font-size: 12px; color: #718096;
        font-weight: 600; margin-bottom: 6px;
    }
    .metric-value {
        font-size: 22px; font-weight: 700; color: #1A202C;
    }
    .metric-sub { font-size: 12px; color: #A0AEC0; margin-top: 4px; }

    /* ── 상태 뱃지 */
    .badge {
        display: inline-block;
        padding: 2px 10px; border-radius: 12px;
        font-size: 12px; font-weight: 600;
    }

    /* ── 섹션 제목 */
    .section-title {
        font-size: 14px; font-weight: 700;
        color: #2D3748; margin: 16px 0 10px;
        padding-bottom: 6px;
        border-bottom: 1px solid #E2E8F0;
    }

    /* ── 테이블 헤더 */
    thead tr th {
        background: #F7FAFC !important;
        color: #4A5568 !important;
        font-size: 12px !important;
        font-weight: 600 !important;
    }

    /* ── 버튼 */
    .stButton button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }

    /* ── 입력 필드 */
    .stTextInput input, .stSelectbox select, .stNumberInput input {
        border-radius: 6px !important;
        border: 1px solid #CBD5E0 !important;
        font-size: 14px !important;
    }

    /* ── Streamlit 기본 헤더 숨김 */
    #MainMenu { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f"""
    <div class="page-header">
        <h2>{title}</h2>{sub}
    </div>
    """, unsafe_allow_html=True)


def metric_card(label: str, value: str, sub: str = "", color: str = ""):
    cls = f"metric-card {color}" if color else "metric-card"
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="{cls}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {sub_html}
    </div>"""


def section_title(text: str):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def status_badge(status: str) -> str:
    colors = {
        '입고': ('#EBF5FB','#1B4F8A'), '진단': ('#FEFCE8','#B7791F'),
        '수리중': ('#F0FFF4','#276749'), '부품대기': ('#FFF5F5','#C53030'),
        '도장': ('#FAF5FF','#6B46C1'), '상품화': ('#E6FFFA','#2C7A7B'),
        '출고대기': ('#FFF3E0','#C05621'), '출고완료': ('#F7FAFC','#718096'),
    }
    bg, fg = colors.get(status, ('#F7FAFC','#718096'))
    return f"<span class='badge' style='background:{bg};color:{fg}'>{status}</span>"
