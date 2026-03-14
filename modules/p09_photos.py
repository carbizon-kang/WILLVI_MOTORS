"""사진 관리 - 수리 전/중/후 사진"""
import streamlit as st
from database.connection import get_supabase
from utils.styles import apply_global_style, page_header, section_title

LABELS = ['입고전', '수리중', '출고전', '기타']
LABEL_ICON = {'입고전': '📥', '수리중': '🔧', '출고전': '📤', '기타': '📎'}


def render():
    apply_global_style()
    page_header("사진 관리", "차량별 수리 사진 업로드 및 조회")
    sb = get_supabase()

    # ── 차량 선택
    vehicles = sb.table("vehicles") \
        .select("id, plate_number, model, status") \
        .order("intake_date", desc=True) \
        .execute().data or []

    if not vehicles:
        st.info("등록된 차량이 없습니다.")
        return

    search = st.text_input("차량번호 검색")
    filtered = [v for v in vehicles
                if not search or search.lower() in (v.get("plate_number") or "").lower()]

    opts = {f"{v['plate_number']} | {v.get('model','')} | {v.get('status','')}": v['id']
            for v in filtered}
    if not opts:
        st.warning("검색 결과 없음")
        return

    sel_label = st.selectbox("차량 선택", list(opts.keys()))
    vehicle_id = opts[sel_label]

    st.divider()

    # ── 사진 업로드
    st.subheader("사진 업로드")
    col_up1, col_up2 = st.columns(2)
    label = col_up1.selectbox("사진 구분", LABELS)
    memo  = col_up2.text_input("메모 (선택)")

    uploaded_files = st.file_uploader(
        "사진 선택 (여러 장 가능)",
        type=["jpg", "jpeg", "png", "heic", "webp"],
        accept_multiple_files=True,
    )

    if uploaded_files and st.button("📤 업로드", type="primary"):
        success_cnt = 0
        for uf in uploaded_files:
            try:
                from utils.photo_upload import upload_photo
                file_bytes = uf.read()
                url = upload_photo(file_bytes, uf.name, vehicle_id)
                sb.table("repair_photos").insert({
                    "vehicle_id": vehicle_id,
                    "label": label,
                    "file_url": url,
                    "file_name": uf.name,
                    "memo": memo.strip() or None,
                }).execute()
                success_cnt += 1
            except Exception as e:
                st.error(f"업로드 실패 ({uf.name}): {e}")
        if success_cnt:
            st.success(f"✅ {success_cnt}장 업로드 완료")
            st.rerun()

    st.divider()

    # ── 기존 사진 조회 (구분별 탭)
    photos = sb.table("repair_photos") \
        .select("*") \
        .eq("vehicle_id", vehicle_id) \
        .order("taken_at", desc=True) \
        .execute().data or []

    if not photos:
        st.info("등록된 사진이 없습니다.")
        return

    tabs = st.tabs([f"{LABEL_ICON.get(lb, '')} {lb} ({sum(1 for p in photos if p['label']==lb)})"
                    for lb in LABELS])

    for tab, lb in zip(tabs, LABELS):
        with tab:
            lb_photos = [p for p in photos if p.get("label") == lb]
            if not lb_photos:
                st.caption("사진 없음")
                continue

            cols = st.columns(3)
            for i, ph in enumerate(lb_photos):
                with cols[i % 3]:
                    url = ph.get("file_url", "")
                    fname = ph.get("file_name", "")
                    taken = (ph.get("taken_at") or "")[:16]
                    memo_txt = ph.get("memo") or ""

                    if url:
                        st.image(url, caption=f"{fname}\n{taken}", use_container_width=True)
                    else:
                        st.markdown(f"🖼️ {fname}")

                    if memo_txt:
                        st.caption(memo_txt)

                    # 공유 링크
                    if st.button("🔗 링크 복사", key=f"link_{ph['id']}"):
                        st.code(url)

                    # 삭제
                    if st.button("🗑️ 삭제", key=f"del_{ph['id']}"):
                        try:
                            from utils.photo_upload import delete_photo
                            delete_photo(url)
                        except Exception:
                            pass
                        sb.table("repair_photos").delete().eq("id", ph["id"]).execute()
                        st.rerun()
