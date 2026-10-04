from datetime import datetime, date
import streamlit as st
import pandas as pd

# 페이지 기본 설정
st.set_page_config(
    page_title="주식회사 범운해운항공 - 통합 물류 관리 시스템",
    page_icon="🚢",
    layout="wide"
)

# -------------------------------------------------------------------------
# [보안 및 사용자 계정 관리 시스템 초기화]
# -------------------------------------------------------------------------
if "user_db" not in st.session_state:
    st.session_state.user_db = {
        "admin": {"pw": "bomwoon123", "role": "관리자(대표)", "name": "이상복"},
        "staff1": {"pw": "1234", "role": "직원", "name": "담당직원"}
    }

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None


def login_screen():
    """로그인 화면 출력 함수"""
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        st.markdown("<h2 style='text-align: center; color: #1e3a8a;'>🚢 범운해운항공 물류 시스템</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 9.5pt;'>관계자 외 접속이 제한된 보안 구역입니다.</p><br>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            input_id = st.text_input("아이디 (ID)")
            input_pw = st.text_input("비밀번호 (Password)", type="password")
            submit_login = st.form_submit_button("로그인", use_container_width=True)
            
            if submit_login:
                if input_id in st.session_state.user_db and st.session_state.user_db[input_id]["pw"] == input_pw:
                    st.session_state.logged_in_user = input_id
                    st.session_state.user_role = st.session_state.user_db[input_id]["role"]
                    st.success(f"환영합니다, {st.session_state.user_db[input_id]['name']}님!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
        
        st.markdown("<p style='text-align: center; font-size: 8.5pt; color: #94a3b8; margin-top: 20px;'>* 초기 관리자 아이디: <b>admin</b> / 비밀번호: <b>bomwoon123</b></p>", unsafe_allow_html=True)


# 로그인이 안 되어 있다면 로그인 화면만 표시하고 중단
if not st.session_state.logged_in_user:
    login_screen()
    st.stop()


# -------------------------------------------------------------------------
# [메인 프로그램 상태 초기화]
# -------------------------------------------------------------------------
if "bl_data" not in st.session_state:
    st.session_state.bl_data = []

if "clients" not in st.session_state:
    st.session_state.clients = {
        "대한상사": {"사업자등록번호": "123-81-12345", "담당자": "김철수 부장", "전화번호": "02-555-1234", "이메일": "chulsoo@daehan.com"},
        "한국물류": {"사업자등록번호": "220-88-54321", "담당자": "박영희 과장", "전화번호": "032-333-5678", "이메일": "yhpark@hankooklogis.com"}
    }

if "meeting_notes" not in st.session_state:
    st.session_state.meeting_notes = []

if "daily_manifest" not in st.session_state:
    st.session_state.daily_manifest = []

if "client_tariffs" not in st.session_state:
    st.session_state.client_tariffs = {}

if "client_deposits" not in st.session_state:
    st.session_state.client_deposits = {}

if "accounting_records" not in st.session_state:
    st.session_state.accounting_records = []

if "work_logs" not in st.session_state:
    st.session_state.work_logs = []


# -------------------------------------------------------------------------
# 사이드바 설정 (로그인 정보 및 메뉴)
# -------------------------------------------------------------------------
st.sidebar.markdown("<h2 style='color: #1e3a8a;'>🚢 범운해운항공</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 8.5pt; color: #64748b;'>BOMWOON SHIPPING & AIR</p>", unsafe_allow_html=True)
st.sidebar.info(f"현재 접속자: **{st.session_state.user_db[st.session_state.logged_in_user]['name']}**님\n\n(권한: {st.session_state.user_role})")

if st.sidebar.button("로그아웃"):
    st.session_state.logged_in_user = None
    st.session_state.user_role = None
    st.rerun()

st.sidebar.markdown("---")

# 기본 메뉴 구성
menu_list = [
    "수출입 B/L 등록",
    "등록 B/L 수정 및 Profit 내역",
    "B/L 운송장 출력",
    "거래처 인보이스 발행",
    "화물 견적서 발행",
    "거래처 미팅 노트",
    "금일발송 매니페스트",
    "거래처 등록 요금 상세관리",
    "거래처 미수금관리",
    "일계표 및 입출금 장부",
    "업무용 일지"
]

# 접속한 계정이 관리자(대표)일 때만 메뉴에 '직원 계정 관리' 추가
if st.session_state.user_role == "관리자(대표)":
    menu_list.append("직원 계정 관리 (관리자 전용)")

menu = st.sidebar.selectbox("메인 메뉴 이동", menu_list)


# -------------------------------------------------------------------------
# [메뉴 1] 수출입 B/L 등록
# -------------------------------------------------------------------------
if menu == "수출입 B/L 등록":
    st.subheader("📦 수출입 B/L 및 Profit 등록 관리")
    
    with st.form("bl_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            job_no = st.text_input("Job 번호", value=f"BW-{datetime.now().strftime('%y%m%d')}-01")
            bl_no = st.text_input("B/L 번호")
            cargo_type = st.selectbox("화물 구분", ["수출 (Export)", "수입 (Import)", "삼국간 (Cross-Trade)"])
        with col2:
            client_name = st.selectbox("화주사 (Client)", list(st.session_state.clients.keys()) if st.session_state.clients else ["기본 화주"])
            pol = st.text_input("출발지 (POL)", placeholder="예: INC (Incheon)")
            pod = st.text_input("도착지 (POD)", placeholder="예: SHA (Shanghai)")
        with col3:
            item_name = st.text_input("품명 (Description)")
            box_count = st.number_input("수량 (Box/Pallet)", min_value=1, value=1)
            cbm = st.number_input("CBM / 용적중량", min_value=0.0, value=1.0, step=0.1)
            amount = st.number_input("청구 운임 (KRW)", min_value=0, value=150000, step=10000)
            
        submitted = st.form_submit_button("B/L 정보 저장하기")
        if submitted:
            new_entry = {
                "Job 번호": job_no,
                "B/L 번호": bl_no,
                "구분": cargo_type,
                "화주사": client_name,
                "POL": pol,
                "POD": pod,
                "품명": item_name,
                "수량": box_count,
                "CBM": cbm,
                "금액": amount,
                "등록일": str(date.today()),
                "등록자": st.session_state.user_db[st.session_state.logged_in_user]['name']
            }
            st.session_state.bl_data.append(new_entry)
            st.success(f"Job No. [{job_no}] B/L 데이터가 성공적으로 등록되었습니다!")


# -------------------------------------------------------------------------
# [메뉴 2] 등록 B/L 수정 및 Profit 내역
# -------------------------------------------------------------------------
elif menu == "등록 B/L 수정 및 Profit 내역":
    st.subheader("📋 등록된 B/L 목록 및 Profit 정산 내역")
    if st.session_state.bl_data:
        df_bl = pd.DataFrame(st.session_state.bl_data)
        st.dataframe(df_bl, use_container_width=True)
    else:
        st.info("등록된 B/L 내역이 없습니다.")


# -------------------------------------------------------------------------
# [메뉴 3] B/L 운송장 출력
# -------------------------------------------------------------------------
elif menu == "B/L 운송장 출력":
    st.subheader("📄 B/L 운송장 및 선적서류 출력")
    if st.session_state.bl_data:
        bl_options = [item["Job 번호"] + " / " + item["B/L 번호"] for item in st.session_state.bl_data]
        selected_bl_print = st.selectbox("출력할 B/L 선택", bl_options)
        st.info(f"선택하신 운송장 [{selected_bl_print}]의 인쇄 프리뷰를 제공합니다.")
    else:
        st.info("출력할 B/L 데이터가 없습니다.")


# -------------------------------------------------------------------------
# [메뉴 4] 거래처 인보이스 발행
# -------------------------------------------------------------------------
elif menu == "거래처 인보이스 발행":
    st.subheader("🧾 해운·항공 운임 청구서 (Invoice) 발행")
    if not st.session_state.clients:
        st.warning("등록된 거래처가 없습니다.")
    else:
        selected_inv_client = st.selectbox("청구 대상 화주사 선택", list(st.session_state.clients.keys()))
        client_info_inv = st.session_state.clients[selected_inv_client]
        
        client_bls = [item for item in st.session_state.bl_data if item.get('화주사') == selected_inv_client]
        base_supply_amount = sum([item.get('금액', 0) for item in client_bls]) if client_bls else 150000
        
        st.info(f"선택하신 화주사 [{selected_inv_client}]의 청구 예정 금액 합계: **{base_supply_amount:,} 원**")


# -------------------------------------------------------------------------
# [메뉴 5] 화물 견적서 발행
# -------------------------------------------------------------------------
elif menu == "화물 견적서 발행":
    st.subheader("📊 화물 운송 견적서 발행")
    st.info("고객사 제출용 해상/항공 운송 견적서를 작성합니다.")


# -------------------------------------------------------------------------
# [메뉴 6] 거래처 미팅 노트
# -------------------------------------------------------------------------
elif menu == "거래처 미팅 노트":
    st.subheader("📝 거래처 미팅 및 영업 일지")
    with st.form("meeting_form"):
        m_client = st.selectbox("미팅 거래처", list(st.session_state.clients.keys()) if st.session_state.clients else ["기본"])
        m_content = st.text_area("미팅 내용 및 특이사항")
        m_submitted = st.form_submit_button("미팅 노트 저장")
        if m_submitted:
            st.session_state.meeting_notes.append({"거래처": m_client, "내용": m_content, "날짜": str(date.today())})
            st.success("미팅 노트가 저장되었습니다.")


# -------------------------------------------------------------------------
# [메뉴 7] 금일발송 매니페스트
# -------------------------------------------------------------------------
elif menu == "금일발송 매니페스트":
    st.subheader("🚢 금일 발송 화물 매니페스트 (Manifest)")
    if st.session_state.bl_data:
        st.dataframe(pd.DataFrame(st.session_state.bl_data), use_container_width=True)
    else:
        st.info("금일 발송된 화물 내역이 없습니다.")


# -------------------------------------------------------------------------
# [메뉴 8] 거래처 등록 요금 상세관리
# -------------------------------------------------------------------------
elif menu == "거래처 등록 요금 상세관리":
    st.subheader("💰 거래처별 계약 요금 상세 관리")
    st.info("화주사별 맞춤 계약 운임 관리 영역입니다.")


# -------------------------------------------------------------------------
# [메뉴 9] 거래처 미수금관리
# -------------------------------------------------------------------------
elif menu == "거래처 미수금관리":
    st.subheader("📉 거래처 미수금 및 입금 현황 관리")
    st.info("미수금 잔액 및 입금 내역 정산 영역입니다.")


# -------------------------------------------------------------------------
# [메뉴 10] 일계표 및 입출금 장부
# -------------------------------------------------------------------------
elif menu == "일계표 및 입출금 장부":
    st.subheader("📈 일계표 및 현금/통장 입출금 장부")
    st.info("전체 회계 입출금 장부 관리 영역입니다.")


# -------------------------------------------------------------------------
# [메뉴 11] 업무용 일지
# -------------------------------------------------------------------------
elif menu == "업무용 일지":
    st.subheader("📌 사내 업무 일지 작성 및 공유")
    with st.form("worklog_form"):
        w_title = st.text_input("업무 제목")
        w_content = st.text_area("상세 업무 내용")
        w_submitted = st.form_submit_button("업무일지 등록")
        if w_submitted:
            st.session_state.work_logs.append({"제목": w_title, "작성자": st.session_state.user_db[st.session_state.logged_in_user]['name'], "날짜": str(date.today())})
            st.success("업무일지가 등록되었습니다.")


# -------------------------------------------------------------------------
# [메뉴 12] 직원 계정 관리 (관리자(대표) 전용 메뉴)
# -------------------------------------------------------------------------
elif menu == "직원 계정 관리 (관리자 전용)":
    st.subheader("🔑 직원 계정 생성 및 권한 관리 (대표님 전용)")
    st.markdown("직원들이 프로그램에 로그인할 수 있는 **새로운 아이디와 비밀번호**를 생성하거나 기존 계정을 관리할 수 있습니다.")
    
    with st.form("new_account_form"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            new_id = st.text_input("새로운 직원 아이디 (ID)")
        with col_b:
            new_pw = st.text_input("초기 비밀번호 (Password)")
        with col_c:
            new_name = st.text_input("직원 성명 (또는 부서명)")
            
        create_account_btn = st.form_submit_button("직원 계정 생성하기")
        
        if create_account_btn:
            if not new_id or not new_pw or not new_name:
                st.error("아이디, 비밀번호, 직원 성명을 모두 입력해 주세요.")
            elif new_id in st.session_state.user_db:
                st.error(f"이미 존재하는 아이디 [{new_id}]입니다. 다른 아이디를 입력해 주세요.")
            else:
                st.session_state.user_db[new_id] = {
                    "pw": new_pw,
                    "role": "직원",
                    "name": new_name
                }
                st.success(f"성공적으로 직원 계정이 생성되었습니다! (아이디: {new_id} / 이름: {new_name})")

    st.markdown("---")
    st.subheader("👥 현재 등록된 전체 시스템 계정 목록")
    
    user_list_display = []
    for uid, info in st.session_state.user_db.items():
        user_list_display.append({
            "아이디(ID)": uid,
            "성명/부서": info["name"],
            "권한 등급": info["role"]
        })
    
    st.dataframe(pd.DataFrame(user_list_display), use_container_width=True)
    st.info("💡 초기 관리자 계정(admin)은 삭제되지 않으며, 직원의 아이디와 초기 비밀번호를 생성하여 직원분들께 안내해 주시면 됩니다.")

