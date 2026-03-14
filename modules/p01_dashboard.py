"""대시보드 - 기업용 현황판"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from database.connection import get_supabase
from utils.calculations import fmt_money
from utils.styles import apply_global_style, page_header, metric_card, section_title, status_badge

STATUS_ORDER = ['입고', '진단', '수리중', '부품대기', '도장', '상품화', '출고대기', '출고완료']
STATUS_COLOR = {
    '입고': '#3182CE', '진단': '#D69E2E', '수리중': '#38A169',
    '부품대기': '#E53E3E', '도장': '#805AD5', '상품화': '#2C7A7B',
    '출고대기': '#DD6B20', '출고완료': '#A0AEC0'
}


def render():
    apply_global_style()
    page_header("대시보드", f"기준일: {date.today().strftime('%Y년 %m월 %d일')} (차량 입출고 현황)")

    sb = get_supabase()

    # ── 데이터 로드
    vehicles = sb.table("vehicles").select("*").execute().data or []
    today = date.today().isoformat()
    today_in    = [v for v in vehicles if v.get("intake_date") == today]
    today_out   = [v for v in vehicles if v.get("expected_out") == today and v.get("status") != "출고완료"]
    active      = [v for v in vehicles if v.get("status") != "출고완료"]
    waiting_out = [v for v in vehicles if v.get("status") == "출고대기"]

    ym = date.today().strftime("%Y-%m")
    orders_this_month = sb.table("work_orders") \
        .select("total_amount, paint_amount, tech_fee, parts_amount") \
        .gte("created_at", f"{ym}-01").execute().data or []
    total_revenue = sum(r.get("total_amount") or 0 for r in orders_this_month)
    total_tech    = sum(r.get("tech_fee") or 0 for r in orders_this_month)
    total_parts   = sum(r.get("parts_amount") or 0 for r in orders_this_month)
    total_paint   = sum(r.get("paint_amount") or 0 for r in orders_this_month)

    claims = sb.table("insurance_claims") \
        .select("claim_amount, paid_amount, status") \
        .neq("status", "입금완료").execute().data or []
    unpaid_cnt = len(claims)
    unpaid_amt = sum((r.get("claim_amount") or 0) - (r.get("paid_amount") or 0) for r in claims)

    # ── 핵심 지표 (6개 카드)
    cols = st.columns(6)
    cards = [
        ("입고 차량 (전체)", f"{len(active)}대", "", ""),
        ("오늘 입고", f"{len(today_in)}대", "", "green" if today_in else "gray"),
        ("오늘 출고 예정", f"{len(today_out)}대", "", "orange" if today_out else "gray"),
        ("출고 대기", f"{len(waiting_out)}대", "출고 처리 필요" if waiting_out else "없음", "orange" if waiting_out else "gray"),
        ("이번달 매출", fmt_money(total_revenue), f"{len(orders_this_month)}건", "green"),
        ("보험 미수금", fmt_money(unpaid_amt), f"{unpaid_cnt}건 미처리" if unpaid_cnt else "전건 처리", "red" if unpaid_cnt else "gray"),
    ]
    for col, (label, val, sub, color) in zip(cols, cards):
        with col:
            st.markdown(metric_card(label, val, sub, color), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 상태별 차트 + 출고 대기 목록
    col_chart, col_right = st.columns([1.4, 1])

    with col_chart:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        section_title("차량 상태별 현황")
        status_cnt = {}
        for v in active:
            s = v.get("status","입고")
            status_cnt[s] = status_cnt.get(s, 0) + 1

        if status_cnt:
            df_s = pd.DataFrame([
                {"상태": s, "대수": status_cnt.get(s, 0)}
                for s in STATUS_ORDER if s != "출고완료"
            ])
            fig = go.Figure(go.Bar(
                x=df_s["상태"], y=df_s["대수"],
                marker_color=[STATUS_COLOR.get(s, "#ccc") for s in df_s["상태"]],
                text=df_s["대수"], textposition="outside",
                textfont=dict(size=13, color="#2D3748"),
            ))
            fig.update_layout(
                height=260, margin=dict(t=10, b=10, l=0, r=0),
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#4A5568")),
                yaxis=dict(showgrid=True, gridcolor="#EDF2F7", zeroline=False, tickfont=dict(size=11)),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("현재 입고 차량이 없습니다.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="card">', unsafe_allow_html=True)

        tab1, tab2 = st.tabs([f"출고 예정 ({len(today_out)}건)", f"출고 대기 ({len(waiting_out)}건)"])

        with tab1:
            section_title("오늘 출고 예정 차량")
            if today_out:
                for v in today_out:
                    st.markdown(
                        f"<div style='padding:8px 0;border-bottom:1px solid #EDF2F7'>"
                        f"<b style='color:#1A202C'>{v.get('plate_number','')}</b>"
                        f"<span style='color:#718096;margin-left:8px;font-size:13px'>{v.get('model','')}</span><br>"
                        f"{status_badge(v.get('status',''))} "
                        f"<span style='font-size:12px;color:#A0AEC0'>{v.get('intake_type','')}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.markdown("<p style='color:#A0AEC0;font-size:13px;padding:12px 0'>오늘 출고 예정 차량이 없습니다.</p>",
                            unsafe_allow_html=True)

        with tab2:
            section_title("출고 대기 차량")
            if waiting_out:
                for v in waiting_out:
                    exp = v.get("expected_out","") or "-"
                    st.markdown(
                        f"<div style='padding:8px 0;border-bottom:1px solid #EDF2F7'>"
                        f"<b style='color:#1A202C'>{v.get('plate_number','')}</b>"
                        f"<span style='color:#718096;margin-left:8px;font-size:13px'>{v.get('model','')}</span><br>"
                        f"<span style='font-size:12px;color:#A0AEC0'>{v.get('intake_type','')} | 예정: {exp}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.markdown("<p style='color:#A0AEC0;font-size:13px;padding:12px 0'>출고 대기 차량이 없습니다.</p>",
                            unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 매출 요약 + 최근 입고 목록
    col_rev, col_list = st.columns([1, 1.6])

    with col_rev:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        section_title(f"이번달 매출 구성 ({date.today().month}월)")
        if orders_this_month:
            df_rev = pd.DataFrame({
                "항목": ["기술료", "부품", "도장"],
                "금액": [total_tech, total_parts, total_paint]
            })
            fig2 = go.Figure(go.Pie(
                labels=df_rev["항목"], values=df_rev["금액"],
                hole=0.5,
                marker=dict(colors=["#3182CE","#38A169","#805AD5"]),
                textfont=dict(size=12),
            ))
            fig2.update_layout(
                height=220, margin=dict(t=0, b=0, l=0, r=0),
                paper_bgcolor="#FFFFFF",
                legend=dict(orientation="h", y=-0.1, font=dict(size=11)),
                annotations=[dict(text=fmt_money(total_revenue), x=0.5, y=0.5,
                                  font=dict(size=13, color="#2D3748", family="sans-serif"),
                                  showarrow=False)]
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.markdown("<p style='color:#A0AEC0;font-size:13px;padding:24px 0'>매출 데이터가 없습니다.</p>",
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_list:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        section_title("최근 입고 차량 (10건)")
        recent = sorted(vehicles, key=lambda x: x.get("intake_date",""), reverse=True)[:10]
        if recent:
            rows = []
            for v in recent:
                rows.append({
                    "상태": v.get("status",""),
                    "차량번호": v.get("plate_number",""),
                    "모델": v.get("model","") or "-",
                    "입고분류": v.get("intake_type",""),
                    "입고일": v.get("intake_date",""),
                    "출고예정": v.get("expected_out","") or "-",
                })
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True, hide_index=True, height=240,
            )
        else:
            st.markdown("<p style='color:#A0AEC0;font-size:13px;padding:24px 0'>차량 데이터가 없습니다.</p>",
                        unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Kanban
    st.markdown('<div class="card">', unsafe_allow_html=True)
    section_title("작업 현황판 (Kanban)")
    kanban_statuses = [s for s in STATUS_ORDER if s != "출고완료"]
    kanban_cols = st.columns(len(kanban_statuses))

    for col, status in zip(kanban_cols, kanban_statuses):
        cards_v = [v for v in active if v.get("status") == status]
        color = STATUS_COLOR.get(status, "#ccc")
        with col:
            st.markdown(
                f"<div style='background:{color};color:white;padding:6px 8px;"
                f"border-radius:6px;text-align:center;font-size:12px;"
                f"font-weight:700;margin-bottom:8px'>"
                f"{status}<br><span style='font-size:18px'>{len(cards_v)}</span></div>",
                unsafe_allow_html=True
            )
            for v in cards_v:
                st.markdown(
                    f"<div style='background:#F7FAFC;border:1px solid #E2E8F0;"
                    f"border-radius:6px;padding:8px;margin-bottom:6px;font-size:12px'>"
                    f"<b style='color:#1A202C'>{v.get('plate_number','')}</b><br>"
                    f"<span style='color:#718096'>{v.get('model','') or '-'}</span><br>"
                    f"<span style='color:#A0AEC0;font-size:11px'>{v.get('intake_type','')}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    st.markdown('</div>', unsafe_allow_html=True)
