"""보험 청구 관리"""
import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_supabase
from utils.styles import apply_global_style, page_header, section_title
from utils.calculations import fmt_money

INSURANCE_COS = ['삼성화재', 'KB손보', '현대해상', 'DB손보', '기타']
CLAIM_STATUS  = ['청구전', '청구완료', '입금완료']


def render():
    st.title("🏦 보험 청구 관리")
    sb = get_supabase()

    # ── 필터
    fc1, fc2 = st.columns(2)
    f_co     = fc1.selectbox("보험사", ["전체"] + INSURANCE_COS)
    f_status = fc2.selectbox("상태", ["전체"] + CLAIM_STATUS)

    q = sb.table("insurance_claims").select(
        "*, vehicles(plate_number, model, intake_date)"
    ).order("created_at", desc=True)
    if f_co != "전체":
        q = q.eq("insurance_co", f_co)
    if f_status != "전체":
        q = q.eq("status", f_status)

    claims = q.execute().data or []

    # ── 요약 지표
    total_claim  = sum(c.get("claim_amount") or 0 for c in claims)
    total_paid   = sum(c.get("paid_amount") or 0 for c in claims)
    total_unpaid = total_claim - total_paid
    pending_cnt  = sum(1 for c in claims if c.get("status") != "입금완료")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("청구 건수", f"{len(claims)}건")
    m2.metric("총 청구금액", fmt_money(total_claim))
    m3.metric("총 입금액", fmt_money(total_paid))
    m4.metric("미수금", fmt_money(total_unpaid), delta=f"-{pending_cnt}건 미처리",
              delta_color="inverse" if pending_cnt else "off")

    st.divider()

    # ── 청구 목록
    rows = []
    for c in claims:
        v = c.get("vehicles") or {}
        rows.append({
            "상태": c.get("status",""),
            "차량번호": v.get("plate_number",""),
            "모델": v.get("model",""),
            "입고일": v.get("intake_date",""),
            "보험사": c.get("insurance_co",""),
            "차량구분": c.get("vehicle_type",""),
            "청구금액": c.get("claim_amount") or 0,
            "자기부담금": c.get("deductible") or 0,
            "과실비율": c.get("fault_ratio") or 0,
            "AOS청구일": c.get("aos_claimed_at") or "",
            "입금액": c.get("paid_amount") or 0,
            "입금일": c.get("paid_at") or "",
            "미수금": (c.get("claim_amount") or 0) - (c.get("paid_amount") or 0),
            "_id": c.get("id",""),
        })

    if not rows:
        st.info("조건에 맞는 보험 청구 내역이 없습니다.")
        return
    df = pd.DataFrame(rows)
    display_df = df.drop(columns=["_id"], errors="ignore")
    money_cols = ["청구금액","자기부담금","입금액","미수금"]

    event = st.dataframe(
        display_df.style.format({c: "{:,.0f}" for c in money_cols}),
        use_container_width=True,
        height=380,
        on_select="rerun",
        selection_mode="single-row",
    )

    # ── 선택 시 상태 업데이트
    selected = event.selection.get("rows", []) if event else []
    if selected:
        idx = selected[0]
        claim_id = rows[idx]["_id"]
        plate = rows[idx]["차량번호"]

        st.divider()
        st.subheader(f"🔄 청구 정보 수정 — {plate}")

        with st.form("claim_update_form"):
            uc1, uc2 = st.columns(2)
            new_status = uc1.selectbox("상태", CLAIM_STATUS,
                                       index=CLAIM_STATUS.index(rows[idx]["상태"])
                                       if rows[idx]["상태"] in CLAIM_STATUS else 0)
            claim_amount = uc2.number_input("청구금액(원)", min_value=0, step=10000,
                                            value=int(rows[idx]["청구금액"]))

            uc3, uc4 = st.columns(2)
            aos_date = uc3.date_input("AOS 청구일",
                                      value=date.fromisoformat(rows[idx]["AOS청구일"])
                                      if rows[idx]["AOS청구일"] else None)
            paid_at  = uc4.date_input("입금일",
                                      value=date.fromisoformat(rows[idx]["입금일"])
                                      if rows[idx]["입금일"] else None)

            paid_amount = st.number_input("입금액(원)", min_value=0, step=10000,
                                          value=int(rows[idx]["입금액"]))
            memo = st.text_input("메모")

            u_sub = st.form_submit_button("✅ 저장", type="primary")

        if u_sub:
            update_data = {
                "status": new_status,
                "claim_amount": claim_amount,
                "paid_amount": paid_amount if paid_amount > 0 else None,
                "aos_claimed_at": str(aos_date) if aos_date else None,
                "paid_at": str(paid_at) if paid_at else None,
                "memo": memo.strip() or None,
            }
            # 차량 AOS 플래그 업데이트
            if aos_date:
                vehicle_id = next(
                    (c["vehicle_id"] for c in claims if c["id"] == claim_id), None
                )
                if vehicle_id:
                    sb.table("vehicles").update({"aos_claimed": True}).eq("id", vehicle_id).execute()

            sb.table("insurance_claims").update(update_data).eq("id", claim_id).execute()
            st.success("✅ 업데이트 완료")
            st.rerun()

    # ── 보험사별 미수금 요약
    st.divider()
    st.subheader("보험사별 정산 현황")
    co_agg = {}
    for c in claims:
        co = c.get("insurance_co","기타")
        if co not in co_agg:
            co_agg[co] = {"청구": 0, "입금": 0, "건수": 0}
        co_agg[co]["청구"] += c.get("claim_amount") or 0
        co_agg[co]["입금"] += c.get("paid_amount") or 0
        co_agg[co]["건수"] += 1

    if co_agg:
        df_co = pd.DataFrame([{
            "보험사": co,
            "건수": v["건수"],
            "총청구": v["청구"],
            "총입금": v["입금"],
            "미수금": v["청구"] - v["입금"],
        } for co, v in co_agg.items()])
        st.dataframe(
            df_co.style.format({"총청구": "{:,.0f}", "총입금": "{:,.0f}", "미수금": "{:,.0f}"}),
            use_container_width=True,
        )
