"""매출 관리 - 월별 매출 현황 및 분석"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database.connection import get_supabase
from utils.styles import apply_global_style, page_header, section_title
from utils.calculations import summarize_work_order, fmt_money, ENGINE_OIL_UNIT_PRICE
from utils.excel_export import export_sales_excel


def render():
    apply_global_style()
    page_header("매출 관리", "월별 매출 현황 및 분석")
    sb = get_supabase()

    # ── 기간 선택
    c1, c2, c3 = st.columns(3)
    today = date.today()
    year  = c1.selectbox("연도", list(range(2024, today.year + 2)), index=today.year - 2024)
    month = c2.selectbox("월", list(range(1, 13)), index=today.month - 1)
    f_type = c3.selectbox("입고분류 필터", [
        "전체", "용답매입", "용답데모",
        "일반-삼성보험", "일반-KB보험", "일반-현대보험", "일반-DB보험", "일반(자비)"
    ])

    ym_start = f"{year}-{month:02d}-01"
    if month == 12:
        ym_end = f"{year+1}-01-01"
    else:
        ym_end = f"{year}-{month+1:02d}-01"

    # ── 데이터 로드: 해당 월 출고 차량 기준
    q = sb.table("vehicles").select(
        "id, plate_number, model, intake_type, intake_date, actual_out, "
        "work_orders(parts_amount, engine_oil_liter, engine_oil_unit, "
        "towing_fee, insurance_fee, tech_fee, paint_amount, vat_rate, total_amount)"
    ).gte("actual_out", ym_start).lt("actual_out", ym_end)

    if f_type != "전체":
        q = q.eq("intake_type", f_type)

    vehicles = q.execute().data or []

    # ── 데이터 평탄화 (차량당 작업지시서 합산)
    rows = []
    for v in vehicles:
        orders = v.get("work_orders") or []
        if not orders:
            # 작업지시서 없는 차량도 행으로 포함
            rows.append({
                "plate_number": v.get("plate_number"),
                "model": v.get("model"),
                "intake_type": v.get("intake_type"),
                "intake_date": v.get("intake_date"),
                "actual_out": v.get("actual_out"),
                "parts_amount": 0, "engine_oil_liter": 0,
                "engine_oil_unit": ENGINE_OIL_UNIT_PRICE,
                "engine_oil_amount": 0, "towing_fee": 0,
                "insurance_fee": 0, "tech_fee": 0,
                "paint_amount": 0, "total_parts": 0,
                "vat_amount": 0, "total_amount": 0,
            })
            continue
        # 복수 작업지시서 합산
        agg = {k: 0 for k in [
            "parts_amount","engine_oil_liter","engine_oil_amount",
            "towing_fee","insurance_fee","tech_fee","paint_amount",
            "total_parts","vat_amount","total_amount"
        ]}
        agg["engine_oil_unit"] = ENGINE_OIL_UNIT_PRICE
        for o in orders:
            s = summarize_work_order(o)
            for key in agg:
                if key != "engine_oil_unit":
                    agg[key] += s.get(key, 0) or 0
        rows.append({
            "plate_number": v.get("plate_number"),
            "model": v.get("model"),
            "intake_type": v.get("intake_type"),
            "intake_date": v.get("intake_date"),
            "actual_out": v.get("actual_out"),
            **agg,
        })

    if not rows:
        st.info(f"{year}년 {month}월 출고 차량 데이터가 없습니다.")
        return

    # ── 합계 지표
    total_revenue = sum(r["total_amount"] for r in rows)
    total_tech    = sum(r["tech_fee"] for r in rows)
    total_parts   = sum(r["parts_amount"] for r in rows)
    total_oil     = sum(r["engine_oil_amount"] for r in rows)
    total_paint   = sum(r["paint_amount"] for r in rows)
    total_towing  = sum(r["towing_fee"] for r in rows)

    st.subheader(f"{year}년 {month}월 매출 요약 — 총 {len(rows)}건")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("총  계", fmt_money(total_revenue))
    m2.metric("기술료", fmt_money(total_tech))
    m3.metric("부품금액", fmt_money(total_parts))
    m4.metric("엔진오일", fmt_money(total_oil))
    m5.metric("도장금액", fmt_money(total_paint))

    # ── 엑셀 내보내기
    excel_bytes = export_sales_excel(rows, year, month)
    st.download_button(
        f"📥 {year}년 {month}월 매출내역서 다운로드",
        data=excel_bytes,
        file_name=f"{year}년{month:02d}월_매출내역서.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.divider()

    # ── 입고분류별 매출 차트
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("입고분류별 총계")
        type_agg = {}
        for r in rows:
            t = r["intake_type"] or "기타"
            type_agg[t] = type_agg.get(t, 0) + r["total_amount"]
        df_type = pd.DataFrame({"분류": list(type_agg.keys()), "금액": list(type_agg.values())})
        fig1 = px.pie(df_type, names="분류", values="금액", hole=0.35)
        fig1.update_layout(height=300, margin=dict(t=10,b=10))
        st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        st.subheader("매출 구성")
        df_comp = pd.DataFrame({
            "항목": ["기술료", "부품금액", "엔진오일", "견인비", "도장금액"],
            "금액": [total_tech, total_parts, total_oil, total_towing, total_paint],
        })
        fig2 = px.bar(df_comp, x="항목", y="금액", text="금액",
                      color_discrete_sequence=["#1F4E79"])
        fig2.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig2.update_layout(height=300, margin=dict(t=10,b=10), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # ── 상세 테이블 (실무 매출내역서 형식)
    st.subheader("상세 내역")
    df_detail = pd.DataFrame([{
        "No": i+1,
        "입고일": r["intake_date"],
        "출고일": r["actual_out"],
        "입고분류": r["intake_type"],
        "차량번호": r["plate_number"],
        "차량모델": r["model"],
        "부품금액": r["parts_amount"],
        "견인비": r["towing_fee"],
        "보험료": r["insurance_fee"],
        "엔진오일(L)": r["engine_oil_liter"],
        "엔진오일금액": r["engine_oil_amount"],
        "총부품금액": r["total_parts"],
        "기술료": r["tech_fee"],
        "부가세": r["vat_amount"],
        "총계": r["total_amount"],
        "도장금액": r["paint_amount"],
    } for i, r in enumerate(rows)])

    money_cols = ["부품금액","견인비","보험료","엔진오일금액","총부품금액","기술료","부가세","총계","도장금액"]
    st.dataframe(
        df_detail.style.format({c: "{:,.0f}" for c in money_cols if c in df_detail.columns}),
        use_container_width=True,
        height=400,
    )
