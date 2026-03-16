"""차량 입고 등록"""
import streamlit as st
import pandas as pd
from datetime import date
from database.connection import get_supabase
from utils.styles import apply_global_style, page_header, section_title
from utils.calculations import fmt_phone
from utils.intake_types import get_type_names, get_intake_types, is_insurance_type, add_intake_type, deactivate_intake_type, activate_intake_type, get_inactive_types

INSURANCE_COS = ['삼성화재', 'KB손보', '현대해상', 'DB손보', '기타']


def render():
    apply_global_style()
    page_header("차량 입고 등록", "차량 입고 현황 및 신규 차량 등록")
    sb = get_supabase()

    # ── 탭: 입고 등록 / 입고분류 관리
    tab_intake, tab_types = st.tabs(["📋 입고 등록", "⚙️ 입고분류 관리"])

    with tab_intake:
        # 등록 완료 후 입력값 초기화
        if st.session_state.get("_intake_reset"):
            for k in list(st.session_state.keys()):
                if k.startswith("fi_"):
                    del st.session_state[k]
            del st.session_state["_intake_reset"]

        type_names = get_type_names(sb)

        st.subheader("① 입고 기본 정보")
        c1, c2, c3 = st.columns(3)
        intake_date  = c1.date_input("입고일 *", value=date.today(), key="fi_intake_date")
        intake_type  = c2.selectbox("입고분류 *", type_names, key="fi_intake_type")
        expected_out = c3.date_input("출고예정일", value=None, key="fi_expected_out")

        c4, c5, c6 = st.columns(3)
        plate_number = c4.text_input("차량번호 *", placeholder="12가3456", key="fi_plate")
        model        = c5.text_input("차량모델", placeholder="BMW 520d", key="fi_model")
        color        = c6.text_input("차량색상", placeholder="흰색", key="fi_color")

        c7, c8 = st.columns(2)
        vin     = c7.text_input("차대번호(VIN)", placeholder="선택입력", key="fi_vin")
        mileage = c8.number_input("입고 주행거리(km)", min_value=0, value=0, step=1000, key="fi_mileage")

        memo = st.text_area("비고", height=80, key="fi_memo")

        st.subheader("② 고객 정보")
        cust_mode = st.radio("고객", ["신규 고객 등록", "기존 고객 검색"], horizontal=True, key="fi_cust_mode")

        customer_id = None
        if cust_mode == "신규 고객 등록":
            cc1, cc2 = st.columns(2)
            cust_name  = cc1.text_input("고객명 *", key="fi_cust_name")
            cust_phone = cc2.text_input("연락처", placeholder="010-0000-0000", key="fi_cust_phone")
            cust_memo  = st.text_input("고객 메모", key="fi_cust_memo")
        else:
            customers = sb.table("customers").select("id,name,phone").order("name").execute().data or []
            opts = {f"{c['name']} ({c.get('phone','')})": c['id'] for c in customers}
            sel  = st.selectbox("고객 선택", ["-- 선택 --"] + list(opts.keys()), key="fi_cust_sel")
            if sel != "-- 선택 --":
                customer_id = opts[sel]
            cust_name = cust_phone = cust_memo = ""

        # 보험 정보 — is_insurance_type()으로 동적 판단
        is_insurance = is_insurance_type(sb, intake_type)
        if is_insurance:
            st.subheader("③ 보험 청구 정보")
            bi1, bi2, bi3, bi4 = st.columns(4)
            ins_co_default = {
                '일반-삼성보험': '삼성화재', '일반-KB보험': 'KB손보',
                '일반-현대보험': '현대해상', '일반-DB보험': 'DB손보'
            }.get(intake_type, '삼성화재')
            insurance_co  = bi1.selectbox("보험사", INSURANCE_COS,
                                          index=INSURANCE_COS.index(ins_co_default)
                                          if ins_co_default in INSURANCE_COS else 0,
                                          key="fi_ins_co")
            vehicle_type  = bi2.selectbox("차량구분", ["국산", "외산"], key="fi_veh_type")
            deductible    = bi3.number_input("자기부담금(원)", min_value=0, step=10000, key="fi_deductible")
            fault_ratio   = bi4.number_input("과실비율(%)", min_value=0.0, max_value=100.0, step=5.0, key="fi_fault")
            vat_applicable = st.checkbox("부가세 적용", value=True, key="fi_vat")
        else:
            insurance_co = vehicle_type = None
            deductible = fault_ratio = 0
            vat_applicable = False

        submitted = st.button("✅ 입고 등록", type="primary", use_container_width=True)

        if submitted:
            if not plate_number.strip():
                st.error("차량번호를 입력하세요.")
            else:
                if cust_mode == "신규 고객 등록" and cust_name.strip():
                    res = sb.table("customers").insert({
                        "name": cust_name.strip(),
                        "phone": fmt_phone(cust_phone.strip()),
                        "memo": cust_memo.strip() or None,
                    }).execute()
                    customer_id = res.data[0]["id"] if res.data else None

                vehicle_data = {
                    "plate_number": plate_number.strip().upper(),
                    "model": model.strip() or None,
                    "color": color.strip() or None,
                    "vin": vin.strip() or None,
                    "mileage": mileage if mileage > 0 else None,
                    "customer_id": customer_id,
                    "intake_date": str(intake_date),
                    "expected_out": str(expected_out) if expected_out else None,
                    "intake_type": intake_type,
                    "status": "입고",
                    "memo": memo.strip() or None,
                }
                v_res = sb.table("vehicles").insert(vehicle_data).execute()
                vehicle_id = v_res.data[0]["id"] if v_res.data else None

                if is_insurance and vehicle_id and insurance_co:
                    sb.table("insurance_claims").insert({
                        "vehicle_id": vehicle_id,
                        "insurance_co": insurance_co,
                        "vehicle_type": vehicle_type,
                        "deductible": int(deductible),
                        "fault_ratio": float(fault_ratio),
                        "vat_applicable": vat_applicable,
                        "status": "청구전",
                    }).execute()

                st.success(f"✅ [{plate_number}] 차량이 입고 등록되었습니다!")
                st.balloons()
                st.session_state["_intake_reset"] = True
                st.rerun()

        # ── 오늘 입고 목록
        st.divider()
        st.subheader("오늘 입고 차량")
        today_str = date.today().isoformat()
        today_vehicles = sb.table("vehicles") \
            .select("plate_number, model, intake_type, status, customers(name, phone)") \
            .eq("intake_date", today_str) \
            .execute().data or []

        if today_vehicles:
            rows = []
            for v in today_vehicles:
                cust = v.get("customers") or {}
                rows.append({
                    "차량번호": v.get("plate_number", ""),
                    "모델": v.get("model", ""),
                    "입고분류": v.get("intake_type", ""),
                    "상태": v.get("status", ""),
                    "고객명": cust.get("name", ""),
                    "연락처": fmt_phone(cust.get("phone", "")),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("오늘 입고된 차량이 없습니다.")

    # ── 입고분류 관리 탭
    with tab_types:
        st.subheader("⚙️ 입고분류 항목 관리")
        st.caption("차량 입고 시 선택할 분류 항목을 추가하거나 비활성화할 수 있습니다.")

        # 현재 목록
        all_types = get_intake_types(sb)
        if all_types:
            df_types = pd.DataFrame([{
                "입고분류명": t["name"],
                "보험청구": "✔ 보험" if t.get("is_insurance") else "일반",
            } for t in all_types])
            st.dataframe(df_types, use_container_width=True, hide_index=True)

        st.divider()

        # 새 항목 추가
        st.subheader("새 항목 추가")
        with st.form("add_type_form", clear_on_submit=True):
            nc1, nc2 = st.columns([3, 1])
            new_name     = nc1.text_input("입고분류명 *", placeholder="예) 일반-메리츠보험, 법인매입, 경매매입")
            new_ins      = nc2.selectbox("유형", ["일반", "보험청구"])
            add_btn      = st.form_submit_button("➕ 추가", type="primary")

        if add_btn:
            if not new_name.strip():
                st.error("입고분류명을 입력하세요.")
            else:
                ok = add_intake_type(sb, new_name.strip(), new_ins == "보험청구")
                if ok:
                    st.success(f"✅ '{new_name}' 항목이 추가되었습니다.")
                    st.rerun()
                else:
                    st.warning(f"'{new_name}' 항목이 이미 존재합니다.")

        # 항목 비활성화
        st.divider()
        st.subheader("항목 비활성화")
        st.caption("비활성화된 항목은 입고 등록 시 선택 목록에서 제외됩니다.")
        del_names = [t["name"] for t in all_types]
        if del_names:
            del_sel = st.selectbox("비활성화할 항목", del_names, key="del_type_sel")
            if st.button("🚫 비활성화", type="secondary"):
                deactivate_intake_type(sb, del_sel)
                st.success(f"'{del_sel}' 항목이 비활성화되었습니다.")
                st.rerun()

        # 항목 재활성화
        st.divider()
        st.subheader("항목 재활성화")
        st.caption("비활성화된 항목을 다시 선택 목록에 추가합니다.")
        inactive_names = get_inactive_types(sb)
        if inactive_names:
            act_sel = st.selectbox("재활성화할 항목", inactive_names, key="act_type_sel")
            if st.button("✅ 재활성화", type="primary"):
                activate_intake_type(sb, act_sel)
                st.success(f"'{act_sel}' 항목이 재활성화되었습니다.")
                st.rerun()
        else:
            st.info("비활성화된 항목이 없습니다.")
