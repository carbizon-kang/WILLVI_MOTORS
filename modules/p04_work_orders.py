"""작업지시서 - 수리 내역 및 비용 입력"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
from database.connection import get_supabase
from utils.styles import apply_global_style, page_header, section_title
from utils.calculations import summarize_work_order, fmt_money, ENGINE_OIL_UNIT_PRICE
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from io import BytesIO
import os

# 한글 폰트 등록
_FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "utils", "fonts", "NanumGothic.ttf")
_FONT_PATH = os.path.normpath(_FONT_PATH)
pdfmetrics.registerFont(TTFont("NanumGothic", _FONT_PATH))

REPAIR_SEQS_DEFAULT = ['수리1', '수리2', '추가']

STATUS_COLOR = {
    '입고': '#4A90D9', '진단': '#F5A623', '수리중': '#7ED321',
    '부품대기': '#D0021B', '도장': '#9B59B6', '상품화': '#1ABC9C',
    '출고대기': '#E67E22', '출고완료': '#95A5A6'
}


def format_money_input(key):
    """금액 입력 필드 포맷팅 함수 (천 단위 콤마 추가)"""
    value = st.session_state.get(key, "")
    digits = ''.join(c for c in value if c.isdigit())
    if not digits:
        formatted = ""
    else:
        formatted = f"{int(digits):,}"
    st.session_state[key] = formatted


def _pdf_styles():
    """공통 PDF 스타일 반환"""
    return {
        "title": ParagraphStyle("KTitle", fontName="NanumGothic", fontSize=22,
                                 spaceAfter=6, alignment=1),
        "sub":   ParagraphStyle("KSub",   fontName="NanumGothic", fontSize=11,
                                 spaceAfter=10, alignment=1,
                                 textColor=colors.HexColor("#555555")),
        "h2":    ParagraphStyle("KH2",    fontName="NanumGothic", fontSize=14,
                                 spaceBefore=8, spaceAfter=4,
                                 textColor=colors.HexColor("#2c3e50")),
        "body":  ParagraphStyle("KBody",  fontName="NanumGothic", fontSize=12,
                                 leading=16, spaceAfter=2),
        "seq":   ParagraphStyle("KSeq",   fontName="NanumGothic", fontSize=13,
                                 textColor=colors.white, leading=18),
    }


def _build_vehicle_info_table(vehicle, customer, st):
    """차량/고객 정보 테이블 생성"""
    cust_name   = (customer or {}).get('name', '')  or ''
    cust_phone  = (customer or {}).get('phone', '') or ''
    mileage     = vehicle.get('mileage', '') or ''
    mileage_str = f"{int(mileage):,} km" if mileage else '-'
    info_data = [
        ["차량번호", vehicle.get('plate_number', '') or ''],
        ["차량모델", vehicle.get('model', '')        or ''],
        ["주행거리", mileage_str],
        ["고객명",   cust_name],
        ["연락처",   cust_phone],
    ]
    tbl = Table(
        [[Paragraph(k, st["body"]), Paragraph(v, st["body"])] for k, v in info_data],
        colWidths=[80, 390]
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ("FONTNAME",   (0, 0), (-1,-1), "NanumGothic"),
        ("FONTSIZE",   (0, 0), (-1,-1), 12),
        ("GRID",       (0, 0), (-1,-1), 0.5, colors.grey),
        ("VALIGN",     (0, 0), (-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ]))
    return tbl


def _build_order_section(work_order, details, st):
    """작업지시서 1건에 해당하는 story 요소 목록 반환"""
    items = []

    # ── 수리구분 헤더 바
    seq_label = work_order.get('repair_seq', '') or ''
    seq_tbl = Table(
        [[Paragraph(f"  ■  {seq_label}", st["seq"])]],
        colWidths=[470], rowHeights=[30]
    )
    seq_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#2c3e50")),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",(0,0), (-1,-1), 8),
    ]))
    items.append(seq_tbl)
    items.append(Spacer(1, 6))

    # ── 담당자 + 수리확인 서명란 (좌우 분할)
    worker = work_order.get('worker', '') or '-'
    sign_tbl = Table(
        [[
            Paragraph(f"담당자:  {worker}", st["body"]),
            Paragraph("수리확인:  _______________________________", st["body"]),
        ]],
        colWidths=[220, 250]
    )
    sign_tbl.setStyle(TableStyle([
        ("FONTNAME",     (0,0), (-1,-1), "NanumGothic"),
        ("FONTSIZE",     (0,0), (-1,-1), 12),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 4),
    ]))
    items.append(sign_tbl)

    # ── 수리내용
    desc = work_order.get('description', '') or ''
    if desc:
        desc_tbl = Table(
            [[Paragraph("수리내용", st["body"]), Paragraph(desc, st["body"])]],
            colWidths=[80, 390]
        )
        desc_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (0,-1), colors.HexColor("#ecf0f1")),
            ("FONTNAME",     (0,0), (-1,-1), "NanumGothic"),
            ("FONTSIZE",     (0,0), (-1,-1), 12),
            ("GRID",         (0,0), (-1,-1), 0.5, colors.grey),
            ("VALIGN",       (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",  (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING",   (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ]))
        items.append(desc_tbl)
    items.append(Spacer(1, 8))

    # ── 세부 내역 테이블
    if details:
        items.append(Paragraph("세부 내역", st["h2"]))
        header_row = [
            Paragraph("유형",   st["body"]),
            Paragraph("항목명", st["body"]),
            Paragraph("수량",   st["body"]),
            Paragraph("단가",   st["body"]),
            Paragraph("금액",   st["body"]),
            Paragraph("메모",   st["body"]),
        ]
        d_rows = [header_row]
        for d in details:
            qty    = d.get('quantity', 1) or 1
            price  = d.get('unit_price', 0) or 0
            amount = d.get('amount') or int(qty * price)
            d_rows.append([
                Paragraph(d.get('item_type', '') or '', st["body"]),
                Paragraph(d.get('item_name', '') or '', st["body"]),
                Paragraph(str(qty), st["body"]),
                Paragraph(fmt_money(price),  st["body"]),
                Paragraph(fmt_money(amount), st["body"]),
                Paragraph(d.get('memo', '') or '', st["body"]),
            ])
        d_tbl = Table(d_rows, colWidths=[60, 155, 40, 75, 80, 60])
        d_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,-1), "NanumGothic"),
            ("FONTSIZE",   (0,0), (-1,-1), 11),
            ("GRID",       (0,0), (-1,-1), 0.5, colors.grey),
            ("ALIGN",      (2,1), (4,-1), "RIGHT"),
            ("VALIGN",     (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",  (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING",   (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        items.append(d_tbl)
        items.append(Spacer(1, 8))

    # ── 비용 요약
    items.append(Paragraph("비용 요약", st["h2"]))
    cost_data = [
        ["부품금액", fmt_money(work_order.get('parts_amount', 0))],
        ["기술료",   fmt_money(work_order.get('tech_fee', 0))],
        ["도장금액", fmt_money(work_order.get('paint_amount', 0))],
        ["합  계",   fmt_money(work_order.get('total_amount', 0))],
    ]
    c_tbl = Table(
        [[Paragraph(k, st["body"]), Paragraph(v, st["body"])] for k, v in cost_data],
        colWidths=[100, 160]
    )
    c_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (0,-1),  colors.HexColor("#ecf0f1")),
        ("BACKGROUND",   (0,-1), (-1,-1), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",    (0,-1), (-1,-1), colors.white),
        ("FONTNAME",     (0,0), (-1,-1), "NanumGothic"),
        ("FONTSIZE",     (0,0), (-1,-1), 12),
        ("GRID",         (0,0), (-1,-1), 0.5, colors.grey),
        ("ALIGN",        (1,0), (1,-1), "RIGHT"),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ]))
    items.append(c_tbl)
    return items


def generate_work_order_pdf(orders_with_details, vehicle, customer=None):
    """작업지시서 PDF 생성 — 작업 여러 건을 섹션별로 구분 출력
    orders_with_details: [(work_order_dict, details_list), ...]
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=40, rightMargin=40,
                            topMargin=40, bottomMargin=40)
    st = _pdf_styles()
    story = []

    # ── 제목 + 출력일시
    story.append(Paragraph("작업지시서", st["title"]))
    story.append(Spacer(1, 28))
    printed_at = datetime.now().strftime("%Y년 %m월 %d일  %H:%M  출력")
    story.append(Paragraph(printed_at, st["sub"]))
    story.append(Spacer(1, 12))

    # ── 차량/고객 정보 (1회 출력)
    story.append(_build_vehicle_info_table(vehicle, customer, st))
    story.append(Spacer(1, 16))

    # ── 작업별 섹션
    for i, (work_order, details) in enumerate(orders_with_details):
        if i > 0:
            # 작업 간 구분선
            story.append(Spacer(1, 10))
            sep = Table([['']], colWidths=[470], rowHeights=[2])
            sep.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#aaaaaa"))
            ]))
            story.append(sep)
            story.append(Spacer(1, 10))
        story.extend(_build_order_section(work_order, details, st))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def render():
    apply_global_style()
    page_header("작업지시서", "수리 작업 내역 및 비용 관리")
    sb = get_supabase()

    # ── 차량 선택
    search_plate = st.text_input("차량번호 검색", placeholder="12가3456")
    all_vehicles = sb.table("vehicles") \
        .select("id, plate_number, model, status, intake_type, intake_date, mileage, customer_id") \
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

    # ── 고객 정보 조회 (PDF용)
    customer = {}
    if vehicle.get("customer_id"):
        cust_rows = sb.table("customers").select("name, phone") \
            .eq("id", vehicle["customer_id"]).execute().data or []
        customer = cust_rows[0] if cust_rows else {}

    # ── 기존 작업지시서 목록
    st.divider()
    orders = sb.table("work_orders").select("*") \
        .eq("vehicle_id", vehicle_id).order("created_at").execute().data or []
    all_done = bool(orders) and all(o.get("status") == "완료" for o in orders)

    if orders:
        st.subheader("작업지시서 현황")

        # ── 전체 통합 PDF (모든 작업 한 파일)
        all_details = [
            sb.table("order_details").select("*").eq("work_order_id", o["id"]).execute().data or []
            for o in orders
        ]
        combined_pdf = generate_work_order_pdf(
            list(zip(orders, all_details)), vehicle, customer
        )
        plate_no = vehicle.get("plate_number", "차량")
        st.download_button(
            "📄 전체 작업지시서 PDF (통합)",
            data=combined_pdf,
            file_name=f"작업지시서_{plate_no}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

        # ── 작업별 목록 테이블
        header_cols = st.columns([1, 2, 1, 1, 1, 1, 1, 1, 1])
        headers = ["구분", "수리내용", "담당자", "부품금액", "기술료", "총계", "완료일", "상태", "개별PDF"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        for o, det in zip(orders, all_details):
            s = summarize_work_order(o)
            row_cols = st.columns([1, 2, 1, 1, 1, 1, 1, 1, 1])
            row_cols[0].write(s.get("repair_seq",""))
            row_cols[1].write((s.get("description") or "")[:40])
            row_cols[2].write(s.get("worker","") or "-")
            row_cols[3].write(fmt_money(s.get("parts_amount",0)))
            row_cols[4].write(fmt_money(s.get("tech_fee",0)))
            row_cols[5].write(fmt_money(s.get("total_amount",0)))
            row_cols[6].write(s.get("completed_at","") or "-")
            row_cols[7].write("완료" if s.get("status") == "완료" else "진행중")

            single_pdf = generate_work_order_pdf([(o, det)], vehicle, customer)
            row_cols[8].download_button(
                "PDF", data=single_pdf,
                file_name=f"작업지시서_{plate_no}_{s.get('repair_seq','')}.pdf",
                mime="application/pdf",
                key=f"pdf_{o['id']}",
            )

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

    # ── 수리구분 목록 (기존 지시서에서 사용된 구분 + 기본값 합산)
    used_seqs = [o.get("repair_seq","") for o in orders if o.get("repair_seq")]
    all_seqs  = list(dict.fromkeys(REPAIR_SEQS_DEFAULT + used_seqs))  # 순서 유지 + 중복 제거

    fc1, fc2, fc3 = st.columns(3)
    repair_seq_mode = fc1.radio("수리구분 입력방식", ["선택", "직접입력"],
                                horizontal=True, label_visibility="collapsed",
                                key=f"seq_mode_{edit_id}")
    if repair_seq_mode == "직접입력":
        repair_seq = fc1.text_input("수리구분 직접입력",
                                    value=edit_order.get("repair_seq", ""),
                                    placeholder="예: 수리3, 재작업 등",
                                    key=f"seq_input_{edit_id}")
    else:
        cur_seq = edit_order.get("repair_seq", "수리1")
        if cur_seq not in all_seqs:
            all_seqs.append(cur_seq)
        repair_seq = fc1.selectbox("수리 구분", all_seqs,
                                   index=all_seqs.index(cur_seq),
                                   key=f"seq_sel_{edit_id}")

    worker    = fc2.text_input("담당 기술자", value=edit_order.get("worker",""))
    wo_status = fc3.selectbox("작업 상태", ["진행중","완료"],
                              index=0 if edit_order.get("status","진행중") == "진행중" else 1)

    description = st.text_area("수리 내용", value=edit_order.get("description",""), height=80)

    # 세부 작업 내역 입력 (등록 시 함께)
    st.markdown("**세부 작업 내역**")
    d_type  = st.multiselect("유형", ["부품","소모품","공임","도장","엔진오일","보험","견인","기타"], key="d_type_new")
    d_name  = st.text_input("항목명", key="d_name_new")
    d_qty   = st.number_input("수량", min_value=0.1, step=0.1, value=1.0, key="d_qty_new")
    d_price_key = "d_price_new"
    d_price = st.text_input("단가(원)", value="", key=d_price_key, 
                            on_change=lambda: format_money_input(d_price_key))
    d_memo  = st.text_input("메모", key="d_memo_new")

    st.markdown("**비용 항목**")
    col1, col2, col3 = st.columns(3)
    parts_key = f"parts_amount_{edit_id or 'new'}"
    parts_amount = col1.text_input("부품금액 (엔진오일 제외, 원)", 
                                   value=fmt_money(edit_order.get("parts_amount",0)), 
                                   key=parts_key, 
                                   on_change=lambda: format_money_input(parts_key))
    tech_fee_key = f"tech_fee_{edit_id or 'new'}"
    tech_fee = col2.text_input("기술료 (공임, 원)", 
                               value=fmt_money(edit_order.get("tech_fee",0)), 
                               key=tech_fee_key, 
                               on_change=lambda: format_money_input(tech_fee_key))
    paint_key = f"paint_amount_{edit_id or 'new'}"
    paint_amount = col3.text_input("도장금액 (원)", 
                                   value=fmt_money(edit_order.get("paint_amount",0)), 
                                   key=paint_key, 
                                   on_change=lambda: format_money_input(paint_key))

    col4, col5, col6 = st.columns(3)
    engine_oil_liter = col4.number_input("엔진오일 (리터)", min_value=0.0, step=0.5,
                                          value=float(edit_order.get("engine_oil_liter",0) or 0))
    engine_oil_unit_key = f"engine_oil_unit_{edit_id or 'new'}"
    engine_oil_unit = col5.text_input("엔진오일 단가 (원/리터)", 
                                      value=fmt_money(edit_order.get("engine_oil_unit", ENGINE_OIL_UNIT_PRICE)), 
                                      key=engine_oil_unit_key, 
                                      on_change=lambda: format_money_input(engine_oil_unit_key))
    towing_key = f"towing_fee_{edit_id or 'new'}"
    towing_fee = col6.text_input("견인비 (원)", 
                                 value=fmt_money(edit_order.get("towing_fee",0)), 
                                 key=towing_key, 
                                 on_change=lambda: format_money_input(towing_key))
    insurance_key = f"insurance_fee_{edit_id or 'new'}"
    insurance_fee = st.text_input("보험료 (원)", 
                                  value=fmt_money(edit_order.get("insurance_fee",0)), 
                                  key=insurance_key, 
                                  on_change=lambda: format_money_input(insurance_key))

    from utils.calculations import calc_engine_oil, calc_total, calc_vat
    def safe_int(value):
        cleaned = value.replace(",", "").replace("원", "")
        return int(cleaned) if cleaned else 0
    
    oil_amt   = calc_engine_oil(engine_oil_liter, safe_int(st.session_state.get(engine_oil_unit_key, "0")))
    vat_amt   = calc_vat(safe_int(st.session_state.get(tech_fee_key, "0")))
    total_amt = calc_total(safe_int(st.session_state.get(parts_key, "0")), oil_amt, 
                           safe_int(st.session_state.get(towing_key, "0")), 
                           safe_int(st.session_state.get(insurance_key, "0")), 
                           safe_int(st.session_state.get(tech_fee_key, "0")))
    preview   = (f"계산 미리보기 | 엔진오일: {fmt_money(oil_amt)} | "
                 f"부가세: {fmt_money(vat_amt)} | 총계: {fmt_money(total_amt)}")
    if safe_int(st.session_state.get(paint_key, "0")) > 0:
        preview += f" | 도장금액: {fmt_money(safe_int(st.session_state.get(paint_key, '0')))}"
    st.info(preview)

    completed_at = None
    if wo_status == "완료":
        completed_at = st.date_input("완료일", value=date.today())

    submitted = st.button(
        "저장" if edit_id else "등록", type="primary", use_container_width=True)

    if submitted:
        if v_status in ("입고", "진단"):
            sb.table("vehicles").update({"status": "수리중"}).eq("id", vehicle_id).execute()
        def safe_int(value):
            cleaned = value.replace(",", "").replace("원", "")
            return int(cleaned) if cleaned else 0
        
        data = {
            "vehicle_id": vehicle_id, "repair_seq": repair_seq,
            "description": description.strip() or None,
            "worker": worker.strip() or None,
            "parts_amount": safe_int(st.session_state.get(parts_key, "0")),
            "engine_oil_liter": engine_oil_liter,
            "engine_oil_unit": safe_int(st.session_state.get(engine_oil_unit_key, "0")),
            "towing_fee": safe_int(st.session_state.get(towing_key, "0")),
            "insurance_fee": safe_int(st.session_state.get(insurance_key, "0")),
            "tech_fee": safe_int(st.session_state.get(tech_fee_key, "0")),
            "paint_amount": safe_int(st.session_state.get(paint_key, "0")),
            "status": wo_status,
            "completed_at": str(completed_at) if completed_at else None,
        }
        if edit_id:
            sb.table("work_orders").update(data).eq("id", edit_id).execute()
            st.success("작업지시서가 수정되었습니다.")
        else:
            result = sb.table("work_orders").insert(data).execute()
            new_id = result.data[0]['id']
            st.success("작업지시서가 등록되었습니다.")
            
            # 세부 내역 함께 등록
            if st.session_state.get("d_name_new", "").strip():
                def safe_int(value):
                    cleaned = value.replace(",", "").replace("원", "")
                    return int(cleaned) if cleaned else 0
                
                sb.table("order_details").insert({
                    "work_order_id": new_id,
                    "item_type": ",".join(st.session_state.get("d_type_new", [])),
                    "item_name": st.session_state.get("d_name_new", "").strip(),
                    "quantity": st.session_state.get("d_qty_new", 1.0),
                    "unit_price": safe_int(st.session_state.get("d_price_new", "0")),
                    "memo": st.session_state.get("d_memo_new", "").strip() or None,
                }).execute()
                st.success("세부 내역도 함께 등록되었습니다.")
            
            # PDF 다운로드
            details = sb.table("order_details").select("*").eq("work_order_id", new_id).execute().data or []
            pdf_data = generate_work_order_pdf([(data, details)], vehicle, customer)
            st.download_button(
                "📄 작업지시서 PDF 다운로드", 
                data=pdf_data, 
                file_name=f"work_order_{vehicle.get('plate_number', '')}_{new_id}.pdf", 
                mime="application/pdf"
            )
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
                "메모": d.get("memo","") or "",
            } for d in details]), use_container_width=True, hide_index=True)

        dc1, dc2, dc3, dc4 = st.columns([2,3,1,2])
        d_type  = dc1.multiselect("유형", ["부품","소모품","공임","도장","엔진오일","보험","견인","기타"])
        d_name  = dc2.text_input("항목명")
        d_qty   = dc3.number_input("수량", min_value=0.1, step=0.1, value=1.0)
        d_price_key = f"d_price_{edit_id}"
        d_price = dc4.text_input("단가(원)", value="", key=d_price_key, 
                                 on_change=lambda: format_money_input(d_price_key))
        d_memo  = st.text_input("메모")
        d_sub   = st.button("세부 내역 추가", use_container_width=True)

        if d_sub and d_name.strip():
            def safe_int(value):
                cleaned = value.replace(",", "").replace("원", "")
                return int(cleaned) if cleaned else 0
            
            sb.table("order_details").insert({
                "work_order_id": edit_id, "item_type": ",".join(d_type),
                "item_name": d_name.strip(), "quantity": d_qty,
                "unit_price": safe_int(st.session_state.get(d_price_key, "0")),
                "memo": d_memo.strip() or None,
            }).execute()
            st.rerun()
