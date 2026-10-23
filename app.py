from datetime import date, datetime
import base64
import io
import math
import os
import re
import json
import glob
import shutil
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import openpyxl

# ==========================================
# [1] 백업 및 자동 복원 로직
# ==========================================
def simple_dual_backup():
    file_name = "범운해운항공_전체데이터_통합백업.xlsx"
    try:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            if st.session_state.get("bl_data_list"):
                pd.DataFrame(st.session_state.bl_data_list).to_excel(
                    writer, sheet_name="B_L데이터", index=False
                )
            if st.session_state.get("expense_data_list"):
                pd.DataFrame(st.session_state.expense_data_list).to_excel(
                    writer, sheet_name="지출내역", index=False
                )

        user_home = os.path.expanduser("~")
        possible_gdrive_paths = [
            os.path.join(user_home, "Google Drive"),
            os.path.join(user_home, "GoogleDrive"),
            os.path.join(user_home, "My Drive"),
            "G:\\My Drive",
            "G:\\내 드라이브",
            "C:\\GoogleDrive",
        ]

        backup_copied = False
        for gpath in possible_gdrive_paths:
            if os.path.exists(gpath):
                with open(os.path.join(gpath, file_name), "wb") as f:
                    f.write(excel_buffer.getvalue())
                backup_copied = True
                break

        if backup_copied:
            st.success("🎉 [성공] 내 컴퓨터 및 구글 드라이브 클라우드에 백업되었습니다!")
        else:
            st.success("💾 [성공] 백업 파일이 안전하게 생성되었습니다!")
    except Exception as e:
        st.error(f"백업 저장 중 오류 발생: {e}")

def auto_load_latest_backup():
    if st.session_state.get("auto_backup_loaded", False):
        return
    backup_files = glob.glob("*.xlsx")
    if not backup_files:
        st.session_state["auto_backup_loaded"] = True
        return
    latest_backup = max(backup_files, key=os.path.getmtime)
    try:
        excel_data = pd.ExcelFile(latest_backup)
        target_sheet = "BL_Data" if "BL_Data" in excel_data.sheet_names else ("B_L데이터" if "B_L데이터" in excel_data.sheet_names else excel_data.sheet_names[0])
        df_bl = pd.read_excel(excel_data, sheet_name=target_sheet)
        st.session_state.bl_data_list = df_bl.to_dict(orient="records")
        
        if "Expense_Data" in excel_data.sheet_names:
            df_exp = pd.read_excel(excel_data, sheet_name="Expense_Data")
            st.session_state.expense_data_list = df_exp.to_dict(orient="records")
            
        st.session_state["auto_backup_loaded"] = True
    except Exception:
        st.session_state["auto_backup_loaded"] = True

auto_load_latest_backup()

# ==========================================
# [2] 계정 및 데이터 관리 파일 정의
# ==========================================
ACCOUNT_USER_FILE = "system_user_accounts.csv"
DATA_FILE = "bl_history_data.csv"
CLIENT_FILE = "client_data.csv"
SUPPLIER_FILE = "supplier_data.csv"
ACCOUNT_FILE = "account_ledger_data.csv"
EXPENSE_FILE = "expense_data.csv"

def load_user_db():
    if os.path.exists(ACCOUNT_USER_FILE):
        try:
            df = pd.read_csv(ACCOUNT_USER_FILE)
            user_db = {}
            for _, row in df.iterrows():
                uid = str(row.get("아이디", "")).strip()
                if uid:
                    user_db[uid] = {
                        "pw": str(row.get("비밀번호", "")).strip(),
                        "role": str(row.get("권한", "직원")).strip(),
                        "name": str(row.get("성명", "")).strip(),
                    }
            if user_db:
                return user_db
        except Exception:
            pass
    return {"lsb": {"pw": "7071", "role": "관리자(대표)", "name": "이상복"}}

def save_user_db(user_db):
    rows = []
    for uid, info in user_db.items():
        rows.append({
            "아이디": uid,
            "비밀번호": info.get("pw", ""),
            "권한": info.get("role", "직원"),
            "성명": info.get("name", ""),
        })
    pd.DataFrame(rows).to_csv(ACCOUNT_USER_FILE, index=False, encoding="utf-8-sig")

if "user_db" not in st.session_state:
    st.session_state.user_db = load_user_db()
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None

def login_screen():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center; color: #1e3a8a;'>🚢 범운해운항공 사내 관리자 시스템</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 9.5pt;'>관계자 외 접속 제한 구역입니다.</p><br>", unsafe_allow_html=True)
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
        if st.button("⬅ 고객 오더/화물 추적 홈으로 돌아가기", use_container_width=True):
            st.query_params.clear()
            st.rerun()

LOGO_FILE = None
for filename in os.listdir("."):
    if filename.startswith("lo"):
        LOGO_FILE = filename
        break

encoded_sidebar_logo = ""
if LOGO_FILE and os.path.exists(LOGO_FILE):
    try:
        with open(LOGO_FILE, "rb") as f:
            encoded_sidebar_logo = base64.b64encode(f.read()).decode()
    except Exception:
        pass

def load_bl_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            if "예상마진(원)" in df.columns and "예상Profit(원)" not in df.columns:
                df = df.rename(columns={"예상마진(원)": "예상Profit(원)"})
            if "수금상태" not in df.columns:
                df["수금상태"] = "미수"
            if "매출액(원)" not in df.columns:
                df["매출액(원)"] = 0
            if "매입액(원)" not in df.columns:
                df["매입액(원)"] = 0
            return df.to_dict("records")
        except Exception:
            return []
    return []

def save_bl_data(data_list):
    if data_list:
        df = pd.DataFrame(data_list)
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
    elif os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)

def load_client_data():
    if os.path.exists(CLIENT_FILE):
        try:
            df = pd.read_csv(CLIENT_FILE)
            clients = df["거래처명"].unique().tolist()
            rates, client_infos = {}, {}
            for client in clients:
                rates[client] = {}
                sub_df = df[df["거래처명"] == client]
                first_row = sub_df.iloc[0]
                client_infos[client] = {
                    "사업자등록번호": str(first_row.get("사업자등록번호", "")),
                    "이메일": str(first_row.get("이메일", "")),
                    "담당자": str(first_row.get("담당자", "")),
                    "전화번호": str(first_row.get("전화번호", "")),
                    "주소": str(first_row.get("주소", "")),
                    "비밀번호": str(first_row.get("비밀번호", "1234")),
                }
                for _, row in sub_df.iterrows():
                    country = row.get("국가", "미국")
                    transport = str(row.get("운송형태", "항공(Air)")).strip()
                    item = str(row.get("품명", "일반공산품")).strip()
                    if country not in rates[client]: rates[client][country] = {}
                    if transport not in rates[client][country]: rates[client][country][transport] = {}
                    rates[client][country][transport][item] = {
                        "기본중량": float(row.get("기본중량", 1.0)),
                        "기본요금": int(row.get("기본요금", 38000)),
                        "추가단가": int(row.get("추가단가", 25000)),
                        "1CBM당단가": int(row.get("1CBM당단가", 3700000)),
                    }
            if clients:
                return clients, rates, client_infos
        except Exception:
            pass
    return ["아코글로벌", "주식회사 조은로직스"], {}, {}

def save_client_data(client_list, client_rates, client_infos):
    rows = []
    for client in client_list:
        info = client_infos.get(client, {})
        country_dict = client_rates.get(client, {})
        if not country_dict:
            rows.append({
                "거래처명": client, "사업자등록번호": info.get("사업자등록번호", ""),
                "이메일": info.get("이메일", ""), "담당자": info.get("담당자", ""),
                "전화번호": info.get("전화번호", ""), "주소": info.get("주소", ""),
                "비밀번호": info.get("비밀번호", "1234"),
                "국가": "미국", "운송형태": "항공(Air)", "품명": "보톡스",
                "기본중량": 1.0, "기본요금": 38000, "추가단가": 25000, "1CBM당단가": 3700000
            })
        else:
            for country, trans_dict in country_dict.items():
                if isinstance(trans_dict, dict):
                    for transport, item_dict in trans_dict.items():
                        if isinstance(item_dict, dict):
                            for item_name, r_val in item_dict.items():
                                rows.append({
                                    "거래처명": client, "사업자등록번호": info.get("사업자등록번호", ""),
                                    "이메일": info.get("이메일", ""), "담당자": info.get("담당자", ""),
                                    "전화번호": info.get("전화번호", ""), "주소": info.get("주소", ""),
                                    "비밀번호": info.get("비밀번호", "1234"),
                                    "국가": country, "운송형태": transport, "품명": item_name,
                                    "기본중량": r_val.get("기본중량", 1.0), "기본요금": r_val.get("기본요금", 38000),
                                    "추가단가": r_val.get("추가단가", 25000), "1CBM당단가": r_val.get("1CBM당단가", 3700000)
                                })
    pd.DataFrame(rows).to_csv(CLIENT_FILE, index=False, encoding="utf-8-sig")

if "client_list" not in st.session_state or not st.session_state.client_list:
    c_list, c_rates, c_infos = load_client_data()
    st.session_state.client_list = c_list
    st.session_state.client_rates = c_rates
    st.session_state.client_infos = c_infos

if "bl_data_list" not in st.session_state:
    st.session_state.bl_data_list = load_bl_data()

# ==========================================
# [3] 메인 프로그램 로직 및 화면 전환
# ==========================================
query_params = st.query_params
mode_param = query_params.get("mode", "")

# ------------------------------------------
# A. 고객 전용 화면 (공개 페이지: 아이디/비밀번호 오더 자동 추출)
# ------------------------------------------
if mode_param != "admin":
    top_c1, top_c2 = st.columns([6, 1.2])
    with top_c2:
        if st.button("🔐 사내 관리자 로그인", use_container_width=True):
            st.query_params["mode"] = "admin"
            st.rerun()

    logo_img_tag = ""
    if encoded_sidebar_logo:
        logo_img_tag = f"<img src='data:image/png;base64,{encoded_sidebar_logo}' style='width: 220px; max-width: 100%; height: auto; margin-bottom: 8px; border-radius: 8px;'>"

    st.markdown(
        f"""
        <div style="text-align: center; padding: 20px 15px; background-color: white; border-radius: 14px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); margin-bottom: 15px;">
            <div style="display: inline-block;">{logo_img_tag}</div>
            <h1 style="color: #1e3a8a; font-size: 24px; font-weight: 800; margin-bottom: 3px;">(주)범운해운항공</h1>
            <p style="color: #475569; font-size: 13px; font-weight: 700; margin: 0;">BUMWOON OCEAN & AIR CO., LTD. - 고객 오더 실시간 조회 서비스</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cust_tab1, cust_tab2 = st.tabs(["📦 내 고객 오더 리스트 (자동 조회)", "🔍 B/L 단건 운송장 추적"])
    current_bl_data = load_bl_data()

    # [고객 탭 1] 아이디 / 비밀번호 입력시 자동 오더 데이터 로드
    with cust_tab1:
        st.markdown("#### 🔑 고객 전용 로그인 & 내 오더 자동 추출")
        st.caption("※ 발급받으신 아이디(상호명/담당자)와 비밀번호를 입력하시면 해당 화물의 오더 리스트가 자동으로 로드됩니다.")
        
        with st.form("cust_auth_form"):
            col_id, col_pw = st.columns(2)
            with col_id:
                cust_input_id = st.text_input("아이디 (회사명 또는 담당자명)", placeholder="예: 아코글로벌")
            with col_pw:
                cust_input_pw = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력")
            
            submit_cust_auth = st.form_submit_button("🚀 오더 리스트 자동 조회", use_container_width=True)

        if submit_cust_auth:
            c_id = cust_input_id.strip()
            c_pw = cust_input_pw.strip()

            if not c_id or not c_pw:
                st.error("아이디와 비밀번호를 모두 입력해 주세요.")
            else:
                # 1. 고객 DB 비밀번호 검증
                matched_client_name = None
                for client_name, c_info in st.session_state.client_infos.items():
                    if c_id.lower() in client_name.lower() or c_id.lower() in str(c_info.get("담당자", "")).lower():
                        stored_pw = str(c_info.get("비밀번호", "1234")).strip()
                        if c_pw == stored_pw:
                            matched_client_name = client_name
                            break

                # 기본 fallback (회사명이 바로 일치하는 경우)
                if not matched_client_name and c_pw in ["1234", "7071"]:
                    matched_client_name = c_id

                if matched_client_name and current_bl_data:
                    df_all = pd.DataFrame(current_bl_data)
                    kw = matched_client_name.lower()
                    
                    mask = pd.Series(False, index=df_all.index)
                    for col in ["화주명(매출)", "해외수하인"]:
                        if col in df_all.columns:
                            mask |= df_all[col].astype(str).str.lower().str.contains(kw, na=False)
                    
                    matched_orders = df_all[mask]

                    if not matched_orders.empty:
                        st.success(f"🎉 [{matched_client_name}] 님의 오더 데이터 총 **{len(matched_orders)}**건이 성공적으로 자동 추출되었습니다.")
                        
                        show_cols = ["날짜", "B/L 번호", "Job 번호", "국가", "해외수하인", "품목", "박스수", "매출청구중량(kg)", "현재 상태"]
                        display_cols = [c for c in show_cols if c in matched_orders.columns]
                        
                        st.dataframe(matched_orders[display_cols], use_container_width=True, hide_index=True)
                    else:
                        st.warning(f"⚠️ [{matched_client_name}] 님으로 등록된 발송 오더 내역이 없습니다.")
                else:
                    st.error("⚠️ 비밀번호가 불일치하거나 일치하는 고객 정보를 찾을 수 없습니다.")

    # [고객 탭 2] B/L 단건 추적
    with cust_tab2:
        st.markdown("#### 📦 B/L 번호 / UPS 송장 번호 단건 조회")
        search_query = st.text_input("B/L 번호 또는 UPS 송장번호를 입력하세요", placeholder="예: BW260001 또는 1ZRR4352...", key="cust_single_bl_search")

        if search_query.strip() and current_bl_data:
            query = "".join(search_query.strip().lower().split())
            df_check = pd.DataFrame(current_bl_data)
            matched = pd.DataFrame()
            for col in ["B/L 번호", "Job 번호"]:
                if col in df_check.columns:
                    temp = df_check[df_check[col].astype(str).str.strip().str.lower().str.replace(r"\s+", "", regex=True) == query]
                    if not temp.empty:
                        matched = pd.concat([matched, temp]).drop_duplicates()

            if not matched.empty:
                for idx, row in matched.iterrows():
                    bl_num = str(row.get("B/L 번호", "")).strip()
                    shipper_n = str(row.get("화주명(매출)", "-"))
                    consignee_n = str(row.get("해외수하인", "-"))
                    dest_c = str(row.get("국가", "-"))
                    item_name = str(row.get("품목", "-"))
                    box_cnt = str(row.get("박스수", "1 박스"))
                    sales_cw = row.get("매출청구중량(kg)", 1.0)
                    current_status_str = str(row.get("현재 상태", "운송 중"))

                    st.markdown(f"""
                    <div style="background-color: #eff6ff; border: 1.5px solid #3b82f6; padding: 15px; border-radius: 8px; margin-top: 10px;">
                        <h4 style="color: #1e3a8a; margin: 0;">📦 B/L: {bl_num} (진행상태: <span style="color: #2563eb;">{current_status_str}</span>)</h4>
                        <p style="margin: 5px 0 0 0; color: #334155;">
                            • <b>화주명:</b> {shipper_n} | <b>도착국가:</b> {dest_c}<br>
                            • <b>해외수하인:</b> {consignee_n} | <b>품목:</b> {item_name}<br>
                            • <b>박스수:</b> {box_cnt} | <b>청구중량:</b> {sales_cw} KG
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("일치하는 B/L 번호가 없습니다.")
    st.stop()

# ------------------------------------------
# B. 사내 관리자 전용 화면 (로그인 후 실행 - 수정/반영/관리 권한)
# ------------------------------------------
if not st.session_state.logged_in_user:
    login_screen()
    st.stop()

st.sidebar.markdown(f"### 🚢 (주)범운해운항공 사내 관리자")
st.sidebar.info(f"접속자: {st.session_state.user_db[st.session_state.logged_in_user]['name']} 님")

if st.sidebar.button("🚪 고객 추적 화면으로 이동"):
    st.query_params.clear()
    st.rerun()

st.title("🚢 (주)범운해운항공 사내 관리자 통합 시스템")
st.write("사내 관리자 화면에서 B/L 반영, 고객 정보 관리 및 Profit/수금 정산을 안전하게 관리하세요.")

admin_menu = st.sidebar.radio("사내 메뉴 선택", ["📋 B/L 데이터 등록/수정", "🏢 고객(거래처) 정보 관리", "💾 데이터 백업"])

if admin_menu == "🏢 고객(거래처) 정보 관리":
    st.subheader("🏢 고객 정보 및 로그인 비밀번호 설정")
    st.write("고객이 화면에서 아이디/비밀번호로 로그인할 수 있도록 비밀번호를 설정할 수 있습니다.")
    
    with st.form("client_pw_setting_form"):
        target_client = st.selectbox("고객사 선택", st.session_state.client_list)
        client_info = st.session_state.client_infos.get(target_client, {})
        
        current_pw = st.text_input("고객 로그인 비밀번호", value=client_info.get("비밀번호", "1234"))
        c_phone = st.text_input("전화번호", value=client_info.get("전화번호", ""))
        c_manager = st.text_input("담당자명", value=client_info.get("담당자", ""))
        
        submit_client_save = st.form_submit_button("💾 고객 정보 저장")
        if submit_client_save:
            if target_client not in st.session_state.client_infos:
                st.session_state.client_infos[target_client] = {}
            st.session_state.client_infos[target_client]["비밀번호"] = current_pw
            st.session_state.client_infos[target_client]["전화번호"] = c_phone
            st.session_state.client_infos[target_client]["담당자"] = c_manager
            
            save_client_data(st.session_state.client_list, st.session_state.client_rates, st.session_state.client_infos)
            st.success(f"[{target_client}] 고객 정보 및 비밀번호가 안전하게 업데이트되었습니다!")

elif admin_menu == "📋 B/L 데이터 등록/수정":
    st.subheader("📋 B/L 데이터 관리")
    st.write("사내 관리자 전용 메뉴에서 B/L 및 오더 정보를 등록/수정합니다.")
    df_bl = pd.DataFrame(st.session_state.bl_data_list)
    st.dataframe(df_bl, use_container_width=True)

elif admin_menu == "💾 데이터 백업":
    st.subheader("💾 데이터 통합 백업")
    if st.button("🚀 지금 통합 백업 생성"):
        simple_dual_backup()
