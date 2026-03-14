"""작업지시서 - 수리 내역 및 비용 입력"""
import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_supabase
from utils.styles import apply_global_style, page_header, section_title
from utils.calculations import summarize_work_order, fmt_money, ENGINE_OIL_UNIT_PRICE

REPAIR_SEQS = ['수리1', '수리2', '추가']

STATUS_COLOR = {
    '입고': '#4A90D9', '진단': '#F5A623', '수리중': '#7ED321',
    '부품대기': '#D0021B', '도장': '#9B59B6', '상품화': '#1ABC9C',
    '출고대기': '#E67E22', '출고완료': '#95A5A6'
}


def render():
    apply_global_style()
    page_header("작업지시서", "수리 작업 내역 및 비용 관리")
    sb = get_supabase()

    # ── 차량 선택
    search_plate = st.text_input("차량번호 검색", placeholder="12가3456")
    all_vehicles = sb.table("vehicles") \
        .select("id, plate_number, model, status, intake_type, intake_date") \
        .order("intake_date", desc=True) \
        .execute().data or []

    filtered_v = [v for v in all_vehicles
                  if not search_plate or search_plate.lower() in (v.get("plate_number","")).lower()]
    if not filtered_v:
        st.warning("검색 결과 없음")
        return

    all_opts = {f"{v['plate_number']} | {v.get('model','')} | {v.get('status','')}": v['id']
                for v in filtered_v}
    default_vid = st.session_state.get("detail_vehicle_id", None)
    default_key = next((k for k, v in all_opts.items() if v == default_vid), None)
    sel_label   = st.selectbox("차량 선택", list(all_opts.keys()),
                               index=list(all_opts.keys()).index(default_key) if default_key else 0)
    vehicle_id  = all_opts[sel_label]

    vehicle  = next((v for v in filtered_v if v["id"] == vehicle_id), {})
    v_status = vehicle.get("status", "")
    color    = STATUS_COLOR.get(v_status, "#888")
    st.markdown(
        f"<span style='background:{color};color:white;padding:4px 14px;"
        f"border-radius:12px;font-weight:bold'>● {v_status}</span>",
        unsafe_allow_html=True
    )

    # ── 기존 작업지시서 목록
    st.divider()
    orders = sb.table("work_orders").select("*") \
        .eq("vehicle_id", vehicle_id).order("created_at").execute().data or []
    all_done = bool(orders) and all(o.get("status") == "완료" for o in orders)

    if orders:
        st.subheader("작업지시서 현황")
        rows = []
        for o in orders:
            s = summarize_work_order(o)
            rows.append({
                "구분": s.get("repair_seq",""),
                "수리내용": (s.get("description") or "")[:40],
                "담당자": s.get("worker","") or "-",
                "부품금액": fmt_money(s.get("parts_amount",0)),
                "기술료": fmt_money(s.get("tech_fee",0)),
                "총계": fmt_money(s.get("total_amount",0)),
                "완료일": s.get("completed_at","") or "-",
                "상태": "완료" if s.get("status") == "완료" else "진행중",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        grand_total = sum(summarize_work_order(o).get("total_amount",0) or 0 for o in orders)
        st.metric("전체 작업 합계", fmt_money(grand_total))

        # ── 진행중 작업 빠른 완료 처리
        pending_orders = [o for o in orders if o.get("status") != "완료"]
        if pending_orders:
            st.divider()
            st.subheader(f"⏳ 진행중 작업 완료 처리 ({len(pending_orders)}건)")
            for o in pending_orders:
                desc = (o.get("description") or "")[:30] or "내용 없음"
                c_label, c_date, c_btn = st.columns([3, 2, 1])
                c_label.markdown(f"**[{o.get('repair_seq','')}]** {desc}")
                done_date = c_date.date_input(
                    "완료일", value=date.today(),
                    key=f"done_date_{o['id']}",
                    label_visibility="collapsed"
                )
                if c_btn.button("완료", key=f"done_btn_{o['id']}", type="primary"):
                    sb.table("work_orders").update({
                        "status": "완료",
                        "completed_at": str(done_date),
                    }).eq("id", o["id"]).execute()
                    st.rerun()

        # ── 출고 흐름 버튼
        st.divider()
        pending_cnt = sum(1 for o in orders if o.get("status") != "완료")

        if v_status not in ("출고대기", "출고완료"):
            if all_done:
                st.success("모든 작업이 완료되었습니다.")
                c1, _ = st.columns([2, 4])
                if c1.button("🚗 출고대기로 이동", type="primary", use_container_width=True):
                    sb.table("vehicles").update({"status": "출고대기"}).eq("id", vehicle_id).execute()
                    st.success(f"[{vehicle.get('plate_number','')}] 출고대기로 변경되었습니다.")
                    st.rerun()

        if v_status == "출고대기":
            st.info("출고 대기 중입니다.")
            c_out, _ = st.columns([2, 4])
            if c_out.button("📤 출고완료 처리", type="primary", use_container_width=True):
                sb.table("vehicles").update({
                    "status": "출고완료",
                    "actual_out": str(date.today()),
                }).eq("id", vehicle_id).execute()
                st.success(f"출고완료 처리되었습니다. (출고일: {date.today()})")
                st.rerun()

    # ── 작업지시서 등록 / 수정
    st.divider()
    st.subheader("작업지시서 등록 / 수정")

    edit_id = None
    if orders:
        edit_opts = {"⊕ 새 작업지시서 추가": None}
        for o in orders:
            label = (f"[{o['repair_seq']}] {(o.get('description') or '')[:30]} "
                     f"({'완료' if o.get('status')=='완료' else '진행중'})")
            edit_opts[label] = o['id']
        sel_edit = st.selectbox("편집할 지시서", list(edit_opts.keys()))
        edit_id  = edit_opts[sel_edit]

    edit_order = next((o for o in orders if o['id'] == edit_id), {}) if edit_id else {}

    with st.form("work_order_form"):
        fc1, fc2, fc3 = st.columns(3)
        repair_seq = fc1.selectbox("수리 구분", REPAIR_SEQS,
                                   index=REPAIR_SEQS.index(edit_order.get("repair_seq","수리1"))
                                   if edit_order.get("repair_seq") in REPAIR_SEQS else 0)
        worker    = fc2.text_input("담당 기술자", value=edit_order.get("worker",""))
        wo_status = fc3.selectbox("작업 상태", ["진행중","완료"],
                                  index=0 if edit_order.get("status","진행중") == "진행중" else 1)

        description = st.text_area("수리 내용", value=edit_order.get("description",""), height=80)

        st.markdown("**비용 항목**")
        col1, col2, col3 = st.columns(3)
        parts_amount = col1.number_input("부품금액 (엔진오일 제외, 원)", min_value=0, step=1000,
                                         value=int(edit_order.get("parts_amount",0) or 0))
        tech_fee     = col2.number_input("기술료 (공임, 원)", min_value=0, step=10000,
                                         value=int(edit_order.get("tech_fee",0) or 0))
        paint_amount = col3.number_input("도장금액 (원)", min_value=0, step=10000,
                                         value=int(edit_order.get("paint_amount",0) or 0))

        col4, col5, col6 = st.columns(3)
        engine_oil_liter = col4.number_input("엔진오일 (리터)", min_value=0.0, step=0.5,
                                              value=float(edit_order.get("engine_oil_liter",0) or 0))
        engine_oil_unit  = col5.number_input("엔진오일 단가 (원/리터)", min_value=0, step=100,
                                              value=int(edit_order.get("engine_oil_unit", ENGINE_OIL_UNIT_PRICE) or ENGINE_OIL_UNIT_PRICE))
        towing_fee       = col6.number_input("견인비 (원)", min_value=0, step=10000,
                                              value=int(edit_order.get("towing_fee",0) or 0))
        insurance_fee    = st.number_input("보험료 (원)", min_value=0, step=10000,
                                           value=int(edit_order.get("insurance_fee",0) or 0))

        from utils.calculations import calc_engine_oil, calc_total, calc_vat
        oil_amt   = calc_engine_oil(engine_oil_liter, engine_oil_unit)
        vat_amt   = calc_vat(tech_fee)
        total_amt = calc_total(parts_amount, oil_amt, towing_fee, insurance_fee, tech_fee)
        preview   = (f"계산 미리보기 | 엔진오일: {fmt_money(oil_amt)} | "
                     f"부가세: {fmt_money(vat_amt)} | 총계: {fmt_money(total_amt)}")
        if paint_amount > 0:
            preview += f" | 도장금액: {fmt_money(paint_amount)}"
        st.info(preview)

        completed_at = None
        if wo_status == "완료":
            completed_at = st.date_input("완료일", value=date.today())

        submitted = st.form_submit_button(
            "저장" if edit_id else "등록", type="primary", use_container_width=True)

    if submitted:
        if v_status in ("입고", "진단"):
            sb.table("vehicles").update({"status": "수리중"}).eq("id", vehicle_id).execute()
        data = {
            "vehicle_id": vehicle_id, "repair_seq": repair_seq,
            "description": description.strip() or None,
            "worker": worker.strip() or None,
            "parts_amount": parts_amount, "engine_oil_liter": engine_oil_liter,
            "engine_oil_unit": engine_oil_unit, "towing_fee": towing_fee,
            "insurance_fee": insurance_fee, "tech_fee": tech_fee,
            "paint_amount": paint_amount, "status": wo_status,
            "completed_at": str(completed_at) if completed_at else None,
        }
        if edit_id:
            sb.table("work_orders").update(data).eq("id", edit_id).execute()
            st.success("작업지시서가 수정되었습니다.")
        else:
            sb.table("work_orders").insert(data).execute()
            st.success("작업지시서가 등록되었습니다.")
        st.rerun()

    # ── 세부 내역
    if orders and edit_id:
        st.divider()
        st.subheader("세부 작업 내역")
        details = sb.table("order_details").select("*") \
            .eq("work_order_id", edit_id).execute().data or []
        if details:
            st.dataframe(pd.DataFrame([{
                "유형": d.get("item_type",""), "항목명": d.get("item_name",""),
                "수량": d.get("quantity",1), "단가": fmt_money(d.get("unit_price",0)),
                "금액": fmt_money(d.get("amount",0)), "메모": d.get("memo","") or "",
            } for d in details]), use_container_width=True, hide_index=True)

        with st.form("detail_form", clear_on_submit=True):
            dc1, dc2, dc3, dc4 = st.columns([2,3,1,2])
            d_type  = dc1.selectbox("유형", ["부품","소모품","공임","기타"])
            d_name  = dc2.text_input("항목명")
            d_qty   = dc3.number_input("수량", min_value=0.1, step=0.1, value=1.0)
            d_price = dc4.number_input("단가(원)", min_value=0, step=1000)
            d_memo  = st.text_input("메모")
            d_sub   = st.form_submit_button("세부 내역 추가", use_container_width=True)

        if d_sub and d_name.strip():
            sb.table("order_details").insert({
                "work_order_id": edit_id, "item_type": d_type,
                "item_name": d_name.strip(), "quantity": d_qty,
                "unit_price": d_price, "memo": d_memo.strip() or None,
            }).execute()
            st.rerun()
