"""차량 현황 목록"""
import streamlit as st
import pandas as pd
from database.connection import get_supabase
from utils.styles import apply_global_style, page_header, section_title
from utils.calculations import fmt_phone
from utils.excel_export import export_work_list_excel

STATUS_LIST   = ['전체', '입고', '진단', '수리중', '부품대기', '도장', '상품화', '출고대기', '출고완료']
INTAKE_TYPES  = ['전체', '용답매입', '용답데모', '일반-삼성보험', '일반-KB보험',
                 '일반-현대보험', '일반-DB보험', '일반(자비)']
STATUS_COLOR  = {
    '입고': '#4A90D9', '진단': '#F5A623', '수리중': '#7ED321',
    '부품대기': '#D0021B', '도장': '#9B59B6', '상품화': '#1ABC9C',
    '출고대기': '#E67E22', '출고완료': '#95A5A6'
}


def render():
    apply_global_style()
    page_header("차량 현황", "전체 입고 차량 현황 조회 및 상태 관리")
    sb = get_supabase()

    # ── 필터
    fc1, fc2, fc3, fc4 = st.columns(4)
    f_status = fc1.selectbox("작업 상태", STATUS_LIST)
    f_type   = fc2.selectbox("입고 분류", INTAKE_TYPES)
    f_search = fc3.text_input("차량번호/모델 검색")
    # 출고완료 선택 시 체크박스 강제 해제
    active_default = f_status not in ("전체", "출고완료")
    f_active = fc4.checkbox("입고중만 표시", value=active_default)

    # ── 데이터 로드
    query = sb.table("vehicles").select(
        "id, plate_number, model, color, intake_date, expected_out, actual_out, "
        "intake_type, status, aos_claimed, insurance_paid, memo, "
        "customers(name, phone)"
    ).order("intake_date", desc=True)

    if f_active and f_status != "출고완료":
        query = query.neq("status", "출고완료")
    if f_status != "전체":
        query = query.eq("status", f_status)
    if f_type != "전체":
        query = query.eq("intake_type", f_type)

    vehicles = query.execute().data or []

    # 검색 필터 (클라이언트)
    if f_search.strip():
        kw = f_search.strip().lower()
        vehicles = [v for v in vehicles
                    if kw in (v.get("plate_number") or "").lower()
                    or kw in (v.get("model") or "").lower()]

    st.caption(f"총 {len(vehicles)}대")

    if not vehicles:
        st.info("조건에 맞는 차량이 없습니다.")
        return

    # ── 엑셀 다운로드
    flat = []
    for v in vehicles:
        cust = v.get("customers") or {}
        flat.append({**v, "customer_name": cust.get("name",""), "customer_phone": cust.get("phone","")})

    col_dl, _ = st.columns([1, 4])
    with col_dl:
        excel_bytes = export_work_list_excel(flat)
        st.download_button(
            "📥 엑셀 다운로드", data=excel_bytes,
            file_name="작업진행내역.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ── 목록 테이블
    rows = []
    for v in flat:
        status = v.get("status", "")
        color = STATUS_COLOR.get(status, "#888")
        rows.append({
            "상태": status,
            "차량번호": v.get("plate_number", ""),
            "모델": v.get("model", ""),
            "입고분류": v.get("intake_type", ""),
            "입고일": v.get("intake_date", ""),
            "출고예정": v.get("expected_out", "") or "-",
            "고객명": v.get("customer_name", ""),
            "연락처": fmt_phone(v.get("customer_phone", "")),
            "AOS": "✔" if v.get("aos_claimed") else "",
            "비고": v.get("memo", "") or "",
            "_id": v.get("id", ""),
        })

    df = pd.DataFrame(rows)
    display_df = df.drop(columns=["_id"], errors="ignore")

    event = st.dataframe(
        display_df,
        use_container_width=True,
        height=480,
        on_select="rerun",
        selection_mode="single-row",
    )

    # ── 상태 변경 (선택 시)
    selected = event.selection.get("rows", []) if event else []
    if selected:
        idx = selected[0]
        vehicle_id = rows[idx]["_id"]
        plate = rows[idx]["차량번호"]

        st.divider()
        st.subheader(f"🔄 상태 변경 — {plate}")
        status_opts = ['입고', '진단', '수리중', '부품대기', '도장', '상품화', '출고대기', '출고완료']
        cur_status = rows[idx]["상태"]
        new_status = st.selectbox("새 상태", status_opts,
                                  index=status_opts.index(cur_status) if cur_status in status_opts else 0)

        exp_date = st.date_input("출고예정일 수정", value=None)
        actual_out = None
        if new_status == "출고완료":
            from datetime import date
            actual_out = st.date_input("실제 출고일", value=date.today())

        if st.button("상태 업데이트", type="primary"):
            update_data = {"status": new_status}
            if exp_date:
                update_data["expected_out"] = str(exp_date)
            if actual_out:
                update_data["actual_out"] = str(actual_out)
            sb.table("vehicles").update(update_data).eq("id", vehicle_id).execute()
            st.success(f"✅ {plate} → {new_status}")
            st.rerun()

        # 상세 이동 버튼
        if st.button("📄 작업지시서 보기"):
            st.session_state["detail_vehicle_id"] = vehicle_id
            st.session_state["_goto_page"] = "작업지시서"
            st.rerun()
