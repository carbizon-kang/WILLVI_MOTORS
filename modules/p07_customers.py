"""고객 관리"""
import streamlit as st
import pandas as pd
from database.connection import get_supabase
from utils.styles import apply_global_style, page_header, section_title
from utils.calculations import fmt_money


def format_phone_number():
    """핸드폰 번호 포맷팅 함수"""
    phone = st.session_state.get("phone_input", "")
    digits = ''.join(c for c in phone if c.isdigit())
    if len(digits) <= 3:
        formatted = digits
    elif len(digits) <= 7:
        formatted = f"{digits[:3]}-{digits[3:]}"
    else:
        formatted = f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    st.session_state.phone_input = formatted


def render():
    apply_global_style()
    page_header("고객 관리", "고객 정보 및 수리 이력 조회")
    sb = get_supabase()

    tab1, tab2 = st.tabs(["고객 목록", "고객 등록/수정"])

    with tab1:
        search = st.text_input("검색 (이름/연락처)")
        customers = sb.table("customers").select("*").order("name").execute().data or []
        if search.strip():
            kw = search.lower()
            customers = [c for c in customers
                         if kw in (c.get("name") or "").lower()
                         or kw in (c.get("phone") or "").lower()]

        st.caption(f"총 {len(customers)}명")
        if not customers:
            st.info("고객이 없습니다.")
            return

        rows = [{"이름": c["name"], "연락처": c.get("phone",""),
                 "메모": c.get("memo","") or "", "등록일": c.get("created_at","")[:10],
                 "_id": c["id"]} for c in customers]
        df = pd.DataFrame(rows)

        event = st.dataframe(
            df.drop(columns=["_id"], errors="ignore"),
            use_container_width=True,
            height=380,
            on_select="rerun",
            selection_mode="single-row",
        )

        selected = event.selection.get("rows", []) if event else []
        if selected:
            idx = selected[0]
            cust_id = rows[idx]["_id"]
            st.divider()
            st.subheader(f"수리 이력 — {rows[idx]['이름']}")
            # 해당 고객 차량 목록
            v_list = sb.table("vehicles") \
                .select("plate_number, model, intake_type, intake_date, actual_out, status, "
                        "work_orders(total_amount)") \
                .eq("customer_id", cust_id) \
                .order("intake_date", desc=True) \
                .execute().data or []

            if v_list:
                hist = []
                for v in v_list:
                    orders = v.get("work_orders") or []
                    total = sum((o.get("total_amount") or 0) for o in orders)
                    hist.append({
                        "차량번호": v.get("plate_number",""),
                        "모델": v.get("model",""),
                        "입고분류": v.get("intake_type",""),
                        "입고일": v.get("intake_date",""),
                        "출고일": v.get("actual_out","") or "입고중",
                        "상태": v.get("status",""),
                        "총수리비": fmt_money(total),
                    })
                st.dataframe(pd.DataFrame(hist), use_container_width=True)
            else:
                st.info("수리 이력 없음")

    with tab2:
        # 신규 등록
        st.subheader("신규 고객 등록")
        with st.form("customer_form", clear_on_submit=True):
            cc1, cc2 = st.columns(2)
            name  = cc1.text_input("고객명 *")
            phone = cc2.text_input("연락처", value=st.session_state.get("phone_input", ""), key="phone_input", on_change=format_phone_number, placeholder="010-0000-0000")
            memo  = st.text_input("메모")
            sub   = st.form_submit_button("✅ 등록", type="primary")

        if sub:
            if not name.strip():
                st.error("고객명을 입력하세요.")
            else:
                sb.table("customers").insert({
                    "name": name.strip(),
                    "phone": st.session_state.get("phone_input", "").strip() or None,
                    "memo": memo.strip() or None,
                }).execute()
                st.success(f"✅ [{name}] 고객이 등록되었습니다.")
                # 폼 제출 후 session_state 초기화
                if "phone_input" in st.session_state:
                    del st.session_state.phone_input
                st.rerun()
