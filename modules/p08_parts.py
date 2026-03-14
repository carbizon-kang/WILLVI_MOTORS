"""부품 재고 관리"""
import streamlit as st
import pandas as pd
from database.connection import get_supabase
from utils.styles import apply_global_style, page_header, section_title
from utils.calculations import fmt_money

CATEGORIES = ['엔진', '외장', '내장', '전기', '소모품', '타이어', '기타']


def render():
    apply_global_style()
    page_header("부품 재고", "부품 재고 현황 및 입출고 관리")
    sb = get_supabase()

    tab1, tab2 = st.tabs(["재고 현황", "부품 등록/수정"])

    with tab1:
        # 재고 부족 알림
        parts = sb.table("parts").select("*").order("name").execute().data or []
        low_stock = [p for p in parts if p.get("stock_qty", 0) <= p.get("min_stock", 0) and p.get("min_stock", 0) > 0]
        if low_stock:
            st.warning(f"⚠️ 재고 부족 부품: {', '.join(p['name'] for p in low_stock)}")

        # 필터
        fc1, fc2 = st.columns(2)
        f_cat    = fc1.selectbox("카테고리", ["전체"] + CATEGORIES)
        f_search = fc2.text_input("부품명/번호 검색")

        filtered = parts
        if f_cat != "전체":
            filtered = [p for p in filtered if p.get("category") == f_cat]
        if f_search.strip():
            kw = f_search.lower()
            filtered = [p for p in filtered
                        if kw in (p.get("name") or "").lower()
                        or kw in (p.get("part_number") or "").lower()]

        st.caption(f"총 {len(filtered)}종 | 재고 부족 {len(low_stock)}종")

        rows = [{
            "부품명": p.get("name",""),
            "부품번호": p.get("part_number","") or "-",
            "카테고리": p.get("category","") or "-",
            "단가": p.get("unit_price",0) or 0,
            "재고": p.get("stock_qty",0) or 0,
            "최소재고": p.get("min_stock",0) or 0,
            "공급업체": p.get("supplier","") or "-",
            "_id": p.get("id",""),
        } for p in filtered]

        df = pd.DataFrame(rows)
        if not df.empty:
            # 재고 부족 행 하이라이트
            def highlight_low(row):
                if row["재고"] <= row["최소재고"] and row["최소재고"] > 0:
                    return ["background-color: #FFEBEE"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df.drop(columns=["_id"], errors="ignore").style
                  .apply(highlight_low, axis=1)
                  .format({"단가": "{:,.0f}"}),
                use_container_width=True,
                height=420,
            )

            # 재고 조정
            event = st.dataframe(
                df.drop(columns=["_id"], errors="ignore"),
                use_container_width=False,
                height=1,  # hidden
                on_select="rerun",
                selection_mode="single-row",
                key="parts_select",
            )
        else:
            st.info("부품이 없습니다.")
            return

    with tab2:
        st.subheader("부품 등록")
        with st.form("part_form", clear_on_submit=True):
            pc1, pc2, pc3 = st.columns(3)
            p_name   = pc1.text_input("부품명 *")
            p_number = pc2.text_input("부품번호")
            p_cat    = pc3.selectbox("카테고리", CATEGORIES)

            pc4, pc5, pc6 = st.columns(3)
            p_price    = pc4.number_input("단가(원)", min_value=0, step=100)
            p_stock    = pc5.number_input("초기 재고", min_value=0, step=1)
            p_min      = pc6.number_input("최소 재고(알림 기준)", min_value=0, step=1)

            p_supplier = st.text_input("공급업체")
            p_memo     = st.text_input("메모")
            p_sub      = st.form_submit_button("✅ 등록", type="primary")

        if p_sub:
            if not p_name.strip():
                st.error("부품명을 입력하세요.")
            else:
                sb.table("parts").insert({
                    "name": p_name.strip(),
                    "part_number": p_number.strip() or None,
                    "category": p_cat,
                    "unit_price": p_price,
                    "stock_qty": int(p_stock),
                    "min_stock": int(p_min),
                    "supplier": p_supplier.strip() or None,
                    "memo": p_memo.strip() or None,
                }).execute()
                st.success(f"✅ [{p_name}] 부품이 등록되었습니다.")
                st.rerun()

        # 재고 조정
        st.divider()
        st.subheader("재고 수량 조정")
        all_parts = sb.table("parts").select("id, name, stock_qty").order("name").execute().data or []
        if all_parts:
            p_opts = {f"{p['name']} (현재: {p.get('stock_qty',0)}개)": p for p in all_parts}
            sel_p = st.selectbox("부품 선택", list(p_opts.keys()))
            sel_part = p_opts[sel_p]
            adj = st.number_input("조정 수량 (+ 입고 / - 출고)", step=1, value=0)
            if st.button("재고 조정 적용"):
                new_qty = (sel_part.get("stock_qty") or 0) + adj
                sb.table("parts").update({"stock_qty": max(0, new_qty)}).eq("id", sel_part["id"]).execute()
                st.success(f"재고 조정: {sel_part['name']} → {max(0, new_qty)}개")
                st.rerun()
