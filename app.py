from datetime import date, datetime
import base64
import io
import math
import os
import re
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import json
import glob
import shutil
import openpyxl 

def simple_dual_backup():
    file_name = "범운해운항공_전체데이터_통합백업.xlsx"
    try:
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
                shutil.copy(file_name, os.path.join(gpath, file_name))
                backup_copied = True
                break
    except Exception as e:
        pass

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
        target_sheet = "BL_Data" if "BL_Data" in excel_data.sheet_names else excel_data.sheet_names[0]
        df_bl = pd.read_excel(excel_data, sheet_name=target_sheet)
        st.session_state.bl_data_list = df_bl.to_dict(orient="records")
        if "Expense_Data" in excel_data.sheet_names:
            df_exp = pd.read_excel(excel_data, sheet_name="Expense_Data")
            st.session_state.expense_list = df_exp.to_dict(orient="records")
        st.session_state["auto_backup_loaded"] = True
    except Exception as e:
        st.session_state["auto_backup_loaded"] = True

auto_load_latest_backup()

ACCOUNT_USER_FILE = "system_user_accounts.csv"

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
        st.markdown("<h2 style='text-align: center; color: #1e3a8a;'>🚢 범운해운항공 물류 시스템</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            input_id = st.text_input("아이디 (ID)")
            input_pw = st.text_input("비밀번호 (Password)", type="password")
            submit_login = st.form_submit_button("로그인", use_container_width=True)
            if submit_login:
                if input_id in st.session_state.user_db and st.session_state.user_db[input_id]["pw"] == input_pw:
                    st.session_state.logged_in_user = input_id
                    st.session_state.user_role = st.session_state.user_db[input_id]["role"]
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

DATA_FILE = "bl_history_data.csv"
CLIENT_FILE = "client_data.csv"
SUPPLIER_FILE = "supplier_data.csv"
ACCOUNT_FILE = "account_ledger_data.csv"
EXPENSE_FILE = "expense_data.csv"
NOTE_FILE = "daily_note_data.csv"
MEETING_FILE = "meeting_note_data.csv"
QUOTATION_FILE = "quotation_data.csv"

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
                }
            if clients:
                return clients, rates, client_infos
        except Exception:
            pass
    return ["아코글로벌", "주식회사 조은로직스"], {}, {}

def load_supplier_data():
    if os.path.exists(SUPPLIER_FILE):
        try:
            df = pd.read_csv(SUPPLIER_FILE)
            suppliers = df["거래처명"].unique().tolist()
            rates, supplier_infos = {}, {}
            for supplier in suppliers:
                rates[supplier] = {}
                sub_df = df[df["거래처명"] == supplier]
                first_row = sub_df.iloc[0]
                supplier_infos[supplier] = {
                    "사업자등록번호": str(first_row.get("사업자등록번호", "")),
                    "이메일": str(first_row.get("이메일", "")),
                    "담당자": str(first_row.get("담당자", "")),
                    "전화번호": str(first_row.get("전화번호", "")),
                    "주소": str(first_row.get("주소", "")),
                }
            if suppliers:
                return suppliers, rates, supplier_infos
        except Exception:
            pass
    return ["(주)카스익스프레스", "ESI"], {}, {}

if "client_list" not in st.session_state or not st.session_state.client_list:
    c_list, c_rates, c_infos = load_client_data()
    st.session_state.client_list = c_list
    st.session_state.client_rates = c_rates
    st.session_state.client_infos = c_infos

if "supplier_list" not in st.session_state or not st.session_state.supplier_list:
    s_list, s_rates, s_infos = load_supplier_data()
    st.session_state.supplier_list = s_list
    st.session_state.supplier_rates = s_rates
    st.session_state.supplier_infos = s_infos

if "bl_data_list" not in st.session_state:
    st.session_state.bl_data_list = load_bl_data()

COUNTRY_LIST = ["미국", "중국", "호주", "태국", "인도", "멕시코", "홍콩", "베트남", "기타 국가"]

# ==========================================
# 사이드바 및 메인 메뉴
# ==========================================
st.sidebar.markdown("### 🚢 (주)범운해운항공")

current_user_name = "이상복"
if st.session_state.logged_in_user and st.session_state.user_db:
    current_user_name = st.session_state.user_db.get(st.session_state.logged_in_user, {}).get("name", "이상복")

menu_options = [
    "📊 수출입 B/L 등록",
    "📋 등록 B/L 수정 및 Profit 내역",
    "💰 매출 관리 (화주별 독립 트랙)",
    "🤝 매입 관리 (협력사별 독립 트랙)",
    "🚢 B/L 운송장 출력",
    "📑 거래처 인보이스 발행",
    "📄 화물 견적서 발행",
    "🤝 거래처 미팅 노트",
    "📋 금일발송 매니페스트",
    "🏢 매출 거래처(화주) 관리",
    "🚢 매입 거래처(선사/협력사) 관리",
    "💵 거래처 미수금관리",
    "💳 일계표 및 입출금 장부",
    "📝 업무용 일지",
]

if st.session_state.user_role == "관리자(대표)":
    menu_options.append("🔑 직원 계정 관리 (대표님 전용)")

selected_menu = st.sidebar.radio("📌 메인 메뉴 이동", menu_options)

header_html = """
<div style='background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); padding: 20px 24px; border-radius: 12px; color: white; margin-bottom: 20px;'>
    <h1 style='color: #ffffff; margin: 0; font-size: 21px; font-weight: 800;'>🚢 (주)범운해운항공 종합 관리 프로그램</h1>
    <p style='margin: 4px 0 0 0; color: #93c5fd; font-size: 12px;'>Job별 Profit 정산, 거래처별 요율 관리 및 스마트 인보이스 발행 시스템</p>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# [7] 금일발송 매니페스트 (사내용 / 거래처 공유용 탭 통합)
# ==========================================
if selected_menu == "📋 금일발송 매니페스트":
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 15px;'>📋 날짜별 발송 화물 매니페스트 및 입고 LIST</h3>",
        unsafe_allow_html=True,
    )

    tab_internal, tab_external = st.tabs(["🔒 사내 정산용 (매출/매입/Profit 포함)", "📤 거래처 공유용 입고 LIST (금액 제외)"])

    # -------------------------------------------------------------
    # 1️⃣ [탭 1] 사내 정산용
    # -------------------------------------------------------------
    with tab_internal:
        st.markdown("##### 🔒 사내 정산용 매니페스트 (매출, 매입, 마진 포함)")
        m_col_f1, m_col_f2 = st.columns(2)
        with m_col_f1:
            selected_manifest_date = st.date_input(
                "1️⃣ 조회할 선적 날짜 선택", value=date.today(), key="manifest_date_picker_internal"
            )
        
        target_date_str = str(selected_manifest_date)
        date_shipments = [
            item for item in st.session_state.bl_data_list
            if str(item.get("날짜", ""))[:10] == target_date_str
        ]

        if date_shipments:
            available_suppliers = sorted(list(set(str(r.get("매입처", "-")) for r in date_shipments if str(r.get("매입처", "-")).strip())))
            supplier_filter_options = ["전체 매입처 보기"] + available_suppliers
            
            with m_col_f2:
                selected_vendor_filter = st.selectbox(
                    "2️⃣ 매입처 선택", options=supplier_filter_options, key="manifest_vendor_select_internal"
                )

            filtered_shipments = date_shipments if selected_vendor_filter == "전체 매입처 보기" else [
                item for item in date_shipments if str(item.get("매입처", "-")).strip() == selected_vendor_filter
            ]

            if filtered_shipments:
                manifest_rows = []
                for r_m in filtered_shipments:
                    try:
                        sales_amt = int(float(str(r_m.get("매출액(원)", 0)).replace(",", "") or 0))
                    except:
                        sales_amt = 0
                    try:
                        purchase_amt = int(float(str(r_m.get("매입액(원)", 0)).replace(",", "") or 0))
                    except:
                        purchase_amt = 0
                    profit_amt = sales_amt - purchase_amt

                    manifest_rows.append({
                        "날짜": str(r_m.get("날짜", target_date_str))[:10],
                        "B/L 번호": str(r_m.get("B/L 번호", "-")),
                        "화주명(매출)": str(r_m.get("화주명(매출)", "-")),
                        "해외수하인": str(r_m.get("해외수하인", "-")),
                        "박스수": str(r_m.get("박스수", "1 박스")),
                        "부피규격": str(r_m.get("부피규격", "-")),
                        "매출청구중량(kg)": float(r_m.get('매출청구중량(kg)', 1.0)),
                        "매입처": str(r_m.get("매입처", "-")),
                        "매출액(원)": sales_amt,
                        "매입액(원)": purchase_amt,
                        "Profit(원)": profit_amt,
                    })

                manifest_display_df = pd.DataFrame(manifest_rows)
                display_view_df = manifest_display_df.copy()
                display_view_df["매출청구중량(kg)"] = display_view_df["매출청구중량(kg)"].apply(lambda x: f"{x:.1f} kg")
                display_view_df["매출액(원)"] = display_view_df["매출액(원)"].apply(lambda x: f"{x:,} 원")
                display_view_df["매입액(원)"] = display_view_df["매입액(원)"].apply(lambda x: f"{x:,} 원")
                display_view_df["Profit(원)"] = display_view_df["Profit(원)"].apply(lambda x: f"{x:,} 원")

                st.dataframe(display_view_df, use_container_width=True)

                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    manifest_display_df.to_excel(writer, index=False, sheet_name='사내매니페스트')
                excel_data = excel_buffer.getvalue()

                st.download_button(
                    label="📥 사내 정산용 매니페스트 엑셀 다운로드 (.xlsx)",
                    data=excel_data,
                    file_name=f"Bumwoon_Internal_Manifest_{target_date_str}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.warning("선택하신 매입처에 해당하는 선적 내역이 없습니다.")
        else:
            st.info("해당 날짜에 등록된 선적 내역이 없습니다.")

    # -------------------------------------------------------------
    # 2️⃣ [탭 2] 거래처 공유용 입고 LIST (수정 없이 바로 송부)
    # -------------------------------------------------------------
    with tab_external:
        st.markdown("##### 📦 거래처 제출용 입고 LIST (매출/매입 단가 및 Profit 제외)")
        m_col_e1, m_col_e2 = st.columns(2)
        with m_col_e1:
            selected_share_date = st.date_input(
                "1️⃣ 입고 날짜 선택", value=date.today(), key="manifest_date_picker_share"
            )
        
        share_date_str = str(selected_share_date)
        share_shipments = [
            item for item in st.session_state.bl_data_list
            if str(item.get("날짜", ""))[:10] == share_date_str
        ]

        if share_shipments:
            available_shippers = sorted(list(set(str(r.get("화주명(매출)", "-")) for r in share_shipments if str(r.get("화주명(매출)", "-")).strip())))
            shipper_filter_options = ["전체 거래처 보기"] + available_shippers
            
            with m_col_e2:
                selected_shipper_filter = st.selectbox(
                    "2️⃣ 거래처(화주) 선택", options=shipper_filter_options, key="manifest_shipper_select_share"
                )

            filtered_share_shipments = share_shipments if selected_shipper_filter == "전체 거래처 보기" else [
                item for item in share_shipments if str(item.get("화주명(매출)", "-")).strip() == selected_shipper_filter
            ]

            if filtered_share_shipments:
                st.markdown(f"#### 📦 [{share_date_str}] 입고 LIST (총 <span style='color: #2563eb;'>{len(filtered_share_shipments)}</span>건)", unsafe_allow_html=True)

                share_rows = []
                for idx, r_m in enumerate(filtered_share_shipments, 1):
                    try:
                        raw_gw = float(r_m.get("실중량(kg)", r_m.get("매출실중량(kg)", 1.0)) or 1.0)
                        gw_str = f"{raw_gw:.2f}"
                    except:
                        gw_str = "1.00"

                    share_rows.append({
                        "NO": idx,
                        "입고날짜": str(r_m.get("날짜", share_date_str))[:10],
                        "B/L 번호": str(r_m.get("B/L 번호", "-")),
                        "실중량(kg)": gw_str,
                        "부피규격(사이즈)": str(r_m.get("부피규격", "-")),
                        "수하인": str(r_m.get("해외수하인", "-")),
                        "수하인 전화번호": str(r_m.get("해외수하인전화번호", "-")),
                        "수하인 주소": str(r_m.get("해외수하인주소", "-")),
                    })

                share_display_df = pd.DataFrame(share_rows)

                st.markdown(
                    """
                    <style>
                    table { font-size: 14.5px !important; }
                    th { font-size: 15px !important; background-color: #1e3a8a !important; color: white !important; text-align: center !important; }
                    td { font-size: 14px !important; padding: 10px 8px !important; }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                
                st.dataframe(share_display_df, use_container_width=True, hide_index=True)

                excel_buffer_share = io.BytesIO()
                with pd.ExcelWriter(excel_buffer_share, engine='openpyxl') as writer:
                    share_display_df.to_excel(writer, index=False, sheet_name='입고LIST')
                excel_data_share = excel_buffer_share.getvalue()

                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    st.download_button(
                        label="📥 거래처 공유용 입고리스트 엑셀 다운로드 (.xlsx)",
                        data=excel_data_share,
                        file_name=f"입고LIST_{share_date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                manifest_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        @media print {{ body {{ -webkit-print-color-adjust: exact; }} .no-print {{ display: none !important; }} @page {{ size: A4 landscape; margin: 10mm; }} }}
                        body {{ font-family: 'Pretendard', sans-serif; color: #1e293b; font-size: 10pt; margin: 0; padding: 15px; background: #fff; }}
                        .box {{ max-width: 1150px; margin: 0 auto; border: 2px solid #0f172a; padding: 25px; border-radius: 8px; }}
                        .t-tbl {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                        .t-tbl th, .t-tbl td {{ border: 1px solid #475569; padding: 9px 10px; text-align: left; vertical-align: middle; font-size: 10pt; }}
                        .t-tbl th {{ background-color: #0f172a; color: white; text-align: center; font-weight: bold; }}
                        .p-btn {{ display: block; width: 100%; background-color: #2563eb; color: white; text-align: center; padding: 14px; font-size: 13pt; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; margin-bottom: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="box">
                        <button class="p-btn no-print" onclick="window.print()">🖨 입고리스트 인쇄 / PDF 저장</button>
                        <h2 style="text-align: center; color: #1e3a8a; margin-bottom: 5px; font-size: 20pt; font-weight: 900;">입 고 LIST</h2>
                        <p style="text-align: center; color: #475569; font-size: 11pt; margin-top: 0;">선적일자: <b>{share_date_str}</b> | (주)범운해운항공</p>
                        <table class="t-tbl">
                            <tr>
                                <th style="width: 5%;">NO</th>
                                <th style="width: 10%;">입고날짜</th>
                                <th style="width: 11%;">B/L 번호</th>
                                <th style="width: 9%;">실중량(kg)</th>
                                <th style="width: 16%;">부피규격(사이즈)</th>
                                <th style="width: 12%;">수하인</th>
                                <th style="width: 13%;">전화번호</th>
                                <th style="width: 24%;">수하인 주소</th>
                            </tr>
                """
                for idx, r_m in enumerate(filtered_share_shipments, 1):
                    try:
                        raw_gw = float(r_m.get("실중량(kg)", r_m.get("매출실중량(kg)", 1.0)) or 1.0)
                        gw_str = f"{raw_gw:.2f}"
                    except:
                        gw_str = "1.00"

                    manifest_html += f"""
                            <tr>
                                <td style="text-align: center; font-weight: bold;">{idx}</td>
                                <td style="text-align: center;">{str(r_m.get("날짜", share_date_str))[:10]}</td>
                                <td style="text-align: center; font-weight: bold;">{str(r_m.get("B/L 번호", "-"))}</td>
                                <td style="text-align: center;">{gw_str} kg</td>
                                <td style="text-align: center;">{str(r_m.get("부피규격", "-"))}</td>
                                <td style="font-weight: bold;">{str(r_m.get("해외수하인", "-"))}</td>
                                <td>{str(r_m.get("해외수하인전화번호", "-"))}</td>
                                <td>{str(r_m.get("해외수하인주소", "-"))}</td>
                            </tr>
                    """
                manifest_html += """
                        </table>
                        <div style="margin-top: 30px; text-align: right; font-weight: bold; font-size: 12pt;">
                            주식회사 범운해운항공 대표이사 이상복 [직인생략]
                        </div>
                    </div>
                </body>
                </html>
                """
                
                with d_col2:
                    if st.button("🖨 입고리스트 인쇄 / PDF 보고서", type="primary", use_container_width=True):
                        components.html(manifest_html, height=750, scrolling=True)
            else:
                st.warning("⚠️ 선택하신 조건에 해당하는 선적 내역이 없습니다.")
        else:
            st.info("해당 날짜에 등록된 선적 내역이 없습니다.")

# ==========================================
# 기타 메뉴 선택 시 안내 메시지
# ==========================================
elif selected_menu == "📊 수출입 B/L 등록":
    st.info("📊 B/L 등록 메뉴입니다.")
elif selected_menu == "📋 등록 B/L 수정 및 Profit 내역":
    st.info("📋 등록 B/L 수정 및 Profit 내역 메뉴입니다.")
else:
    st.info(f"📌 '{selected_menu}' 메뉴를 선택하셨습니다.")
