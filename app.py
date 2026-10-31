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
import os
import shutil
import openpyxl 

def simple_dual_backup():
    """복잡한 인증 없이 내 컴퓨터와 구글 드라이브 양쪽에 최신 백업 파일을 동시에 자동 저장하는 이중 백업 함수"""
    file_name = "범운해운항공_전체데이터_통합백업.xlsx"

    try:
        # 1. B/L 및 경비 데이터를 엑셀 파일로 생성
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            if st.session_state.get("bl_data_list"):
                pd.DataFrame(st.session_state.bl_data_list).to_excel(
                    writer, sheet_name="B_L데이터", index=False
                )
            if st.session_state.get("expense_list"):
                pd.DataFrame(st.session_state.expense_list).to_excel(
                    writer, sheet_name="지출내역", index=False
                )

        # 2. 내 컴퓨터의 구글 드라이브 동기화 폴더 탐색 및 복사
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

        if backup_copied:
            st.success(
                "🎉 [성공] 내 컴퓨터와 구글 드라이브(클라우드) 두 곳 모두에 최신 백업이 완료되었습니다!"
            )
        else:
            st.success(
                "💾 [성공] 내 컴퓨터 폴더에 백업 파일이 안전하게 저장되었습니다!"
            )

    except Exception as e:
        st.error(f"백업 저장 중 오류 발생: {e}")
# ==========================================
# 🔄 깃허브 백업 엑셀 파일 자동 복원 로직 (개선판)
# ==========================================
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
        # BL_Data 시트가 있으면 읽고, 없으면 엑셀의 첫 번째 시트를 자동으로 읽음
        target_sheet = "BL_Data" if "BL_Data" in excel_data.sheet_names else excel_data.sheet_names[0]
        df_bl = pd.read_excel(excel_data, sheet_name=target_sheet)
        st.session_state.bl_data_list = df_bl.to_dict(orient="records")
        
        if "Expense_Data" in excel_data.sheet_names:
            df_exp = pd.read_excel(excel_data, sheet_name="Expense_Data")
            st.session_state.expense_list = df_exp.to_dict(orient="records")
            
        st.session_state["auto_backup_loaded"] = True
        st.sidebar.success(f"📁 자동 복원 완료: {latest_backup}")
    except Exception as e:
        st.session_state["auto_backup_loaded"] = True

auto_load_latest_backup()
# ==========================================
# [보안 및 계정 파일 저장소 시스템]
# ==========================================
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
  return {
      "lsb": {"pw": "7071", "role": "관리자(대표)", "name": "이상복"}
  }


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
  """로그인 화면 출력 함수"""
  st.markdown("<br><br>", unsafe_allow_html=True)
  col1, col2, col3 = st.columns([1, 1.2, 1])

  with col2:
    st.markdown(
        "<h2 style='text-align: center; color: #1e3a8a;'>🚢 범운해운항공 물류"
        " 시스템 (사내 관리자)</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #64748b; font-size:"
        " 9.5pt;'>관계자 외 접속이 제한된 보안 구역입니다.</p><br>",
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
      input_id = st.text_input("아이디 (ID)")
      input_pw = st.text_input("비밀번호 (Password)", type="password")
      submit_login = st.form_submit_button("로그인", use_container_width=True)

      if submit_login:
        if (
            input_id in st.session_state.user_db
            and st.session_state.user_db[input_id]["pw"] == input_pw
        ):
          st.session_state.logged_in_user = input_id
          st.session_state.user_role = st.session_state.user_db[input_id][
              "role"
          ]
          st.success(
              f"환영합니다, {st.session_state.user_db[input_id]['name']}님!"
          )
          st.rerun()
        else:
          st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    if st.button("⬅ 고객 화물 추적 홈으로 돌아가기", use_container_width=True):
      st.query_params.clear()
      st.rerun()


# ==========================================
# 데이터 파일 경로 및 로고 공통 정의
# ==========================================
DATA_FILE = "bl_history_data.csv"
CLIENT_FILE = "client_data.csv"
SUPPLIER_FILE = "supplier_data.csv"
ACCOUNT_FILE = "account_ledger_data.csv"
EXPENSE_FILE = "expense_data.csv"
NOTE_FILE = "daily_note_data.csv"
MEETING_FILE = "meeting_note_data.csv"
QUOTATION_FILE = "quotation_data.csv"

# GitHub 저장소에 있는 범운 회사 로고를 우선 사용합니다.
# 파일명이 정확히 lo.png이면 다른 파일보다 먼저 선택합니다.
LOGO_FILE = None
_logo_candidates = [
  "lo.png", "logo.png", "LO.png", "Logo.png",
  "lo.jpg", "logo.jpg", "lo.jpeg", "logo.jpeg",
  "lo.webp", "logo.webp",
]
for _candidate in _logo_candidates:
  if os.path.isfile(_candidate):
    LOGO_FILE = _candidate
    break

# 파일명이 다를 경우에만 lo로 시작하는 이미지 파일을 보조 탐색합니다.
if LOGO_FILE is None:
  for _filename in os.listdir("."):
    _lower = _filename.lower()
    if _lower.startswith("lo") and os.path.splitext(_lower)[1] in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
      LOGO_FILE = _filename
      break

encoded_sidebar_logo = ""
label_logo_data_uri = ""
if LOGO_FILE and os.path.exists(LOGO_FILE):
  try:
    with open(LOGO_FILE, "rb") as f:
      logo_bytes = f.read()
    encoded_sidebar_logo = base64.b64encode(logo_bytes).decode()
    logo_ext = os.path.splitext(LOGO_FILE)[1].lower()
    logo_mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}.get(logo_ext, "image/png")
    label_logo_data_uri = f"data:{logo_mime};base64,{encoded_sidebar_logo}"
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
      if "최종작성자" not in df.columns:
        df["최종작성자"] = "이상복"
      if "최종수정자" not in df.columns:
        df["최종수정자"] = "-"
      return df.to_dict("records")
    except Exception:
      return []
  return []


def save_bl_data(data_list):
  if data_list:
    df = pd.DataFrame(data_list)
    if "예상마진(원)" in df.columns and "예상Profit(원)" not in df.columns:
      df = df.rename(columns={"예상마진(원)": "예상Profit(원)"})
    if "수금상태" not in df.columns:
      df["수금상태"] = "미수"
    if "최종작성자" not in df.columns:
      df["최종작성자"] = "이상복"
    if "최종수정자" not in df.columns:
      df["최종수정자"] = "-"
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
  else:
    if os.path.exists(DATA_FILE):
      os.remove(DATA_FILE)


def load_meeting_data():
  if os.path.exists(MEETING_FILE):
    try:
      return pd.read_csv(MEETING_FILE).to_dict("records")
    except:
      return []
  return []


def save_meeting_data(data_list):
  if data_list:
    pd.DataFrame(data_list).to_csv(
        MEETING_FILE, index=False, encoding="utf-8-sig"
    )
  else:
    if os.path.exists(MEETING_FILE):
      os.remove(MEETING_FILE)


def load_expense_data():
  if os.path.exists(EXPENSE_FILE):
    try:
      return pd.read_csv(EXPENSE_FILE).to_dict("records")
    except:
      return []
  return []


def save_expense_data(data_list):
  if data_list:
    pd.DataFrame(data_list).to_csv(
        EXPENSE_FILE, index=False, encoding="utf-8-sig"
    )
  else:
    if os.path.exists(EXPENSE_FILE):
      os.remove(EXPENSE_FILE)


def load_account_data():
  """일계표 전용 CSV 장부 데이터를 불러옵니다."""
  if os.path.exists(ACCOUNT_FILE):
    try:
      return pd.read_csv(ACCOUNT_FILE).fillna("").to_dict("records")
    except Exception as e:
      print(f"일계표 데이터 읽기 오류: {e}")
  return []


def save_account_data(data_list):
  """일계표 장부를 ACCOUNT_FILE에 저장합니다."""
  if data_list:
    pd.DataFrame(data_list).to_csv(ACCOUNT_FILE, index=False, encoding="utf-8-sig")
  elif os.path.exists(ACCOUNT_FILE):
    os.remove(ACCOUNT_FILE)


def load_note_data():
  if os.path.exists(NOTE_FILE):
    try:
      return pd.read_csv(NOTE_FILE).to_dict("records")
    except:
      return []
  return []


def save_note_data(data_list):
  if data_list:
    pd.DataFrame(data_list).to_csv(NOTE_FILE, index=False, encoding="utf-8-sig")
  else:
    if os.path.exists(NOTE_FILE):
      os.remove(NOTE_FILE)


# ==========================================
# [매출 거래처(화주)] 데이터 관리
# ==========================================
def _client_safe_number(value, default, as_int=False):
  """거래처 요율의 빈칸/NaN/문자값 때문에 전체 거래처 로딩이 중단되지 않도록 숫자를 안전 변환합니다."""
  try:
    if value is None or pd.isna(value) or str(value).strip() == "":
      return int(default) if as_int else float(default)
    cleaned = str(value).replace(",", "").strip()
    number = float(cleaned)
    if not math.isfinite(number):
      return int(default) if as_int else float(default)
    return int(number) if as_int else number
  except (TypeError, ValueError, OverflowError):
    return int(default) if as_int else float(default)


def _client_text(value, default=""):
  """CSV/엑셀의 NaN을 문자열 'nan'으로 저장하지 않습니다."""
  try:
    if value is None or pd.isna(value):
      return default
  except (TypeError, ValueError):
    pass
  value = str(value).strip()
  return default if value.lower() in ("nan", "none", "null") else value


def load_client_data():
  """
  매출 거래처 CSV를 거래처 단위로 최대한 복원합니다.
  한 행의 숫자 오류나 빈 요율이 있어도 다른 거래처까지 기본 2곳으로 축소하지 않습니다.
  """
  if os.path.exists(CLIENT_FILE):
    try:
      df = pd.read_csv(CLIENT_FILE, dtype={"거래처명": str}, keep_default_na=False)
      if "거래처명" in df.columns and not df.empty:
        clients = []
        rates = {}
        client_infos = {}

        for _, row in df.iterrows():
          client = _client_text(row.get("거래처명", ""))
          if not client:
            continue

          if client not in clients:
            clients.append(client)
            rates[client] = {}
            client_infos[client] = {
                "사업자등록번호": _client_text(row.get("사업자등록번호", "")),
                "이메일": _client_text(row.get("이메일", "")),
                "담당자": _client_text(row.get("담당자", "")),
                "전화번호": _client_text(row.get("전화번호", "")),
                "주소": _client_text(row.get("주소", "")),
            }

          country = _client_text(row.get("국가", "미국"), "미국")
          transport = _client_text(row.get("운송형태", "항공(Air)"), "항공(Air)")
          item = _client_text(row.get("품명", "일반공산품"), "일반공산품")

          rates[client].setdefault(country, {}).setdefault(transport, {})[item] = {
              "기본중량": _client_safe_number(row.get("기본중량", 1.0), 1.0),
              "기본요금": _client_safe_number(row.get("기본요금", 38000), 38000, as_int=True),
              "추가단가": _client_safe_number(row.get("추가단가", 25000), 25000, as_int=True),
              "1CBM당단가": _client_safe_number(row.get("1CBM당단가", 3700000), 3700000, as_int=True),
          }

        if clients:
          return clients, rates, client_infos
    except Exception as e:
      # CSV 자체를 읽을 수 없는 경우에만 기본 거래처로 넘어갑니다.
      # 개별 요율 숫자 변환 오류는 위에서 행 단위로 처리합니다.
      st.warning(f"거래처 CSV 읽기 중 문제가 있어 기본 데이터 확인이 필요합니다: {e}")

  default_clients = ["아코글로벌", "주식회사 조은로직스"]
  default_rates = {
      "아코글로벌": {
          "미국": {
              "항공(Air)": {
                  "보톡스 필러": {
                      "기본중량": 1.0,
                      "기본요금": 38000,
                      "추가단가": 25000,
                      "1CBM당단가": 3700000,
                  }
              }
          }
      },
      "주식회사 조은로직스": {
          "미국": {
              "항공(Air)": {
                  "일반화물": {
                      "기본중량": 1.0,
                      "기본요금": 38000,
                      "추가단가": 25000,
                      "1CBM당단가": 3700000,
                  }
              }
          }
      },
  }
  default_infos = {
      "아코글로벌": {
          "사업자등록번호": "778-09-03229",
          "이메일": "infoakoglobal@gmail.com",
          "담당자": "박장우대표님",
          "전화번호": "",
          "주소": "경기도 김포시 풍무동 326-5번지 2층",
      },
      "주식회사 조은로직스": {
          "사업자등록번호": "",
          "이메일": "",
          "담당자": "조정희 과장",
          "전화번호": "",
          "주소": "",
      },
  }
  return default_clients, default_rates, default_infos


def save_client_data(client_list, client_rates, client_infos):
  """거래처 목록 전체를 보존하고 요율이 비어 있어도 거래처 자체는 CSV에 남깁니다."""
  rows = []
  seen_clients = set()

  for raw_client in (client_list or []):
    client = _client_text(raw_client)
    if not client or client in seen_clients:
      continue
    seen_clients.add(client)

    info = client_infos.get(client, {}) if isinstance(client_infos, dict) else {}
    info = info if isinstance(info, dict) else {}
    country_dict = client_rates.get(client, {}) if isinstance(client_rates, dict) else {}
    client_base = {
        "거래처명": client,
        "사업자등록번호": _client_text(info.get("사업자등록번호", "")),
        "이메일": _client_text(info.get("이메일", "")),
        "담당자": _client_text(info.get("담당자", "")),
        "전화번호": _client_text(info.get("전화번호", "")),
        "주소": _client_text(info.get("주소", "")),
    }

    rate_rows_added = False
    if isinstance(country_dict, dict):
      for country, trans_dict in country_dict.items():
        if not isinstance(trans_dict, dict):
          continue
        for transport, item_dict in trans_dict.items():
          if not isinstance(item_dict, dict):
            continue
          for item_name, r_val in item_dict.items():
            r_val = r_val if isinstance(r_val, dict) else {}
            rows.append({
                **client_base,
                "국가": _client_text(country, "미국"),
                "운송형태": _client_text(transport, "항공(Air)"),
                "품명": _client_text(item_name, "일반공산품"),
                "기본중량": _client_safe_number(r_val.get("기본중량", 1.0), 1.0),
                "기본요금": _client_safe_number(r_val.get("기본요금", 38000), 38000, as_int=True),
                "추가단가": _client_safe_number(r_val.get("추가단가", 25000), 25000, as_int=True),
                "1CBM당단가": _client_safe_number(r_val.get("1CBM당단가", 3700000), 3700000, as_int=True),
            })
            rate_rows_added = True

    if not rate_rows_added:
      # 요율이 없는 거래처도 거래처 목록에서 사라지지 않도록 기본 빈 요율 행으로 보존
      rows.append({
          **client_base,
          "국가": "미국",
          "운송형태": "항공(Air)",
          "품명": "일반화물",
          "기본중량": 1.0,
          "기본요금": 38000,
          "추가단가": 25000,
          "1CBM당단가": 3700000,
      })

  pd.DataFrame(rows, columns=[
      "거래처명", "사업자등록번호", "이메일", "담당자", "전화번호", "주소",
      "국가", "운송형태", "품명", "기본중량", "기본요금", "추가단가", "1CBM당단가"
  ]).to_csv(CLIENT_FILE, index=False, encoding="utf-8-sig")


# ==========================================
# [매입 거래처(선사/항공사/협력사)] 데이터 관리
# ==========================================
def load_supplier_data():
  if os.path.exists(SUPPLIER_FILE):
    try:
      df = pd.read_csv(SUPPLIER_FILE)
      suppliers = df["거래처명"].unique().tolist()
      rates = {}
      supplier_infos = {}
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
        for _, row in sub_df.iterrows():
          country = row.get("국가", "미국")
          transport = str(row.get("운송형태", "항공(Air)")).strip()
          item = str(row.get("품명", "일반공산품")).strip()
          if country not in rates[supplier]:
            rates[supplier][country] = {}
          if transport not in rates[supplier][country]:
            rates[supplier][country][transport] = {}
          rates[supplier][country][transport][item] = {
              "기본중량": _client_safe_number(row.get("기본중량", 1.0), 1.0),
              "기본요금": _client_safe_number(row.get("기본요금", 35000), 35000, as_int=True),
              "추가단가": _client_safe_number(row.get("추가단가", 22000), 22000, as_int=True),
              "1CBM당단가": _client_safe_number(row.get("1CBM당단가", 3500000), 3500000, as_int=True),
          }
      if suppliers:
        return suppliers, rates, supplier_infos
    except Exception:
      pass

  default_suppliers = ["(주)카스익스프레스", "ESI"]
  default_rates = {
      "(주)카스익스프레스": {
          "미국": {
              "항공(Air)": {
                  "보톡스 필러": {
                      "기본중량": 1.0,
                      "기본요금": 35000,
                      "추가단가": 22000,
                      "1CBM당단가": 3500000,
                  }
              }
          }
      },
      "ESI": {
          "미국": {
              "항공(Air)": {
                  "일반화물": {
                      "기본중량": 1.0,
                      "기본요금": 35000,
                      "추가단가": 22000,
                      "1CBM당단가": 3500000,
                  }
              }
          }
      },
  }
  default_infos = {
      "(주)카스익스프레스": {
          "사업자등록번호": "",
          "이메일": "",
          "담당자": "",
          "전화번호": "",
          "주소": "",
      },
      "ESI": {
          "사업자등록번호": "",
          "이메일": "",
          "담당자": "정재국대표님",
          "전화번호": "",
          "주소": "",
      },
  }
  return default_suppliers, default_rates, default_infos


def save_supplier_data(supplier_list, supplier_rates, supplier_infos):
  rows = []
  for supplier in supplier_list:
    info = supplier_infos.get(
        supplier,
        {
            "사업자등록번호": "",
            "이메일": "",
            "담당자": "",
            "전화번호": "",
            "주소": "",
        },
    )
    country_dict = supplier_rates.get(supplier, {})
    if not country_dict:
      rows.append({
          "거래처명": supplier,
          "사업자등록번호": info.get("사업자등록번호", ""),
          "이메일": info.get("이메일", ""),
          "담당자": info.get("담당자", ""),
          "전화번호": info.get("전화번호", ""),
          "주소": info.get("주소", ""),
          "국가": "미국",
          "운송형태": "항공(Air)",
          "품명": "일반화물",
          "기본중량": 1.0,
          "기본요금": 35000,
          "추가단가": 22000,
          "1CBM당단가": 3500000,
      })
    else:
      for country, trans_dict in country_dict.items():
        if isinstance(trans_dict, dict):
          for transport, item_dict in trans_dict.items():
            if isinstance(item_dict, dict):
              for item_name, r_val in item_dict.items():
                rows.append({
                    "거래처명": supplier,
                    "사업자등록번호": info.get("사업자등록번호", ""),
                    "이메일": info.get("이메일", ""),
                    "담당자": info.get("담당자", ""),
                    "전화번호": info.get("전화번호", ""),
                    "주소": info.get("주소", ""),
                    "국가": country,
                    "운송형태": transport,
                    "품명": item_name,
                    "기본중량": r_val.get("기본중량", 1.0),
                    "기본요금": r_val.get("기본요금", 35000),
                    "추가단가": r_val.get("추가단가", 22000),
                    "1CBM당단가": r_val.get("1CBM당단가", 3500000),
                })
  pd.DataFrame(rows).to_csv(SUPPLIER_FILE, index=False, encoding="utf-8-sig")


def _select_rate(rates_by_country, country, transport_mode, item_name):
  """Select only an exact country/transport/item rate, or an unambiguous sole option."""
  if not isinstance(rates_by_country, dict) or not rates_by_country:
    return None

  country_key = str(country or "").strip()
  if country_key in rates_by_country:
    country_rates = rates_by_country[country_key]
  elif len(rates_by_country) == 1:
    country_rates = next(iter(rates_by_country.values()))
  else:
    return None

  if not isinstance(country_rates, dict) or not country_rates:
    return None
  if transport_mode in country_rates:
    transport_rates = country_rates[transport_mode]
  elif len(country_rates) == 1:
    transport_rates = next(iter(country_rates.values()))
  else:
    return None

  if not isinstance(transport_rates, dict) or not transport_rates:
    return None
  item_key = str(item_name or "").strip()
  if item_key in transport_rates:
    rate = transport_rates[item_key]
  elif len(transport_rates) == 1:
    rate = next(iter(transport_rates.values()))
  else:
    return None
  return rate if isinstance(rate, dict) else None


def _calculate_weight_rate(rate, cw, default_base, default_add):
  try:
    chargeable_weight = max(0.0, float(cw))
    base_weight = max(0.0, float(rate.get("기본중량", 1.0)))
    base_price = max(0, int(float(rate.get("기본요금", default_base))))
    add_price = max(0, int(float(rate.get("추가단가", default_add))))
  except (TypeError, ValueError, OverflowError):
    return None
  if chargeable_weight <= base_weight:
    return base_price
  return int(base_price + math.ceil(chargeable_weight - base_weight) * add_price)


def calculate_auto_price(
    client_name, cw, transport_mode="항공(Air)", item_name="일반화물", country=None
):
  rates_dict = st.session_state.get("client_rates", {}).get(client_name, {})
  rate = _select_rate(rates_dict, country, transport_mode, item_name)
  price = _calculate_weight_rate(rate, cw, 38000, 25000) if rate else None
  if price is not None:
    return price
  return int(38000 + math.ceil(max(0.0, float(cw) - 1.0)) * 25000)


def calculate_purchase_auto_price(
    supplier_name, cw, transport_mode="항공(Air)", item_name="일반화물", country=None
):
  rates_dict = st.session_state.get("supplier_rates", {}).get(supplier_name, {})
  rate = _select_rate(rates_dict, country, transport_mode, item_name)
  price = _calculate_weight_rate(rate, cw, 35000, 22000) if rate else None
  if price is not None:
    return price
  return int(35000 + math.ceil(max(0.0, float(cw) - 1.0)) * 22000)

def generate_barcode_html(text):
    """표준 Code 128 바코드와 QR 코드를 함께 생성합니다."""
    clean_txt = str(text or "").strip()
    if not clean_txt:
        return '<div style="color:#b91c1c;font-size:9pt;">B/L 번호가 없어 바코드를 생성할 수 없습니다.</div>'

    # 사용자 입력값을 HTML에 안전하게 표시
    from html import escape
    safe_txt = escape(clean_txt)

    code128_html = ""
    qr_html = ""

    try:
        from reportlab.graphics.barcode import createBarcodeDrawing
        from reportlab.graphics import renderSVG

        drawing = createBarcodeDrawing(
            "Code128",
            value=clean_txt,
            barHeight=38,
            barWidth=0.65,
            humanReadable=False,
            quiet=True,
        )
        svg = renderSVG.drawToString(drawing)
        code128_html = (
            '<div style="display:flex;flex-direction:column;align-items:center;'
            'justify-content:center;min-width:0;flex:1;">'
            f'{svg}'
            f'<div style="font-size:8pt;font-weight:800;letter-spacing:1px;'
            f'color:#111827;margin-top:3px;white-space:nowrap;">{safe_txt}</div>'
            '<div style="font-size:6.5pt;color:#475569;">CODE 128 · 스캐너용</div>'
            '</div>'
        )
    except Exception:
        code128_html = (
            '<div style="color:#b91c1c;font-size:8pt;">'
            'Code 128 생성 실패: reportlab 패키지 설치를 확인하세요.</div>'
        )

    try:
        import qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=5,
            border=3,
        )
        qr.add_data(clean_txt)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        qr_image.save(qr_buffer, format="PNG")
        qr_b64 = base64.b64encode(qr_buffer.getvalue()).decode("ascii")
        qr_html = (
            '<div style="display:flex;flex-direction:column;align-items:center;'
            'justify-content:center;flex:0 0 82px;">'
            f'<img src="data:image/png;base64,{qr_b64}" alt="B/L QR code" '
            'style="width:76px;height:76px;object-fit:contain;background:#fff;">'
            '<div style="font-size:6.5pt;color:#475569;">QR · 스마트폰용</div>'
            '</div>'
        )
    except Exception:
        qr_html = (
            '<div style="font-size:7pt;color:#b91c1c;text-align:center;">'
            'QR 생성 실패: qrcode 패키지 설치를 확인하세요.</div>'
        )

    return (
        '<div style="display:flex;align-items:center;justify-content:flex-end;'
        'gap:10px;background:#fff;padding:5px;max-width:100%;overflow:hidden;">'
        f'{code128_html}{qr_html}</div>'
    )


# ==========================================
# 세션 상태 필수 데이터 초기화
# ==========================================
if "client_list" not in st.session_state or not st.session_state.client_list:
  c_list, c_rates, c_infos = load_client_data()
  st.session_state.client_list = c_list
  st.session_state.client_rates = c_rates
  st.session_state.client_infos = c_infos

if (
    "supplier_list" not in st.session_state
    or not st.session_state.supplier_list
):
  s_list, s_rates, s_infos = load_supplier_data()
  st.session_state.supplier_list = s_list
  st.session_state.supplier_rates = s_rates
  st.session_state.supplier_infos = s_infos

if "bl_data_list" not in st.session_state:
  st.session_state.bl_data_list = load_bl_data()
if "meeting_data_list" not in st.session_state:
  st.session_state.meeting_data_list = load_meeting_data()
if "expense_data_list" not in st.session_state:
  st.session_state.expense_data_list = load_expense_data()
if "cashbook_list" not in st.session_state:
  st.session_state.cashbook_list = load_account_data()
if "note_data_list" not in st.session_state:
  st.session_state.note_data_list = load_note_data()

TRACKING_STATUS_OPTIONS = [
    "📦 물류센터 입고 및 접수 완료",
    "🔄 수출입 통관 진행 중",
    "✈ 항공/해상 선적 완료 (운송 중)",
    "📍 현지 공항/항만 도착",
    "🚚 현지 배송 진행 중 (Out for Delivery)",
    "✅ 배송 완료 (Delivered)",
    "⚠ 운송 지연 또는 보류",
]

# ==========================================
# 고객사 전용 화물 접수 / 수정 시스템
# ==========================================
CUSTOMER_ACCOUNT_FILE = "customer_accounts.csv"
CUSTOMER_REQUEST_FILE = "customer_freight_requests.csv"
CUSTOMER_HISTORY_FILE = "customer_freight_edit_history.csv"


def _read_customer_csv(path):
    if not os.path.exists(path):
        return []
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False).to_dict("records")
    except Exception:
        return []


def _write_customer_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def _customer_accounts():
    return _read_customer_csv(CUSTOMER_ACCOUNT_FILE)


def _customer_requests():
    return _read_customer_csv(CUSTOMER_REQUEST_FILE)


def _customer_history_append(record):
    rows = _read_customer_csv(CUSTOMER_HISTORY_FILE)
    rows.append(record)
    _write_customer_csv(CUSTOMER_HISTORY_FILE, rows)


def _customer_hash_password(password):
    import hashlib
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()

# 기존 화면 코드에서 사용하던 함수명과의 호환 별칭
customer_hash_password = _customer_hash_password
write_customer_csv = _write_customer_csv
customer_history_append = _customer_history_append


def _customer_is_active(account):
    return str(account.get("상태", "승인")).strip() == "승인"


def _customer_request_is_billed(item):
    return bool(str(item.get("연결 B/L 번호", "")).strip()) or str(item.get("상태", "접수")).startswith("B/L 등록")

# 이전 배포 코드에서 사용한 함수명과의 호환 별칭 (NameError 방지)
customer_request_is_billed = _customer_request_is_billed


# 고객 화물 접수 화면에서 사용할 도착 국가 목록 (요청된 8개 국가만 표시)
CUSTOMER_DEST_COUNTRIES = [
    "미국", "중국", "인도", "호주", "인도네시아", "태국", "베트남"
]
CUSTOMER_ITEM_OPTIONS = ["보톡스", "필러", "화장품", "특가품목", "일반화물", "의류", "전자제품", "식품", "기타"]


def _customer_portal():
    st.markdown("<div style='text-align:center;padding:14px 4px;'>", unsafe_allow_html=True)
    st.markdown("## 📦 고객사 화물 접수 / 내역 수정")
    st.caption("고객사별 아이디로 로그인하면 해당 회사의 접수 내역만 확인할 수 있습니다.")
    st.markdown("</div>", unsafe_allow_html=True)
    accounts = _customer_accounts()
    if not st.session_state.get("customer_logged_in"):
        login_tab, help_tab = st.tabs(["🔐 고객사 로그인", "ℹ️ 계정 안내"])
        with login_tab:
            with st.form("customer_login_form"):
                cid = st.text_input("고객사 아이디")
                cpw = st.text_input("비밀번호", type="password")
                login = st.form_submit_button("로그인", use_container_width=True, type="primary")
            if login:
                found = next((a for a in accounts if a.get("아이디", "").strip() == cid.strip()), None)
                if found and _customer_is_active(found) and found.get("비밀번호해시", "") == _customer_hash_password(cpw):
                    st.session_state.customer_logged_in = True
                    st.session_state.customer_account_id = found.get("아이디", "")
                    st.session_state.customer_company = found.get("고객사상호", "")
                    st.rerun()
                elif found and not _customer_is_active(found):
                    st.error("아직 관리자 승인이 완료되지 않은 계정입니다. 범운해운항공에 문의해 주세요.")
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
        with help_tab:
            st.info("고객사 계정은 범운해운항공 사내 관리자가 발급합니다. 아이디·비밀번호 발급을 요청해 주세요.")
        if st.button("⬅ 화물 추적 홈으로 돌아가기", use_container_width=True):
            st.query_params.clear()
            st.rerun()
        return

    cid = st.session_state.get("customer_account_id", "")
    account = next((a for a in accounts if a.get("아이디", "") == cid and _customer_is_active(a)), None)
    if not account:
        st.session_state.customer_logged_in = False
        st.session_state.customer_account_id = ""
        st.session_state.customer_company = ""
        st.error("계정이 비활성화되었습니다. 다시 로그인해 주세요.")
        st.rerun()
    company = account.get("고객사상호", "")
    head_l, head_r = st.columns([4, 1])
    head_l.success(f"로그인: {company}")
    if head_r.button("로그아웃", use_container_width=True):
        st.session_state.customer_logged_in = False
        st.session_state.customer_account_id = ""
        st.session_state.customer_company = ""
        st.rerun()

    # 함수명 통일: 정의된 _customer_requests()를 호출해 NameError 방지
    all_requests = _customer_requests()
    mine = [r for r in all_requests if r.get("고객사아이디", "") == cid]
    tab_new, tab_list = st.tabs(["➕ 새 화물 접수", "📋 내 접수 내역 / 수정"])
    with tab_new:
        st.markdown("#### 화물 접수 정보")
        # 박스별 규격은 체크했을 때만 표시되도록 폼 바깥에 배치
        use_box_details = st.checkbox(
            "➕ 박스별 부피 입력 추가 (박스 크기가 서로 다를 때 선택)",
            value=False,
            key="customer_new_use_box_details",
            help="선택하지 않으면 한 가지 규격을 전체 박스에 적용합니다."
        )
        cartons = st.number_input("박스 수량 (CTN)", min_value=1, max_value=100, value=1, step=1, key="customer_new_cartons")
        box_dims = []
        c_ship = st.columns(3)
        with c_ship[0]: shipper = st.text_input("화주 상호 *", value=company)
        with c_ship[1]: shipper_address = st.text_input("화주 주소 *")
        with c_ship[2]: shipper_phone = st.text_input("화주 전화번호 *")
        c_cons = st.columns(3)
        with c_cons[0]: consignee = st.text_input("해외 수하인 상호 *")
        with c_cons[1]: consignee_address = st.text_input("해외 수하인 주소 *")
        with c_cons[2]: consignee_phone = st.text_input("해외 수하인 전화번호")
        dest_country = st.selectbox("도착 국가 선택 *", options=CUSTOMER_DEST_COUNTRIES, index=0, key="customer_new_dest_country", help="미국·중국·인도·호주·인도네시아·태국·베트남 중 선택하세요.")
        item_name = st.selectbox("품목 / 화물 내용 *", CUSTOMER_ITEM_OPTIONS, index=4, key="customer_new_item_name")
        transport = st.selectbox("운송 형태", ["항공(Air)", "해상(LCL)"])
        weight = st.number_input("실제 총중량 (kg) *", min_value=0.0, value=1.0, step=0.5, format="%.2f")
        if use_box_details:
            st.caption("각 박스의 크기를 입력하세요. 51.5cm 같은 소수점 치수도 유지됩니다.")
            for bi in range(int(cartons)):
                st.markdown(f"박스 {bi+1} / {int(cartons)}")
                d1, d2, d3 = st.columns(3)
                with d1: bw = st.number_input(f"가로 (cm) · 박스 {bi+1}", min_value=0.0, value=1.0, step=0.1, format="%.1f", key=f"customer_box_w{bi}")
                with d2: bl = st.number_input(f"세로 (cm) · 박스 {bi+1}", min_value=0.0, value=1.0, step=0.1, format="%.1f", key=f"customer_box_l{bi}")
                with d3: bh = st.number_input(f"높이 (cm) · 박스 {bi+1}", min_value=0.0, value=1.0, step=0.1, format="%.1f", key=f"customer_box_h{bi}")
                box_dims.append({"박스순번": bi+1, "가로cm": float(bw), "세로cm": float(bl), "높이cm": float(bh), "실제중량kg": "", "바코드": "", "입고상태": "미입고"})
            dims_valid = all(d["가로cm"] > 0 and d["세로cm"] > 0 and d["높이cm"] > 0 for d in box_dims)
            total_cbm_preview = sum(d["가로cm"] * d["세로cm"] * d["높이cm"] / 1_000_000 for d in box_dims)
            divisor_preview = 5000 if transport == "항공(Air)" else 6000
            volume_preview = sum(d["가로cm"] * d["세로cm"] * d["높이cm"] / divisor_preview for d in box_dims)
        else:
            d1, d2, d3 = st.columns(3)
            with d1: width = st.number_input("가로 (cm) ", min_value=0.0, value=1.0, step=0.1, format="%.1f")
            with d2: length = st.number_input("세로 (cm) ", min_value=0.0, value=1.0, step=0.1, format="%.1f")
            with d3: height = st.number_input("높이 (cm) ", min_value=0.0, value=1.0, step=0.1, format="%.1f")
            box_dims = [{"박스순번": bi+1, "가로cm": float(width), "세로cm": float(length), "높이cm": float(height), "실제중량kg": "", "바코드": "", "입고상태": "미입고"} for bi in range(int(cartons))]
            dims_valid = width > 0 and length > 0 and height > 0
            total_cbm_preview = float(width) * float(length) * float(height) * int(cartons) / 1_000_000
            divisor_preview = 5000 if transport == "항공(Air)" else 6000
            volume_preview = float(width) * float(length) * float(height) * int(cartons) / divisor_preview
        charge_preview = max(float(weight), float(volume_preview))
        p1, p2, p3 = st.columns(3)
        p1.metric("총 CBM", f"{total_cbm_preview:.4f}")
        p2.metric(f"부피중량 (÷{divisor_preview})", f"{volume_preview:.2f} kg")
        p3.metric("적용중량", f"{charge_preview:.2f} kg")
        export_license_no = st.text_input("수출면장 번호 (해당 시 입력)", key="customer_new_export_license")
        note = st.text_input("추가 요청 사항 (선택)")
        submitted = st.button("🖨️ QR & 바코드 발급·인쇄", use_container_width=True, type="primary")
        if submitted:
            required = [shipper, shipper_address, shipper_phone, consignee, consignee_address, dest_country, item_name]
            if not all(str(v).strip() for v in required):
                st.error("표시된 필수 항목을 모두 입력해 주세요.")
            elif weight <= 0 or int(cartons) <= 0 or not dims_valid:
                st.error("실제 중량과 각 박스의 가로·세로·높이는 0보다 커야 합니다.")
            else:
                import uuid
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                req_id = "REQ-" + uuid.uuid4().hex[:10].upper()
                # 바코드는 박스마다 고유하고 접수번호와 연결
                for bd in box_dims:
                    bd["바코드"] = f"BW{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
                cbm = sum(d["가로cm"]*d["세로cm"]*d["높이cm"]/1_000_000 for d in box_dims)
                vol_weight = sum(d["가로cm"]*d["세로cm"]*d["높이cm"]/(5000 if transport == "항공(Air)" else 6000) for d in box_dims)
                # 기존 B/L 연결 코드와의 호환을 위해 대표 치수는 첫 박스 기준으로 유지
                first_box = box_dims[0]
                new_req = {
                    "접수번호": req_id, "접수일시": now, "고객사아이디": cid, "고객사상호": company,
                    "화주상호": shipper.strip(), "화주주소": shipper_address.strip(), "화주전화번호": shipper_phone.strip(),
                    "해외수하인": consignee.strip(), "해외수하인주소": consignee_address.strip(), "해외수하인전화번호": consignee_phone.strip(),
                    "도착국가": dest_country.strip(), "품목": item_name.strip(), "운송형태": transport,
                    "실제중량kg": f"{weight:.2f}", "가로cm": f"{first_box['가로cm']:.2f}", "세로cm": f"{first_box['세로cm']:.2f}", "높이cm": f"{first_box['높이cm']:.2f}",
                    "박스수량": str(int(cartons)), "CBM": f"{cbm:.4f}", "부피중량kg": f"{vol_weight:.2f}",
                    "박스별정보JSON": json.dumps(box_dims, ensure_ascii=False),
                    "바코드목록JSON": json.dumps([d["바코드"] for d in box_dims], ensure_ascii=False),
                    "수출면장번호": export_license_no.strip(), "추가요청": note.strip(), "상태": "접수", "연결 B/L 번호": "", "변경요청JSON": "", "관리자메모": ""
                }
                all_requests.append(new_req)
                _write_customer_csv(CUSTOMER_REQUEST_FILE, all_requests)
                _customer_history_append({"일시": now, "접수번호": req_id, "고객사아이디": cid, "작업자": company, "작업": "신규 접수 및 박스별 바코드 발급", "변경내용": json.dumps(new_req, ensure_ascii=False)})
                st.success(f"접수가 완료되었습니다. 접수번호: {req_id} / QR·바코드 {len(box_dims)}개 발급 완료")

                # 접수 직후 해당 접수 건의 A4 라벨을 바로 인쇄할 수 있도록 출력 화면 생성
                import html as _html
                immediate_labels = []
                for li, bd in enumerate(box_dims):
                    barcode_value = str(bd.get("바코드", "")).strip()
                    qr_data_uri = ""
                    try:
                        import qrcode
                        qr_obj = qrcode.QRCode(box_size=7, border=2)
                        qr_obj.add_data(barcode_value)
                        qr_obj.make(fit=True)
                        qr_img = qr_obj.make_image(fill_color="black", back_color="white")
                        qr_buf = io.BytesIO()
                        qr_img.save(qr_buf, format="PNG")
                        qr_data_uri = "data:image/png;base64," + base64.b64encode(qr_buf.getvalue()).decode("ascii")
                    except Exception:
                        pass
                    immediate_labels.append({
                        "접수번호": req_id, "고객사": company, "화주": shipper.strip(),
                        "도착국가": dest_country, "품목": item_name,
                        "박스": f"{li+1}/{len(box_dims)}", "바코드": barcode_value,
                        "QR이미지": qr_data_uri,
                        "로고": label_logo_data_uri,
                    })
                safe_labels = json.dumps(immediate_labels, ensure_ascii=False).replace("</", "<\\/")
                immediate_html = r"""<!doctype html><html><head><meta charset="utf-8"><style>
                @page{size:A4 portrait;margin:8mm}*{box-sizing:border-box}body{font-family:Arial,'Malgun Gothic',sans-serif;margin:0;color:#111}
                .toolbar{text-align:center;padding:10px}.sheet{width:194mm;height:281mm;margin:0 auto;display:grid;grid-template-rows:1fr 1fr;gap:3mm;page-break-after:always;break-after:page}
                .label{border:1.5px solid #b3262d;border-radius:2mm;padding:6mm;display:grid;grid-template-columns:38mm minmax(0,1fr);grid-template-rows:auto 1fr;gap:3mm;overflow:hidden;break-inside:avoid;position:relative}
                .info{grid-column:1 / -1;grid-row:1;min-width:0;font-size:10.5pt;line-height:1.55;overflow-wrap:anywhere}
                .brandhead{display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-start;gap:1.5mm;border-bottom:1.2mm solid #b3262d;padding-bottom:3mm;margin-bottom:3mm;max-width:100%;overflow:hidden}
                .brandlogo{display:block;width:27mm;max-width:100%;height:18mm;object-fit:contain;object-position:left center}
                .brand{font-size:15pt;font-weight:900;letter-spacing:0;line-height:1.2;white-space:nowrap;max-width:100%}
                .boxno{font-size:16pt;font-weight:800;margin-top:2mm;background:#f1f5f9;padding:2mm}
                .qrwrap{grid-column:1;grid-row:2;display:flex;flex-direction:column;align-items:center;justify-content:center;min-width:0}
                .qr{width:32mm;height:32mm;object-fit:contain}
                .barwrap{grid-column:2;grid-row:2;align-self:center;text-align:center;min-width:0;overflow:hidden}
                .barcode{display:block;width:100%;height:27mm}.code{font-size:10pt;font-weight:bold;overflow-wrap:anywhere}
                @media print{.toolbar{display:none}.sheet{margin:0}}
                </style><script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script></head><body>
                <div class="toolbar"><button onclick="window.print()">A4 라벨 인쇄</button>　접수 완료: QR·바코드 라벨 __COUNT__개 / A4 한 장에 2개</div><div id="pages"></div>
                <script>const rows=__ROWS__;const root=document.getElementById('pages');let sheet;rows.forEach((r,i)=>{if(i%2===0){sheet=document.createElement('div');sheet.className='sheet';root.appendChild(sheet)}
                const d=document.createElement('div');d.className='label';const info=document.createElement('div');
                info.innerHTML='<div class="brandhead">'+(r.로고?'<img class="brandlogo" src="'+r.로고+'">':'')+'<div class="brand">(주)범운해운항공</div></div><div class="info">접수번호: '+r.접수번호+'<br>고객사: '+r.고객사+'<br>화주: '+r.화주+'<br>도착국가: '+r.도착국가+'　품목: '+r.품목+'<div class="boxno">BOX '+r.박스+'</div></div>';d.appendChild(info);
                const qr=document.createElement('div');qr.className='qrwrap';if(r.QR이미지){const im=document.createElement('img');im.className='qr';im.src=r.QR이미지;qr.appendChild(im);qr.insertAdjacentHTML('beforeend','<b>QR CODE</b>')}else{qr.textContent='QR 생성 실패';}d.appendChild(qr);
                const bar=document.createElement('div');bar.className='barwrap';const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.classList.add('barcode');bar.appendChild(svg);const code=document.createElement('div');code.className='code';code.textContent=r.바코드;bar.appendChild(code);bar.insertAdjacentHTML('beforeend','<b>CODE 128 BARCODE</b>');d.appendChild(bar);sheet.appendChild(d);
                if(window.JsBarcode){JsBarcode(svg,r.바코드,{format:'CODE128',displayValue:false,margin:8,height:75,width:2,lineColor:'#000',background:'#fff'});}
                });
                window.addEventListener('load',()=>{setTimeout(()=>window.print(),900)});</script></body></html>""".replace("__ROWS__", safe_labels).replace("__COUNT__", str(len(box_dims)))
                components.html(immediate_html, height=950, scrolling=True)
                st.info("인쇄 창이 자동으로 열리지 않으면 위 라벨 화면의 ‘A4 라벨 인쇄’ 버튼을 눌러주세요. 인쇄 설정은 A4 세로·배율 100%를 권장합니다.")

    with tab_list:
        if not mine:
            st.info("아직 접수한 화물이 없습니다.")
        else:
            display_rows = [{"접수번호": r.get("접수번호", ""), "접수일시": r.get("접수일시", ""), "화주상호": r.get("화주상호", ""), "품목": r.get("품목", ""), "실제중량kg": r.get("실제중량kg", ""), "CBM": r.get("CBM", ""), "상태": r.get("상태", ""), "연결 B/L 번호": r.get("연결 B/L 번호", "")} for r in mine]
            st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
            choice = st.selectbox("수정할 접수 건 선택", options=[r.get("접수번호", "") for r in mine], key="customer_request_select")
            target = next((r for r in mine if r.get("접수번호", "") == choice), None)
            if target:
                billed = customer_request_is_billed(target)

                # B/L 등록 전 고객사 본인이 잘못 접수한 건을 직접 삭제할 수 있습니다.
                with st.expander("🗑️ 선택한 접수 건 삭제", expanded=False):
                    if billed:
                        st.warning("B/L 등록된 접수 건은 고객사가 직접 삭제할 수 없습니다. 관리자에게 요청해 주세요.")
                    else:
                        st.warning("삭제하면 이 접수 건과 박스별 바코드 정보가 고객사 목록에서 삭제됩니다.")
                        confirm_customer_delete = st.checkbox(
                            f"{choice} 접수 건을 삭제하는 데 동의합니다.",
                            key=f"customer_confirm_delete_{choice}"
                        )
                        if st.button(
                            "🗑️ 선택한 접수 건 삭제하기",
                            key=f"customer_delete_{choice}",
                            disabled=not confirm_customer_delete,
                            use_container_width=True
                        ):
                            all_requests = [
                                r for r in all_requests
                                if not (
                                    str(r.get("접수번호", "")) == str(choice)
                                    and str(r.get("고객사아이디", "")) == str(cid)
                                )
                            ]
                            _write_customer_csv(CUSTOMER_REQUEST_FILE, all_requests)
                            _customer_history_append({
                                "일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "접수번호": choice,
                                "고객사아이디": cid,
                                "작업자": company,
                                "작업": "고객사 B/L 미등록 접수 삭제",
                                "변경내용": json.dumps(target, ensure_ascii=False)
                            })
                            st.success("선택한 접수 건을 삭제했습니다.")
                            st.rerun()

                # 과거 접수 건에 바코드가 없으면 기존 박스 수량에 맞춰 고유번호를 보완합니다.
                try:
                    label_boxes = json.loads(target.get("박스별정보JSON", "[]") or "[]")
                except Exception:
                    label_boxes = []
                if not label_boxes:
                    try:
                        import uuid
                        old_count = max(1, int(float(target.get("박스수량", 1) or 1)))
                        old_w = float(target.get("가로cm", 1) or 1)
                        old_l = float(target.get("세로cm", 1) or 1)
                        old_h = float(target.get("높이cm", 1) or 1)
                        label_boxes = [
                            {
                                "박스순번": bi + 1,
                                "가로cm": old_w, "세로cm": old_l, "높이cm": old_h,
                                "바코드": f"BW{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                                "입고상태": "미입고"
                            }
                            for bi in range(old_count)
                        ]
                        target["박스별정보JSON"] = json.dumps(label_boxes, ensure_ascii=False)
                        target["바코드목록JSON"] = json.dumps(
                            [b["바코드"] for b in label_boxes], ensure_ascii=False
                        )
                        req_idx = next(
                            (i for i, r in enumerate(all_requests)
                             if r.get("접수번호", "") == choice and r.get("고객사아이디", "") == cid),
                            None
                        )
                        if req_idx is not None:
                            all_requests[req_idx] = target
                            _write_customer_csv(CUSTOMER_REQUEST_FILE, all_requests)
                            _customer_history_append({
                                "일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "접수번호": choice, "고객사아이디": cid, "작업자": company,
                                "작업": "기존 접수 건 QR·바코드 보완 발급",
                                "변경내용": json.dumps(target, ensure_ascii=False)
                            })
                    except Exception as barcode_fix_error:
                        st.warning(f"기존 접수 건의 바코드 보완 중 오류: {barcode_fix_error}")
                if label_boxes:
                    st.markdown("#### 🏷 A4 화물 라벨 출력 (QR + 일반 바코드)")
                    st.caption("일반 A4 용지 기준 한 장에 라벨 2개씩 배치됩니다. 박스마다 QR코드와 Code 128 바코드가 함께 인쇄됩니다.")
                    label_records = []
                    for i, b in enumerate(label_boxes):
                        barcode_value = str(b.get("바코드", "")).strip()
                        qr_data_uri = ""
                        if barcode_value:
                            try:
                                import qrcode
                                qr_obj = qrcode.QRCode(box_size=7, border=2)
                                qr_obj.add_data(barcode_value)
                                qr_obj.make(fit=True)
                                qr_img = qr_obj.make_image(fill_color="black", back_color="white")
                                qr_buf = io.BytesIO()
                                qr_img.save(qr_buf, format="PNG")
                                qr_data_uri = "data:image/png;base64," + base64.b64encode(qr_buf.getvalue()).decode("ascii")
                            except Exception:
                                qr_data_uri = ""
                        label_records.append({
                            "접수번호": target.get("접수번호", ""),
                            "고객사": target.get("고객사상호", company),
                            "화주": target.get("화주상호", ""),
                            "도착국가": target.get("도착국가", ""),
                            "품목": target.get("품목", ""),
                            "박스": f"{i+1}/{len(label_boxes)}",
                            "바코드": barcode_value,
                            "QR이미지": qr_data_uri,
                            "로고": label_logo_data_uri,
                            "실제중량": float(b.get("실제중량kg") or target.get("실제중량kg") or 0),
                            "가로": float(b.get("가로cm") or target.get("가로cm") or 0),
                            "세로": float(b.get("세로cm") or target.get("세로cm") or 0),
                            "높이": float(b.get("높이cm") or target.get("높이cm") or 0),
                            "접수일자": str(target.get("접수일시", "")),
                            "운송형태": str(target.get("운송형태", "항공(Air)")),
                            "비고": str(target.get("추가요청", "") or target.get("추가요청사항", "") or target.get("품목", "")),
                        })
                    label_json = json.dumps(label_records, ensure_ascii=False).replace("</", "<\\/")
                    label_html = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"></script>
<style>
@page{size:A4 portrait;margin:7mm}
*{box-sizing:border-box}
body{margin:0;background:#f1f3f5;color:#111;font-family:Arial,'Malgun Gothic',sans-serif}
.toolbar{padding:10px;text-align:center;font-size:12px}
.toolbar button{background:#b3262d;color:#fff;border:0;border-radius:6px;padding:10px 22px;font-size:15px;font-weight:700;cursor:pointer}
.sheet{width:196mm;height:283mm;margin:8px auto;display:grid;grid-template-rows:1fr 1fr;gap:4mm;page-break-after:always;background:#fff}
.label{height:139.5mm;border:1.5mm solid #c9272c;border-radius:4mm;padding:5mm;display:grid;grid-template-columns:44% 36% 20%;grid-template-rows:48% 52%;gap:0;overflow:hidden;background:#fff}
.topbrand{grid-column:1;grid-row:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2mm;padding:1mm 2mm 3mm;min-width:0;max-width:100%;overflow:hidden;text-align:center}
.brandlogo{display:block;width:27mm;height:21mm;max-width:100%;object-fit:contain;object-position:center;flex:0 0 auto}
.brandtext{display:block;width:100%;min-width:0;max-width:100%;white-space:normal;text-align:center;overflow:hidden}
.brand{font-size:15pt;font-weight:900;letter-spacing:-.3px;line-height:1.2;color:#102b50;white-space:nowrap;max-width:100%;}
.brand-en{font-size:6.5pt;font-weight:700;color:#526071;letter-spacing:0;margin-top:1mm;white-space:normal;overflow-wrap:anywhere}
.shipinfo{grid-column:2;grid-row:1;border-left:1px solid #aeb4bb;padding:1mm 3mm;display:grid;grid-template-rows:repeat(4,1fr);min-width:0}
.info-row{display:grid;grid-template-columns:25mm 1fr;align-items:center;border-bottom:1px solid #d2d5d9;font-size:11pt;min-width:0}
.info-row:last-child{border-bottom:0}.info-key{font-weight:700;white-space:nowrap}.info-val{font-weight:700;overflow-wrap:anywhere;min-width:0}
.weightbox{grid-column:3;grid-row:1;border-left:1px solid #aeb4bb;padding:0 0 0 3mm;display:flex;flex-direction:column;min-width:0}
.boxno{background:#d71920;color:white;text-align:center;font-size:19pt;font-weight:900;border-radius:2mm;padding:2mm 1mm;margin-bottom:1mm;white-space:nowrap}
.weight-row{display:flex;justify-content:space-between;gap:1mm;border-bottom:1px solid #d2d5d9;padding:2mm 0;font-size:10pt;white-space:nowrap}.weight-row b{font-size:11pt}
.codes{grid-column:1/4;grid-row:2;border-top:1.5mm solid #d71920;margin-top:1mm;padding-top:3mm;display:grid;grid-template-columns:29mm minmax(0,1fr) 54mm;gap:4mm;align-items:center;min-height:0}
.qrwrap{height:100%;border:1px solid #cbd0d5;border-radius:2mm;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:1mm;min-width:0}
.qr{width:25mm;height:25mm;object-fit:contain}.qrlabel{font-size:8pt;font-weight:900;margin-top:1mm;color:#222}
.barwrap{height:100%;border:1px solid #cbd0d5;border-radius:2mm;padding:2mm 3mm;display:flex;flex-direction:column;align-items:center;justify-content:center;min-width:0;overflow:hidden}
.barcode{display:block;width:100%;height:23mm;max-width:100%;overflow:hidden}.code{font-size:11pt;font-weight:900;letter-spacing:.2px;text-align:center;overflow-wrap:anywhere;max-width:100%;margin-top:1mm}.barcaption{font-size:8pt;font-weight:800;margin-top:1mm}
.extrainfo{height:100%;border-left:1px solid #aeb4bb;padding-left:3mm;display:flex;flex-direction:column;justify-content:center;min-width:0}
.extra-row{display:grid;grid-template-columns:19mm 1fr;gap:1mm;border-bottom:1px solid #d2d5d9;padding:3mm 0;font-size:9.5pt;min-width:0}.extra-row:last-child{border-bottom:0}.extra-val{overflow-wrap:anywhere;font-weight:600}
.empty{font-size:8pt;color:#b91c1c;text-align:center}
@media print{body{background:#fff}.toolbar{display:none}.sheet{margin:0;box-shadow:none}.label{break-inside:avoid}}
@media screen{.sheet{box-shadow:0 1px 8px #bbb}}
</style></head><body>
<div class="toolbar"><button onclick="window.print()">A4 라벨 인쇄</button>　A4 세로 · 한 장에 라벨 2개 · 인쇄 배율 100%</div><div id="pages"></div>
<script>
const rows=__ROWS__;const root=document.getElementById('pages');let sheet;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
rows.forEach((r,i)=>{
 if(i%2===0){sheet=document.createElement('div');sheet.className='sheet';root.appendChild(sheet);}
 const actual=Number(r.실제중량||0),cbm=(Number(r.가로||0)*Number(r.세로||0)*Number(r.높이||0))/1000000;
 const divisor=String(r.운송형태||'').includes('해상')?6000:5000;
 const volume=(Number(r.가로||0)*Number(r.세로||0)*Number(r.높이||0))/divisor;
 const charge=Math.max(actual,volume);
 const d=document.createElement('div');d.className='label';
 d.innerHTML=`<div class="topbrand">${r.로고?`<img class="brandlogo" src="${r.로고}" alt="범운 로고">`:''}<div class="brandtext"><div class="brand">(주)범운해운항공</div><div class="brand-en">BUMWOON OCEAN &amp; AIR CO., LTD.</div></div></div>
 <div class="shipinfo"><div class="info-row"><span class="info-key">접수번호</span><span class="info-val">${esc(r.접수번호)}</span></div><div class="info-row"><span class="info-key">화주명</span><span class="info-val">${esc(r.화주)}</span></div><div class="info-row"><span class="info-key">도착국가</span><span class="info-val">${esc(r.도착국가)}</span></div><div class="info-row"><span class="info-key">품　목</span><span class="info-val">${esc(r.품목)}</span></div></div>
 <div class="weightbox"><div class="boxno">BOX ${esc(r.박스)}</div><div class="weight-row"><span>실제중량</span><b>${actual.toFixed(2)} kg</b></div><div class="weight-row"><span>부피중량</span><b>${volume.toFixed(2)} kg</b></div><div class="weight-row"><span>적용중량</span><b>${charge.toFixed(2)} kg</b></div></div>
 <div class="codes"><div class="qrwrap">${r.QR이미지?`<img class="qr" src="${r.QR이미지}" alt="QR 코드"><div class="qrlabel">QR CODE</div>`:`<div class="empty">QR 생성 실패</div>`}</div><div class="barwrap"><svg class="barcode"></svg><div class="code">${esc(r.바코드)}</div><div class="barcaption">CODE 128 BARCODE</div></div><div class="extrainfo"><div class="extra-row"><span>접수일자</span><span class="extra-val">${esc(r.접수일자)}</span></div><div class="extra-row"><span>고객사</span><span class="extra-val">${esc(r.고객사)}</span></div><div class="extra-row"><span>비　고</span><span class="extra-val">${esc(r.비고)}</span></div></div></div>`;
 sheet.appendChild(d);
 if(window.JsBarcode&&r.바코드){try{JsBarcode(d.querySelector('svg'),r.바코드,{format:'CODE128',displayValue:false,margin:3,height:58,width:1.45,lineColor:'#000',background:'#fff'});}catch(e){d.querySelector('.barwrap').insertAdjacentHTML('beforeend','<div class="empty">바코드 생성 실패</div>');}}
 else{d.querySelector('.barwrap').insertAdjacentHTML('beforeend','<div class="empty">바코드 라이브러리 연결 실패</div>');}
});
</script></body></html>""".replace("__ROWS__", label_json)
                    components.html(label_html, height=900, scrolling=True)
                else:
                    st.info("이 접수 건에는 박스별 바코드가 없습니다. 새로 접수한 건부터 라벨 출력이 제공됩니다.")
                if billed:
                    st.warning("이 건은 B/L 등록 후입니다. 아래에서 수정 요청을 제출하면 사내 관리자가 승인한 뒤 반영합니다.")
                else:
                    st.info("B/L 등록 전이므로 고객사가 직접 수정할 수 있습니다.")
                try:
                    edit_dims = [float(target.get(k, 0) or 0) for k in ("가로cm", "세로cm", "높이cm")]
                    edit_weight = float(target.get("실제중량kg", 0) or 0)
                    edit_cartons = int(float(target.get("박스수량", 1) or 1))
                except Exception:
                    edit_dims, edit_weight, edit_cartons = [1.0, 1.0, 1.0], 1.0, 1
                with st.form("customer_edit_freight_form"):
                    ce1 = st.columns(3)
                    with ce1[0]: e_shipper = st.text_input("화주 상호 *", value=target.get("화주상호", ""))
                    with ce1[1]: e_address = st.text_input("화주 주소 *", value=target.get("화주주소", ""))
                    with ce1[2]: e_phone = st.text_input("화주 전화번호 *", value=target.get("화주전화번호", ""))
                    ce2 = st.columns(3)
                    with ce2[0]: e_consignee = st.text_input("해외 수하인 상호 *", value=target.get("해외수하인", ""))
                    with ce2[1]: e_caddr = st.text_input("해외 수하인 주소 *", value=target.get("해외수하인주소", ""))
                    with ce2[2]: e_ctel = st.text_input("해외 수하인 전화번호", value=target.get("해외수하인전화번호", ""))
                    current_country = str(target.get("도착국가", "")).strip()
                    country_options = list(CUSTOMER_DEST_COUNTRIES)
                    if current_country and current_country not in country_options:
                        country_options.insert(0, current_country)
                    e_country = st.selectbox("도착 국가 선택 *", options=country_options, index=country_options.index(current_country) if current_country in country_options else 0, key=f"customer_edit_country{choice}", help="도착 국가를 목록에서 선택하세요.")
                    current_item = str(target.get("품목", "")).strip()
                    item_options = list(CUSTOMER_ITEM_OPTIONS)
                    if current_item and current_item not in item_options:
                        item_options.insert(0, current_item)
                    e_item = st.selectbox("품목 *", options=item_options, index=item_options.index(current_item) if current_item in item_options else 0, key=f"customer_edit_item_{choice}")
                    e_transport = st.selectbox("운송 형태", ["항공(Air)", "해상(LCL)"], index=0 if target.get("운송형태", "항공(Air)") == "항공(Air)" else 1)
                    e_weight = st.number_input("실제 중량 (kg) *", min_value=0.0, value=max(0.0, edit_weight), step=0.5, format="%.2f")
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1: e_width = st.number_input("가로 (cm) *", min_value=0.0, value=max(0.0, edit_dims[0]), step=1.0)
                    with ec2: e_length = st.number_input("세로 (cm) *", min_value=0.0, value=max(0.0, edit_dims[1]), step=1.0)
                    with ec3: e_height = st.number_input("높이 (cm) *", min_value=0.0, value=max(0.0, edit_dims[2]), step=1.0)
                    e_cartons = st.number_input("박스 수량 (CTN) *", min_value=1, value=max(1, edit_cartons), step=1)
                    e_export_license = st.text_input("수출면장 번호 (해당 시 입력)", value=target.get("수출면장번호", ""), key=f"customer_edit_license_{choice}")
                    e_note = st.text_input("추가 요청 사항 (선택)", value=target.get("추가요청", ""))
                    preview_vol = e_width * e_length * e_height * e_cartons / (5000 if e_transport == "항공(Air)" else 6000)
                    pv1, pv2, pv3 = st.columns(3)
                    # CBM 미리보기 값을 별도 계산해 변수명 오타로 인한 NameError 방지
                    preview_cbm = (float(e_width) * float(e_length) * float(e_height) * int(e_cartons)) / 1000000.0
                    pv1.metric("CBM", f"{preview_cbm:.4f}")
                    pv2.metric("부피중량", f"{preview_vol:.2f} kg")
                    pv3.metric("적용중량", f"{max(e_weight, preview_vol):.2f} kg")
                    save_edit = st.form_submit_button("💾 수정 저장 / 수정 요청", use_container_width=True, type="primary")
                if save_edit:
                    required = [e_shipper, e_address, e_phone, e_consignee, e_caddr, e_country, e_item]
                    if not all(str(v).strip() for v in required) or e_weight <= 0 or min(e_width, e_length, e_height) <= 0 or e_cartons <= 0:
                        st.error("필수 항목을 확인해 주세요. 중량·규격·수량은 0보다 커야 합니다.")
                    else:
                        cbm = e_width * e_length * e_height * e_cartons / 1000000.0
                        vol = e_width * e_length * e_height * e_cartons / (5000 if e_transport == "항공(Air)" else 6000)
                        updated = dict(target)
                        updated.update({"화주상호":e_shipper.strip(), "화주주소":e_address.strip(), "화주전화번호":e_phone.strip(), "해외수하인":e_consignee.strip(), "해외수하인주소":e_caddr.strip(), "해외수하인전화번호":e_ctel.strip(), "도착국가":e_country.strip(), "품목":e_item.strip(), "운송형태":e_transport, "실제중량kg":f"{e_weight:.2f}", "가로cm":f"{e_width:.2f}", "세로cm":f"{e_length:.2f}", "높이cm":f"{e_height:.2f}", "박스수량":str(int(e_cartons)), "CBM":f"{cbm:.4f}", "부피중량kg":f"{vol:.2f}", "수출면장번호":e_export_license.strip(), "추가요청":e_note.strip()})
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        if billed:
                            target["변경요청JSON"] = json.dumps({"요청일시":now,"요청자":company,"변경후":updated}, ensure_ascii=False)
                            target["상태"] = "B/L 등록 후 수정 승인 대기"
                            action = "B/L 등록 후 수정 승인 요청"
                        else:
                            idx = next(i for i, r in enumerate(all_requests) if r.get("접수번호", "") == choice and r.get("고객사아이디", "") == cid)
                            all_requests[idx] = updated
                            action = "B/L 등록 전 고객 수정"
                        _write_customer_csv(CUSTOMER_REQUEST_FILE, all_requests)
                        _customer_history_append({"일시":now,"접수번호":choice,"고객사아이디":cid,"작업자":company,"작업":action,"변경내용":json.dumps(updated, ensure_ascii=False)})
                        st.success("수정 요청을 관리자에게 전달했습니다." if billed else "접수 내용이 수정되었습니다.")
                        st.rerun()
    if st.button("⬅ 화물 추적 홈으로 돌아가기", use_container_width=True):
        st.session_state.customer_logged_in = False
        st.query_params.clear()
        st.rerun()


def _admin_customer_freight_menu():
    if st.session_state.user_role != "관리자(대표)":
        st.error("대표 관리자만 고객사 계정과 접수 내용을 관리할 수 있습니다.")
        st.stop()
    st.markdown("### 🏢 고객사 계정 및 화물 접수 관리")
    accounts = _customer_accounts()
    requests = _customer_requests()
    t_accounts, t_requests, t_history = st.tabs(["고객사 계정 발급", "화물 접수 / 수정 승인", "수정 이력"])
    with t_accounts:
        # 기존 거래처 등록 자료(client_data.csv)에서 고객사 상호 목록을 가져옵니다.
        registered_companies = []
        for company in st.session_state.get("client_list", []):
            company_name = str(company).strip()
            if company_name and company_name not in ("없음", "선택하세요") and company_name not in registered_companies:
                registered_companies.append(company_name)
        # 기존 고객사 계정의 상호도 유지하여, 거래처 목록 정리 전까지 계정 정보가 사라지지 않게 합니다.
        for account in accounts:
            company_name = str(account.get("고객사상호", "")).strip()
            if company_name and company_name not in registered_companies:
                registered_companies.append(company_name)

        if not registered_companies:
            st.warning("선택할 고객사 상호가 없습니다. 먼저 '매출 거래처(화주) 관리'에서 거래처를 등록해 주세요.")

        with st.form("create_customer_account_form"):
            new_id = st.text_input("고객사 아이디")
            new_pw = st.text_input("초기 비밀번호", type="password")
            company_options = ["상호를 선택하세요"] + registered_companies
            new_company = st.selectbox("고객사 상호 선택", company_options, index=0, help="등록된 거래처 목록에서 고객사 상호를 선택하세요.")
            new_contact = st.text_input("담당자 / 연락처 (선택)")
            make_account = st.form_submit_button("➕ 고객사 계정 생성", type="primary")
        if make_account:
            new_id = new_id.strip()
            new_company = "" if new_company == "상호를 선택하세요" else new_company.strip()
            if not new_id or not new_pw or not new_company:
                st.error("아이디, 비밀번호를 입력하고 고객사 상호를 드롭다운에서 선택해 주세요.")
            elif any(a.get("아이디", "") == new_id for a in accounts):
                st.error("이미 사용 중인 아이디입니다.")
            else:
                accounts.append({"아이디":new_id,"비밀번호해시":customer_hash_password(new_pw),"고객사상호":new_company,"담당자연락처":new_contact.strip(),"상태":"승인","생성일시":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                write_customer_csv(CUSTOMER_ACCOUNT_FILE, accounts)
                st.success("고객사 계정이 생성되었습니다. 고객사에 아이디와 초기 비밀번호를 안전하게 전달해 주세요.")
                st.rerun()
        if accounts:
            st.dataframe(pd.DataFrame([{k:a.get(k,"") for k in ["아이디","고객사상호","담당자연락처","상태","생성일시"]} for a in accounts]), use_container_width=True, hide_index=True)
            chosen_id = st.selectbox("계정 상태 변경 대상", [a.get("아이디","") for a in accounts], key="cust_account_status_select")
            chosen_acc = next(a for a in accounts if a.get("아이디","") == chosen_id)
            new_status = st.selectbox("상태", ["승인","중지"], index=0 if chosen_acc.get("상태","승인")=="승인" else 1, key="cust_account_status_value")
            if st.button("계정 상태 저장"):
                for a in accounts:
                    if a.get("아이디","")==chosen_id: a["상태"] = new_status
                write_customer_csv(CUSTOMER_ACCOUNT_FILE, accounts)
                st.success("계정 상태를 저장했습니다.")
                st.rerun()
    with t_requests:
        if not requests:
            st.info("고객사 화물 접수 내역이 없습니다.")
        else:
            st.markdown("#### 📲 창고 바코드 스캔 입고")
            st.caption("휴대폰은 QR/Code 128 라벨을 촬영하면 자동 입고 처리합니다. USB/무선 스캐너는 입력칸에 커서를 두고 스캔한 뒤 Enter를 누르면 자동 처리됩니다.")

            def _warehouse_receive_one(scan_value, source="스캔"):
                scan_value = str(scan_value or "").strip()
                if not scan_value:
                    return False, "바코드 번호가 비어 있습니다."
                for req in requests:
                    try:
                        scan_boxes = json.loads(req.get("박스별정보JSON", "[]") or "[]")
                    except Exception:
                        scan_boxes = []
                    for bx in scan_boxes:
                        if str(bx.get("바코드", "")).strip() != scan_value:
                            continue
                        if bx.get("입고상태") == "입고":
                            return False, f"이미 입고된 박스입니다: {req.get('접수번호','')} / 박스 {bx.get('박스순번','')}"
                        now_scan = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        bx["입고상태"] = "입고"
                        bx["입고일시"] = now_scan
                        req["박스별정보JSON"] = json.dumps(scan_boxes, ensure_ascii=False)
                        total_boxes = len(scan_boxes)
                        arrived_boxes = sum(1 for item in scan_boxes if item.get("입고상태") == "입고")
                        req["입고박스수"] = str(arrived_boxes)
                        req["상태"] = ("전체 박스 입고 완료" if arrived_boxes >= total_boxes
                                       else f"부분 입고 ({arrived_boxes}/{total_boxes})")
                        write_customer_csv(CUSTOMER_REQUEST_FILE, requests)
                        customer_history_append({
                            "일시": now_scan, "접수번호": req.get("접수번호", ""),
                            "고객사아이디": req.get("고객사아이디", ""),
                            "작업자": st.session_state.get("logged_in_user", "관리자"),
                            "작업": f"{source} 박스 입고", "변경내용": scan_value
                        })
                        return True, f"입고 완료: {req.get('접수번호','')} / 박스 {bx.get('박스순번','')} ({arrived_boxes}/{total_boxes})"
                return False, "등록되지 않은 바코드입니다. 해당 박스의 QR/바코드 라벨을 확인해 주세요."

            camera_photo = st.camera_input("📷 휴대폰으로 QR 또는 Code 128 촬영", key="warehouse_barcode_camera")
            if camera_photo is not None:
                try:
                    import hashlib
                    photo_bytes = camera_photo.getvalue()
                    photo_hash = hashlib.sha256(photo_bytes).hexdigest()
                    if st.session_state.get("warehouse_last_camera_hash") != photo_hash:
                        from PIL import Image
                        from pyzbar.pyzbar import decode as decode_barcode
                        camera_image = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
                        decoded_items = decode_barcode(camera_image)
                        if decoded_items:
                            decoded_value = decoded_items[0].data.decode("utf-8", errors="ignore").strip()
                            if decoded_value:
                                st.session_state["warehouse_last_camera_hash"] = photo_hash
                                ok, message = _warehouse_receive_one(decoded_value, "휴대폰 카메라")
                                st.session_state["warehouse_scan_feedback"] = ("success" if ok else "warning", f"{message} · 인식번호: {decoded_value}")
                                if ok:
                                    st.session_state["warehouse_scanned_barcode"] = ""
                                    st.rerun()
                            else:
                                st.warning("바코드는 감지했지만 번호를 읽지 못했습니다. 라벨을 다시 촬영해 주세요.")
                        else:
                            st.warning("QR 또는 Code 128을 읽지 못했습니다. 라벨을 화면에 크게 맞춰 다시 촬영해 주세요.")
                except ImportError:
                    st.error("카메라 판독 모듈이 없습니다. requirements.txt의 pyzbar/Pillow와 packages.txt의 libzbar0 설치 후 재배포해 주세요.")
                except Exception as camera_error:
                    st.error(f"카메라 판독 오류: {camera_error}")

            feedback = st.session_state.pop("warehouse_scan_feedback", None)
            if feedback:
                if feedback[0] == "success":
                    st.success(feedback[1])
                else:
                    st.warning(feedback[1])

            with st.form("warehouse_scanner_form", clear_on_submit=True):
                scanned_barcode = st.text_input(
                    "박스 바코드 번호 (USB/무선 스캐너는 여기를 클릭 후 스캔하고 Enter)",
                    key="warehouse_scanned_barcode",
                    placeholder="QR/바코드 번호가 자동 입력됩니다.",
                    help="스캐너가 바코드를 입력한 뒤 Enter를 보내면 입고 처리됩니다.",
                )
                scan_submit = st.form_submit_button("📦 스캔 입고 처리", type="secondary")
            if scan_submit:
                ok, message = warehouse_receive_one(scanned_barcode, "USB/무선 스캐너 또는 수동")
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.warning(message)
            st.dataframe(pd.DataFrame([{k:r.get(k,"") for k in ["접수번호","접수일시","고객사상호","화주상호","품목","실제중량kg","CBM","상태","연결 B/L 번호"]} for r in requests]), use_container_width=True, hide_index=True)
            req_id = st.selectbox("관리할 접수 건", [r.get("접수번호","") for r in requests], key="admin_customer_request_select")
            target = next(r for r in requests if r.get("접수번호","")==req_id)
            linked_bl = str(target.get("연결 B/L 번호", "")).strip()
            bl_exists = bool(linked_bl) or str(target.get("상태", "")).strip() == "B/L 등록"
            with st.expander("🗑 접수 건 삭제", expanded=False):
                if bl_exists:
                    st.warning("B/L이 연결/등록된 접수 건은 여기서 삭제할 수 없습니다. B/L 등록 내역을 먼저 관리자 절차로 정리해야 합니다.")
                else:
                    st.warning("삭제하면 해당 고객의 접수 목록에서도 사라집니다. 필요한 경우 먼저 백업해 주세요.")
                    confirm_delete = st.checkbox(f"접수번호 {req_id} 삭제에 동의합니다", key=f"confirm_delete_req{req_id}")
                    if st.button("🗑 B/L 미등록 접수 삭제", key=f"delete_customer_request{req_id}", disabled=not confirm_delete):
                        now_delete = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        requests = [r for r in requests if r.get("접수번호", "") != req_id]
                        write_customer_csv(CUSTOMER_REQUEST_FILE, requests)
                        customer_history_append({"일시": now_delete, "접수번호": req_id, "고객사아이디": target.get("고객사아이디", ""), "작업자": st.session_state.get("logged_in_user", "관리자"), "작업": "B/L 미등록 접수 삭제", "변경내용": json.dumps(target, ensure_ascii=False)})
                        st.success(f"{req_id} 접수 건을 삭제했습니다.")
                        st.rerun()
            st.write("접수 상세 / 승인 전 내용 확인 및 수정")
            # 입력창을 3열로 배치해 세로 길이를 줄이고 한 화면에서 확인하기 쉽게 구성
            with st.form(f"admin_edit_customer_request{req_id}"):
                row1 = st.columns(3)
                with row1[0]:
                    ae_shipper = st.text_input("화주 상호", value=target.get("화주상호", ""))
                with row1[1]:
                    ae_shipper_addr = st.text_input("화주 주소", value=target.get("화주주소", ""))
                with row1[2]:
                    ae_shipper_tel = st.text_input("화주 전화번호", value=target.get("화주전화번호", ""))
                row2 = st.columns(3)
                with row2[0]:
                    ae_consignee = st.text_input("해외 수하인", value=target.get("해외수하인", ""))
                with row2[1]:
                    ae_consignee_addr = st.text_input("해외 수하인 주소", value=target.get("해외수하인주소", ""))
                with row2[2]:
                    ae_consignee_tel = st.text_input("해외 수하인 전화번호", value=target.get("해외수하인전화번호", ""))
                row3 = st.columns(3)
                with row3[0]:
                    ae_country = st.selectbox("도착 국가", CUSTOMER_DEST_COUNTRIES,
                        index=CUSTOMER_DEST_COUNTRIES.index(target.get("도착국가", "미국")) if target.get("도착국가", "미국") in CUSTOMER_DEST_COUNTRIES else 0,
                        key=f"admin_req_country{req_id}")
                with row3[1]:
                    ae_item_options = list(CUSTOMER_ITEM_OPTIONS)
                    if target.get("품목", "") and target.get("품목", "") not in ae_item_options:
                        ae_item_options.insert(0, target.get("품목", ""))
                    ae_item = st.selectbox("품목", ae_item_options,
                        index=ae_item_options.index(target.get("품목", ae_item_options[0])) if target.get("품목", ae_item_options[0]) in ae_item_options else 0,
                        key=f"admin_req_item{req_id}")
                with row3[2]:
                    ae_transport = st.selectbox("운송 형태", ["항공(Air)", "해상(LCL)"],
                        index=0 if target.get("운송형태", "항공(Air)") == "항공(Air)" else 1,
                        key=f"admin_req_transport{req_id}")
                row4 = st.columns(5)
                with row4[0]:
                    ae_weight = st.number_input("실제 중량 (kg)", min_value=0.01, value=max(0.01, float(target.get("실제중량kg", 1) or 1)), step=0.5, key=f"admin_req_weight{req_id}")
                with row4[1]:
                    ae_width = st.number_input("가로 (cm)", min_value=0.01, value=max(0.01, float(target.get("가로cm", 1) or 1)), step=1.0, key=f"admin_req_width{req_id}")
                with row4[2]:
                    ae_length = st.number_input("세로 (cm)", min_value=0.01, value=max(0.01, float(target.get("세로cm", 1) or 1)), step=1.0, key=f"admin_req_length_{req_id}")
                with row4[3]:
                    ae_height = st.number_input("높이 (cm)", min_value=0.01, value=max(0.01, float(target.get("높이cm", 1) or 1)), step=1.0, key=f"admin_req_height_{req_id}")
                with row4[4]:
                    ae_cartons = st.number_input("박스 수량", min_value=1, value=max(1, int(float(target.get("박스수량", 1) or 1))), step=1, key=f"admin_req_cartons_{req_id}")
                ae_license = st.text_input("수출면장 번호 (해당 시 입력)", value=target.get("수출면장번호", ""), key=f"admin_req_license_{req_id}")
                ae_note = st.text_input("추가 요청 사항", value=target.get("추가요청", ""), key=f"admin_req_note_{req_id}")
                save_admin_edit = st.form_submit_button("💾 승인 전 수정 저장", use_container_width=True)
            if save_admin_edit:
                now_edit = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated_request = dict(target)
                updated_request.update({
                    "화주상호": ae_shipper.strip(), "화주주소": ae_shipper_addr.strip(), "화주전화번호": ae_shipper_tel.strip(),
                    "해외수하인": ae_consignee.strip(), "해외수하인주소": ae_consignee_addr.strip(), "해외수하인전화번호": ae_consignee_tel.strip(),
                    "도착국가": ae_country, "품목": ae_item, "운송형태": ae_transport,
                    "실제중량kg": f"{ae_weight:.2f}", "가로cm": f"{ae_width:.2f}", "세로cm": f"{ae_length:.2f}", "높이cm": f"{ae_height:.2f}",
                    "박스수량": str(int(ae_cartons)), "CBM": f"{(ae_width * ae_length * ae_height * ae_cartons)/1000000:.4f}",
                    "부피중량kg": f"{(ae_width * ae_length * ae_height * ae_cartons)/(5000 if ae_transport == '항공(Air)' else 6000):.2f}",
                    "수출면장번호": ae_license.strip(), "추가요청": ae_note.strip(), "최종수정일시": now_edit,
                })
                for ri, rr in enumerate(requests):
                    if rr.get("접수번호", "") == req_id:
                        requests[ri] = updated_request
                        break
                _write_customer_csv(CUSTOMER_REQUEST_FILE, requests)
                _customer_history_append({"일시":now_edit,"접수번호":req_id,"고객사아이디":target.get("고객사아이디", ""),"작업자":st.session_state.logged_in_user,"작업":"관리자 승인 전 접수내용 수정","변경내용":json.dumps(updated_request, ensure_ascii=False)})
                st.success("수정 내용을 저장했습니다. 확인 후 승인해 주세요.")
                st.rerun()

            # 승인 버튼 한 번으로 B/L 번호를 발급하고 수출입 B/L 데이터에 즉시 저장합니다.
            if target.get("상태", "접수") != "B/L 등록":
                if st.button("✅ 내용 확인 후 승인 및 수출입 B/L에 자동 등록", type="primary", use_container_width=True, key=f"approve_issue_bl_{req_id}"):
                    existing_nums = [str(x.get("B/L 번호", "")).strip() for x in st.session_state.get("bl_data_list", [])]
                    existing_nums += [str(x.get("연결 B/L 번호", "")).strip() for x in requests]
                    nums = [int(v[2:]) for v in existing_nums if v.startswith("BW") and v[2:].isdigit()]
                    new_bl = str(target.get("연결 B/L 번호", "")).strip() or f"BW{(max(nums) if nums else 260000)+1:06d}"
                    now_approve = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if any(str(x.get("B/L 번호", "")).strip() == new_bl for x in st.session_state.get("bl_data_list", [])):
                        st.error(f"B/L 번호 {new_bl}는 이미 수출입 B/L에 등록되어 있습니다. 중복 등록하지 않았습니다.")
                    else:
                        try:
                            shipper_auto = str(target.get("화주상호", "")).strip()
                            country_auto = str(target.get("도착국가", "미국")).strip()
                            item_auto = str(target.get("품목", "일반화물")).strip()
                            transport_auto = str(target.get("운송형태", "항공(Air)")).strip()
                            weight_auto = float(target.get("실제중량kg", 0) or 0)
                            width_auto = float(target.get("가로cm", 0) or 0)
                            length_auto = float(target.get("세로cm", 0) or 0)
                            height_auto = float(target.get("높이cm", 0) or 0)
                            cartons_auto = max(1, int(float(target.get("박스수량", 1) or 1)))
                            cbm_auto = width_auto * length_auto * height_auto * cartons_auto / 1000000.0
                            divisor_auto = 5000 if transport_auto == "항공(Air)" else 6000
                            charge_auto = float(math.ceil(max(weight_auto, width_auto * length_auto * height_auto * cartons_auto / divisor_auto)))
                            supplier_auto = ""
                            sales_auto = int(calculate_auto_price(shipper_auto, charge_auto, transport_auto, item_auto, country_auto))
                            purchase_auto = int(calculate_purchase_auto_price(supplier_auto, charge_auto, transport_auto, item_auto, country_auto))
                            job_nums = []
                            for x in st.session_state.get("bl_data_list", []):
                                try:
                                    job_nums.append(int(str(x.get("Job 번호", "")).split("-")[-1]))
                                except (ValueError, TypeError):
                                    pass
                            job_no_auto = f"BW-{date.today().year}-{(max(job_nums) if job_nums else 0)+1:03d}"
                            bl_record = {
                                "구분": "수출 (Export)", "날짜": str(date.today()), "Job 번호": job_no_auto, "B/L 번호": new_bl,
                                "국가": country_auto, "출발지": "대한민국 (KOREA)", "화주명(매출)": shipper_auto,
                                "해외수하인": target.get("해외수하인", ""), "해외수하인주소": target.get("해외수하인주소", ""), "해외수하인전화번호": target.get("해외수하인전화번호", ""), "수출면장번호": target.get("수출면장번호", ""),
                                "매입처": supplier_auto, "운송형태": transport_auto, "서비스옵션": "Door To Door", "품목": item_auto,
                                "박스수": f"{cartons_auto} 박스 (CTN)", "부피규격": f"{width_auto:g}×{length_auto:g}×{height_auto:g}cm({cartons_auto}CTN)",
                                "실중량(kg)": weight_auto, "매출실중량(kg)": weight_auto, "매입실중량(kg)": weight_auto,
                                "매출청구중량(kg)": charge_auto, "매입청구중량(kg)": charge_auto, "CBM": f"{cbm_auto:.3f} CBM",
                                "현재 상태": "📦 물류센터 입고 및 접수 완료", "수금상태": "미수", "매출액(원)": sales_auto, "매입액(원)": purchase_auto,
                                "예상Profit(원)": sales_auto - purchase_auto, "비고": f"고객사 접수번호: {req_id} / {target.get('추가요청', '')}",
                                "최종작성자": st.session_state.get("logged_in_user", "관리자"), "최종수정자": "-"
                            }
                            st.session_state.bl_data_list.append(bl_record)
                            save_bl_data(st.session_state.bl_data_list)
                            for ri, rr in enumerate(requests):
                                if rr.get("접수번호", "") == req_id:
                                    rr["연결 B/L 번호"] = new_bl
                                    rr["상태"] = "B/L 등록"
                                    rr["승인일시"] = now_approve
                                    rr["승인자"] = st.session_state.get("logged_in_user", "관리자")
                                    rr["B/L등록일시"] = now_approve
                                    break
                            _write_customer_csv(CUSTOMER_REQUEST_FILE, requests)
                            _customer_history_append({"일시": now_approve, "접수번호": req_id, "고객사아이디": target.get("고객사아이디", ""), "작업자": st.session_state.get("logged_in_user", "관리자"), "작업": "관리자 승인 및 수출입 B/L 자동 등록", "변경내용": new_bl})
                            st.success(f"승인 및 수출입 B/L 자동 등록 완료: {new_bl} / Job 번호: {job_no_auto}")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"B/L 자동 등록 중 오류가 발생했습니다. 접수 상태는 확인 후 다시 시도해 주세요. 상세: {exc}")
            pending = target.get("변경요청JSON", "")
            if pending:
                try:
                    change = json.loads(pending)
                    st.warning(f"수정 승인 대기: {change.get('요청일시','')} / {change.get('요청자','')}")
                    st.json(change.get("변경후", {}))
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        if st.button("✅ 수정 승인", use_container_width=True):
                            changed = change.get("변경후", {})
                            for i, r in enumerate(requests):
                                if r.get("접수번호","")==req_id:
                                    preserved_bl = r.get("연결 B/L 번호", "")
                                    requests[i] = changed
                                    requests[i]["연결 B/L 번호"] = preserved_bl
                                    requests[i]["상태"] = "B/L 등록" if preserved_bl else "접수"
                                    requests[i]["변경요청JSON"] = ""
                                    break
                            _write_customer_csv(CUSTOMER_REQUEST_FILE, requests)
                            _customer_history_append({"일시":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"접수번호":req_id,"고객사아이디":target.get("고객사아이디",""),"작업자":st.session_state.logged_in_user,"작업":"관리자 수정 승인","변경내용":pending})
                            st.success("수정 내용을 승인했습니다.")
                            st.rerun()
                    with ac2:
                        if st.button("❌ 수정 반려", use_container_width=True):
                            for r in requests:
                                if r.get("접수번호","")==req_id:
                                    r["변경요청JSON"] = ""
                                    r["상태"] = "B/L 등록" if r.get("연결 B/L 번호","") else "접수"
                                    break
                            _write_customer_csv(CUSTOMER_REQUEST_FILE, requests)
                            customer_history_append({"일시":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"접수번호":req_id,"고객사아이디":target.get("고객사아이디",""),"작업자":st.session_state.logged_in_user,"작업":"관리자 수정 반려","변경내용":pending})
                            st.success("수정 요청을 반려했습니다.")
                            st.rerun()
                except Exception:
                    st.error("수정 요청 내용을 읽지 못했습니다. 이력을 확인해 주세요.")
            st.markdown("---")
            st.markdown("#### B/L 등록 상태 연결")
            bl_no = st.text_input("연결할 B/L 번호 (비워두면 B/L 등록 전)", value=target.get("연결 B/L 번호", ""), key="admin_customer_link_bl")
            if st.button("B/L 번호 / 상태 저장", type="primary", key=f"save_customer_bl_link{req_id}"):
                clean_bl = str(bl_no).strip()
                now_link = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    # B/L 번호가 입력되면 고객 접수 내용을 수출입 B/L 자료에 생성/연결합니다.
                    if clean_bl:
                        existing_record = next((x for x in st.session_state.get("bl_data_list", []) if str(x.get("B/L 번호", "")).strip() == clean_bl), None)
                        if existing_record is None:
                            shipper_auto = str(target.get("화주상호", "")).strip()
                            country_auto = str(target.get("도착국가", "미국")).strip()
                            item_auto = str(target.get("품목", "일반화물")).strip()
                            transport_auto = str(target.get("운송형태", "항공(Air)")).strip()
                            weight_auto = float(target.get("실제중량kg", 0) or 0)
                            width_auto = float(target.get("가로cm", 0) or 0)
                            length_auto = float(target.get("세로cm", 0) or 0)
                            height_auto = float(target.get("높이cm", 0) or 0)
                            cartons_auto = max(1, int(float(target.get("박스수량", 1) or 1)))
                            cbm_auto = width_auto * length_auto * height_auto * cartons_auto / 1000000.0
                            divisor_auto = 5000 if transport_auto == "항공(Air)" else 6000
                            charge_auto = float(math.ceil(max(weight_auto, width_auto * length_auto * height_auto * cartons_auto / divisor_auto)))
                            sales_auto = int(calculate_auto_price(shipper_auto, charge_auto, transport_auto, item_auto, country_auto))
                            purchase_auto = int(calculate_purchase_auto_price("", charge_auto, transport_auto, item_auto, country_auto))
                            job_nums = []
                            for x in st.session_state.get("bl_data_list", []):
                                try:
                                    job_nums.append(int(str(x.get("Job 번호", "")).split("-")[-1]))
                                except (ValueError, TypeError):
                                    pass
                            job_no_auto = f"BW-{date.today().year}-{(max(job_nums) if job_nums else 0)+1:03d}"
                            bl_record = {
                                "구분": "수출 (Export)", "날짜": str(date.today()), "Job 번호": job_no_auto, "B/L 번호": clean_bl,
                                "국가": country_auto, "출발지": "대한민국 (KOREA)", "화주명(매출)": shipper_auto,
                                "해외수하인": target.get("해외수하인", ""), "해외수하인주소": target.get("해외수하인주소", ""), "해외수하인전화번호": target.get("해외수하인전화번호", ""), "수출면장번호": target.get("수출면장번호", ""),
                                "매입처": "", "운송형태": transport_auto, "서비스옵션": "Door To Door", "품목": item_auto,
                                "박스수": f"{cartons_auto} 박스 (CTN)", "부피규격": f"{width_auto:g}×{length_auto:g}×{height_auto:g}cm({cartons_auto}CTN)",
                                "실중량(kg)": weight_auto, "매출실중량(kg)": weight_auto, "매입실중량(kg)": weight_auto,
                                "매출청구중량(kg)": charge_auto, "매입청구중량(kg)": charge_auto, "CBM": f"{cbm_auto:.3f} CBM",
                                "현재 상태": "📦 물류센터 입고 및 접수 완료", "수금상태": "미수", "매출액(원)": sales_auto, "매입액(원)": purchase_auto,
                                "예상Profit(원)": sales_auto-purchase_auto, "비고": f"고객사 접수번호: {req_id} / {target.get('추가요청', '')}",
                                "최종작성자": st.session_state.get("logged_in_user", "관리자"), "최종수정자": "-"
                            }
                            st.session_state.bl_data_list.append(bl_record)
                            save_bl_data(st.session_state.bl_data_list)
                        # 동일 B/L이 이미 있으면 중복 생성하지 않고 접수 건만 연결합니다.
                    for r in requests:
                        if r.get("접수번호", "") == req_id:
                            r["연결 B/L 번호"] = clean_bl
                            r["상태"] = "B/L 등록" if clean_bl else "접수"
                            if clean_bl:
                                r["B/L등록일시"] = now_link
                            break
                    _write_customer_csv(CUSTOMER_REQUEST_FILE, requests)
                    _customer_history_append({"일시":now_link,"접수번호":req_id,"고객사아이디":target.get("고객사아이디", ""),"작업자":st.session_state.get("logged_in_user", "관리자"),"작업":"B/L 번호 연결 및 수출입 B/L 저장","변경내용":clean_bl})
                    if clean_bl:
                        st.success(f"B/L {clean_bl} 저장 및 연결 완료. ‘등록 B/L 수정 및 Profit 내역’에서 요금과 Profit을 수정할 수 있습니다.")
                    else:
                        st.success("B/L 연결을 비웠습니다. 고객사 접수 상태로 저장했습니다.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"B/L 저장 중 오류가 발생했습니다: {exc}")
    with t_history:
        history = _read_customer_csv(CUSTOMER_HISTORY_FILE)
        if history:
            st.dataframe(pd.DataFrame(history).sort_values("일시", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("아직 수정 이력이 없습니다.")

query_params = st.query_params
mode_param = query_params.get("mode", "")

# ==========================================
# [고객사 포털 / 관리자 로그인 분기]
# ==========================================
if mode_param == "customer":
  _customer_portal()
  st.stop()
elif mode_param == "admin":
  if not st.session_state.logged_in_user:
    login_screen()
    st.stop()
else:
  top_c1, top_c2 = st.columns([6, 1.2])
  with top_c2:
    if st.button("🔐 사내 관리자 로그인", use_container_width=True):
      st.query_params["mode"] = "admin"
      st.rerun()

  logo_img_tag = ""
  if encoded_sidebar_logo:
    logo_img_tag = f"<img src='data:image/png;base64,{encoded_sidebar_logo}' style='width: 250px; max-width: 100%; height: auto; margin-bottom: 8px; border-radius: 8px;'>"

  st.markdown(
      f"""
    <div style="text-align: center; padding: 22px 15px; background-color: white; border-radius: 14px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); margin-bottom: 15px;">
        <div style="display: inline-block;">{logo_img_tag}</div>
        <h1 style="color: #1e3a8a; font-size: 26px; font-weight: 800; margin-bottom: 3px; letter-spacing: -0.5px;">(주)범운해운항공</h1>
        <p style="color: #475569; font-size: 13px; font-weight: 700; letter-spacing: 0.5px; margin: 0;">BUMWOON OCEAN & AIR CO., LTD.</p>
    </div>
    """,
      unsafe_allow_html=True,
  )

  customer_btn_col1, customer_btn_col2 = st.columns([1, 1])
  with customer_btn_col1:
    if st.button("📦 고객 화물 접수", use_container_width=True, type="primary"):
      st.query_params["mode"] = "customer"
      st.rerun()
  with customer_btn_col2:
    st.caption("고객사 로그인 후 화물 입고 접수 및 접수 내역 수정")

  current_bl_data = load_bl_data()
  st.markdown("#### 📦 B/L & 화물 실시간 통합 조회")
  search_query = st.text_input(
      "B/L 번호 또는 UPS 송장번호를 정확히 입력하세요",
      placeholder="예: BW260001 또는 1ZRR4352...",
  )

  clean_input_no = "".join(search_query.strip().split())
  ups_direct_url = (
      f"https://www.ups.com/track?loc=ko_KR&tracknum={clean_input_no}"
      if clean_input_no
      else "https://www.ups.com/track?loc=ko_KR"
  )
  track17_direct_url = (
      f"https://t.17track.net/ko#nums={clean_input_no}"
      if clean_input_no
      else "https://t.17track.net/ko"
  )

  btn_c1, btn_c2 = st.columns(2)
  with btn_c1:
    st.markdown(
        f"<a href='{ups_direct_url}' target='_blank' style='display: block;"
        " text-align: center; background-color: #ffb500; color: #000; padding:"
        " 12px; border-radius: 6px; font-weight: bold; text-decoration: none;"
        " font-size: 13.5px;'>🚚 UPS 바로 추적 시작</a>",
        unsafe_allow_html=True,
    )
  with btn_c2:
    st.markdown(
        f"<a href='{track17_direct_url}' target='_blank' style='display: block;"
        " text-align: center; background-color: #2563eb; color: #fff; padding:"
        " 12px; border-radius: 6px; font-weight: bold; text-decoration: none;"
        " font-size: 13.5px;'>🌐 17TRACK 바로 추적 시작</a>",
        unsafe_allow_html=True,
    )

  st.markdown("<br>", unsafe_allow_html=True)

  if st.button(
      "🔍 사내 화물 추적 조회하기", use_container_width=True, type="primary"
  ) or search_query:
    if search_query.strip() and current_bl_data:
      query = "".join(search_query.strip().lower().split())
      matched = pd.DataFrame()
      df_check = pd.DataFrame(current_bl_data)
      for col in ["B/L 번호", "Job 번호"]:
        if col in df_check.columns:
          temp = df_check[
              df_check[col]
              .astype(str)
              .str.strip()
              .str.lower()
              .str.replace(r"\s+", "", regex=True)
              == query
          ]
          if not temp.empty:
            matched = pd.concat([matched, temp]).drop_duplicates()

      if not matched.empty:
        for idx, row in matched.iterrows():
          bl_num = str(row.get("B/L 번호", "")).strip()

          def clean_v(v, default="-"):
            if v is None:
              return default
            s = str(v).strip()
            if s == "" or s.lower() == "nan":
              return default
            return s

          shipper_n = clean_v(row.get("화주명(매출)"))
          shipper_inf = st.session_state.client_infos.get(shipper_n, {})
          shipper_addr = clean_v(
              shipper_inf.get("주소"), "경기도 김포시 풍무동 326-5번지 2층"
          )
          shipper_tel = clean_v(shipper_inf.get("전화번호"), "-")

          consignee_n = clean_v(row.get("해외수하인"))
          consignee_addr = clean_v(row.get("해외수하인주소"), "-")
          consignee_tel = clean_v(row.get("해외수하인전화번호"), "-")
          dest_c = clean_v(row.get("국가"))
          origin_p = clean_v(row.get("출발지"), "대한민국 (KOREA)")
          ship_date = clean_v(row.get("날짜"), str(date.today()))
          item_name = clean_v(row.get("품목"))
          box_cnt = clean_v(row.get("박스수"), "1 박스")
          vol_spec = clean_v(row.get("부피규격"), "-")
          cbm_val = clean_v(row.get("CBM"), "-")
          sales_cw = row.get("매출청구중량(kg)", 1.0)
          transport_t = clean_v(row.get("운송형태"), "항공(Air)")
          service_opt = clean_v(row.get("서비스옵션"), "Door To Door")
          current_status_str = clean_v(row.get("현재 상태"), "운송 중")

          logo_embed_m = (
              f"<img src='data:image/png;base64,{encoded_sidebar_logo}'"
              " style='height: 38px; vertical-align: middle; margin-right:"
              " 8px;'>"
              if encoded_sidebar_logo
              else ""
          )
          barcode_html_m = generate_barcode_html(bl_num)

          air_c = "☑" if "항공" in transport_t else "☐"
          sea_c = "☑" if "해상" in transport_t else "☐"
          d2d_c = "☑" if "Door" in service_opt else "☐"

          mobile_awb_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            @media print {{
                                body {{ -webkit-print-color-adjust: exact; }}
                                .no-print {{ display: none !important; }}
                                @page {{ size: A4 portrait; margin: 8mm; }}
                            }}
                            body {{
                                font-family: 'Pretendard', sans-serif;
                                color: #1e293b;
                                font-size: 9pt;
                                line-height: 1.3;
                                margin: 0;
                                padding: 5px;
                                background-color: #ffffff;
                            }}
                            .awb-box {{
                                border: 2px solid #0f172a;
                                padding: 15px;
                                border-radius: 6px;
                                background-color: #ffffff;
                                margin-top: 10px;
                            }}
                            .t-tbl {{ width: 100%; border-collapse: collapse; margin-bottom: 6px; }}
                            .t-tbl td {{ border: 1px solid #64748b; padding: 6px 8px; vertical-align: top; }}
                            .s-hdr {{ background-color: #0f172a; color: white; font-weight: bold; font-size: 8.5pt; padding: 2px 5px; margin-bottom: 3px; }}
                            .p-btn {{
                                display: block;
                                width: 100%;
                                background-color: #dc2626;
                                color: white;
                                text-align: center;
                                padding: 12px;
                                font-size: 11pt;
                                font-weight: bold;
                                border: none;
                                border-radius: 6px;
                                cursor: pointer;
                                margin-bottom: 15px;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="awb-box">
                            <button class="p-btn no-print" onclick="window.print()">🖨 휴대폰에서 B/L 운송장 인쇄 / PDF 저장하기</button>

                            <table style="width: 100%; border-bottom: 2px solid #0f172a; padding-bottom: 8px; margin-bottom: 10px;">
                                <tr>
                                    <td style="width: 55%; border: none;">
                                        <div style="display: flex; align-items: center;">
                                            {logo_embed_m}
                                            <div>
                                                <div style="font-size: 12pt; font-weight: 900; color: #1e3a8a;">주식회사 범운해운항공</div>
                                                <div style="font-size: 7pt; color: #475569; font-weight: bold;">BUMWOON OCEAN & AIR CO., LTD.</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td style="width: 45%; text-align: right; border: none;">
                                        <div style="font-size: 7.5pt; color: #64748b; font-weight: bold;">AIR WAYBILL / B/L NO.</div>
                                        {barcode_html_m}
                                    </td>
                                </tr>
                            </table>

                            <table style="width: 100%; background-color: #eff6ff; border: 1px solid #bfdbfe; padding: 10px; border-radius: 6px; margin-bottom: 10px;">
                                <tr>
                                    <td style="border: none; padding: 0;">
                                        • <b>현재 화물 진행 상태:</b> <span style="color: #2563eb; font-weight: bold; font-size: 10.5pt;">{current_status_str}</span><br>
                                        • <b>화주명:</b> {shipper_n} | <b>수하인:</b> {consignee_n}
                                    </td>
                                </tr>
                            </table>

                            <table class="t-tbl">
                                <tr>
                                    <td style="width: 50%;">
                                        <div class="s-hdr">FROM (SHIPPER / 송하인)</div>
                                        <b>상호:</b> {shipper_n}<br>
                                        <b>주소:</b> {shipper_addr}<br>
                                        <b>연락처:</b> {shipper_tel}
                                    </td>
                                    <td style="width: 50%;">
                                        <div class="s-hdr">TO (CONSIGNEE / 수하인)</div>
                                        <b>수하인:</b> <span style="color: #1e3a8a; font-weight: bold;">{consignee_n}</span><br><b>주소:</b> {consignee_addr}<br><b>연락처:</b> {consignee_tel}<br>
                                        <b>도착 국가:</b> {dest_c}<br>
                                        <b>출발지:</b> {origin_p}
                                    </td>
                                </tr>
                            </table>

                            <table class="t-tbl">
                                <tr>
                                    <td style="width: 33%;">
                                        <div style="font-weight: bold; font-size: 8pt; color: #0f172a;">CARRIER</div>
                                        {air_c} AIR &nbsp; {sea_c} SEA<br><span style="font-size: 7.5pt; color: #64748b;">{transport_t}</span>
                                    </td>
                                    <td style="width: 33%;">
                                        <div style="font-weight: bold; font-size: 8pt; color: #0f172a;">SERVICE</div>
                                        {d2d_c} Door To Door
                                    </td>
                                    <td style="width: 34%;">
                                        <div style="font-weight: bold; font-size: 8pt; color: #0f172a;">SCHEDULE</div>
                                        선적일: <b>{ship_date}</b>
                                    </td>
                                </tr>
                            </table>

                            <table class="t-tbl">
                                <tr>
                                    <td style="width: 60%;">
                                        <div class="s-hdr">DESCRIPTION OF CONTENTS</div>
                                        <div style="font-size: 10pt; font-weight: bold; color: #1e3a8a;">{item_name}</div>
                                        <div style="font-size: 8pt; color: #475569;">
                                            • 박스수: <b>{box_cnt}</b><br>
                                            • 규격: {vol_spec} ({cbm_val})
                                        </div>
                                    </td>
                                    <td style="width: 40%;">
                                        <div class="s-hdr">WEIGHT</div>
                                        청구중량: <b style="color: #dc2626;">{sales_cw} KG</b><br>
                                        박스수: <b>{box_cnt}</b>
                                    </td>
                                </tr>
                            </table>

                            <table style="width: 100%; margin-top: 8px; border-collapse: collapse;">
                                <tr>
                                    <td style="border: 1px solid #64748b; padding: 6px; width: 50%; font-size: 7.5pt;">
                                        ISSUED BY<br><b>(주)범운해운항공 대표이사 이상복</b>
                                    </td>
                                    <td style="border: 1px solid #64748b; padding: 6px; width: 50%; text-align: right; font-size: 7.5pt;">
                                        STAMP<br><b>[직인생략]</b>
                                    </td>
                                </tr>
                            </table>
                        </div>
                    </body>
                    </html>
                    """
          components.html(mobile_awb_html, height=650, scrolling=False)
  st.stop()


# ==========================================
# [B] 사장님 전용 관리자 프로그램 화면
# ==========================================
sidebar_logo_html = ""
if encoded_sidebar_logo:
  sidebar_logo_html = f"<img src='data:image/png;base64,{encoded_sidebar_logo}' style='height: 28px; width: auto;'>"

st.sidebar.markdown(
    f"""
    <div style='display: flex; flex-direction: column; align-items: flex-start; margin-bottom: 5px;'>
        <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 3px;'>
            {sidebar_logo_html}
            <span style='font-size: 17px; font-weight: 800; color: #1e293b;'>(주)범운해운항공</span>
        </div>
        <div style='font-size: 11.5px; font-weight: 700; color: #475569; letter-spacing: 0.2px; margin-left: 36px;'>BUMWOON OCEAN & AIR CO., LTD.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

current_user_id = st.session_state.logged_in_user
current_user_info = st.session_state.user_db.get(
    current_user_id, {"name": "관리자", "role": "관리자(대표)"}
)
current_user_name = current_user_info.get("name", "관리자")

st.sidebar.info(
    f"현재 접속자: **{current_user_name}**님\n\n(권한: {st.session_state.user_role})"
)

col_sb1, col_sb2 = st.sidebar.columns(2)
with col_sb1:
  if st.button("🚪 고객 추적화면", use_container_width=True):
    st.query_params.clear()
    st.rerun()
with col_sb2:
  if st.button("로그아웃", use_container_width=True):
    st.session_state.logged_in_user = None
    st.session_state.user_role = None
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")

# ==========================================
# 💾 최종 통합 데이터 백업 및 일괄 복원 시스템
# ==========================================
st.sidebar.subheader("💾 전체 데이터 통합 백업 및 복원")


def generate_integrated_backup_bytes():
    """B/L 및 모든 관리 자료를 하나의 엑셀 통합 백업 파일로 생성합니다."""
    bl_data = st.session_state.get("bl_data_list", [])
    client_list = st.session_state.get("client_list", [])
    client_rates = st.session_state.get("client_rates", {})
    client_infos = st.session_state.get("client_infos", {})
    supplier_list = st.session_state.get("supplier_list", [])
    supplier_rates = st.session_state.get("supplier_rates", {})
    supplier_infos = st.session_state.get("supplier_infos", {})

    # 일계표 화면이 실제로 사용하는 cashbook_list를 백업합니다.
    ledger_data = st.session_state.get("cashbook_list")
    if ledger_data is None:
        ledger_data = load_account_data()
    expense_data = st.session_state.get("expense_data_list", [])
    meeting_data = st.session_state.get("meeting_data_list", [])
    note_data = st.session_state.get("note_data_list", [])
    customer_accounts = _customer_accounts()
    customer_requests = _customer_requests()
    customer_history = _read_customer_csv(CUSTOMER_HISTORY_FILE)

    meta_dict = {
        "backup_version": 2,
        "client_list": client_list,
        "client_rates": client_rates,
        "client_infos": client_infos,
        "supplier_list": supplier_list,
        "supplier_rates": supplier_rates,
        "supplier_infos": supplier_infos,
        "ledger_data": ledger_data or [],
        "expense_data": expense_data or [],
        "meeting_data": meeting_data or [],
        "note_data": note_data or [],
        "customer_accounts": customer_accounts or [],
        "customer_requests": customer_requests or [],
        "customer_history": customer_history or [],
    }

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # B/L 데이터
        pd.DataFrame(bl_data).to_excel(
            writer, index=False, sheet_name="B_L데이터"
        ) if bl_data else pd.DataFrame(
            columns=["B/L 번호"]
        ).to_excel(writer, index=False, sheet_name="B_L데이터")

        # 일계표를 별도 시트에도 명시적으로 저장합니다.
        pd.DataFrame(ledger_data or []).to_excel(
            writer, index=False, sheet_name="일계표_입출금장부"
        )
        pd.DataFrame(expense_data or []).to_excel(
            writer, index=False, sheet_name="경비_지출내역"
        )
        pd.DataFrame(meeting_data or []).to_excel(
            writer, index=False, sheet_name="거래처미팅노트"
        )
        pd.DataFrame(note_data or []).to_excel(
            writer, index=False, sheet_name="업무용일지"
        )
        pd.DataFrame(customer_accounts or []).to_excel(
            writer, index=False, sheet_name="고객사계정"
        )
        pd.DataFrame(customer_requests or []).to_excel(
            writer, index=False, sheet_name="고객화물접수"
        )
        pd.DataFrame(customer_history or []).to_excel(
            writer, index=False, sheet_name="고객수정이력"
        )

        # 매출 거래처 목록/기본정보를 별도 시트로도 저장합니다.
        client_info_rows = []
        client_rate_rows = []
        for client in client_list or []:
            info = client_infos.get(client, {}) if isinstance(client_infos, dict) else {}
            info = info if isinstance(info, dict) else {}
            client_info_rows.append({
                "거래처명": client,
                "사업자등록번호": info.get("사업자등록번호", ""),
                "이메일": info.get("이메일", ""),
                "담당자": info.get("담당자", ""),
                "전화번호": info.get("전화번호", ""),
                "주소": info.get("주소", ""),
            })
            country_dict = client_rates.get(client, {}) if isinstance(client_rates, dict) else {}
            if isinstance(country_dict, dict):
                for country, trans_dict in country_dict.items():
                    if not isinstance(trans_dict, dict):
                        continue
                    for transport, item_dict in trans_dict.items():
                        if not isinstance(item_dict, dict):
                            continue
                        for item_name, rate in item_dict.items():
                            rate = rate if isinstance(rate, dict) else {}
                            client_rate_rows.append({
                                "거래처명": client,
                                "국가": country,
                                "운송형태": transport,
                                "품명": item_name,
                                "기본중량": rate.get("기본중량", 1.0),
                                "기본요금": rate.get("기본요금", 38000),
                                "추가단가": rate.get("추가단가", 25000),
                                "1CBM당단가": rate.get("1CBM당단가", 3700000),
                            })

        pd.DataFrame(client_info_rows, columns=[
            "거래처명", "사업자등록번호", "이메일", "담당자", "전화번호", "주소"
        ]).to_excel(writer, index=False, sheet_name="매출거래처목록")
        pd.DataFrame(client_rate_rows, columns=[
            "거래처명", "국가", "운송형태", "품명", "기본중량",
            "기본요금", "추가단가", "1CBM당단가"
        ]).to_excel(writer, index=False, sheet_name="매출거래처요율")

        # 기존 거래처/요율 구조 등은 메타 시트에도 보관해 이전 버전과 호환합니다.
        pd.DataFrame([{
            "SYSTEM_META": json.dumps(meta_dict, ensure_ascii=False)
        }]).to_excel(writer, index=False, sheet_name="시스템설정")

    return output.getvalue()


integrated_excel_bytes = generate_integrated_backup_bytes()
st.sidebar.download_button(
    label="📥 전체 데이터 통합 백업 다운로드 (.xlsx)",
    data=integrated_excel_bytes,
    file_name=f"범운해운항공_전체데이터_통합백업_{date.today()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)

st.sidebar.markdown("---")

uploaded_integrated_file = st.sidebar.file_uploader(
    "📤 통합 백업파일 일괄 복원 업로드 (.xlsx)",
    type=["xlsx", "xls", "csv"],
    help="B/L, 거래처/요율, 일계표 입출금 장부, 경비, 미팅 노트 및 업무일지를 함께 복원합니다.",
    key="integrated_backup_uploader",
)

if uploaded_integrated_file is not None:
    try:
        file_extension = uploaded_integrated_file.name.rsplit(".", 1)[-1].lower()
        parsed_meta = {}
        sheets = {}

        if file_extension == "csv":
            sheets["CSV"] = pd.read_csv(uploaded_integrated_file)
        else:
            xls = pd.ExcelFile(uploaded_integrated_file)
            for sheet_name in xls.sheet_names:
                sheets[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name)

        # 시스템 메타데이터 읽기
        for df_meta in sheets.values():
            if "SYSTEM_META" in df_meta.columns and not df_meta.empty:
                meta_val = df_meta["SYSTEM_META"].iloc[0]
                if pd.notna(meta_val) and str(meta_val).strip():
                    try:
                        parsed_meta = json.loads(str(meta_val))
                        break
                    except Exception:
                        pass

        # 거래처 및 기본 정보 복원
        if parsed_meta:
            meta_clients = parsed_meta.get("client_list", []) or []
            meta_rates = parsed_meta.get("client_rates", {}) or {}
            meta_infos = parsed_meta.get("client_infos", {}) or {}
            st.session_state.client_list = list(dict.fromkeys(
                _client_text(v) for v in meta_clients if _client_text(v)
            ))
            st.session_state.client_rates = meta_rates if isinstance(meta_rates, dict) else {}
            st.session_state.client_infos = meta_infos if isinstance(meta_infos, dict) else {}
            st.session_state.supplier_list = parsed_meta.get("supplier_list", st.session_state.get("supplier_list", [])) or []
            st.session_state.supplier_rates = parsed_meta.get("supplier_rates", st.session_state.get("supplier_rates", {})) or {}
            st.session_state.supplier_infos = parsed_meta.get("supplier_infos", st.session_state.get("supplier_infos", {})) or {}

        # 새 백업 형식의 거래처 전용 시트가 있으면 해당 시트를 우선 사용합니다.
        # 이전 백업 파일은 시스템설정의 메타데이터를 그대로 사용합니다.
        if "매출거래처목록" in sheets:
            info_df = sheets["매출거래처목록"].copy()
            if "거래처명" in info_df.columns:
                restored_clients = []
                restored_infos = {}
                for _, row in info_df.iterrows():
                    client = _client_text(row.get("거래처명", ""))
                    if not client:
                        continue
                    if client not in restored_clients:
                        restored_clients.append(client)
                    restored_infos[client] = {
                        "사업자등록번호": _client_text(row.get("사업자등록번호", "")),
                        "이메일": _client_text(row.get("이메일", "")),
                        "담당자": _client_text(row.get("담당자", "")),
                        "전화번호": _client_text(row.get("전화번호", "")),
                        "주소": _client_text(row.get("주소", "")),
                    }
                if restored_clients:
                    st.session_state.client_list = restored_clients
                    st.session_state.client_infos = restored_infos

        if "매출거래처요율" in sheets:
            rate_df = sheets["매출거래처요율"].copy()
            restored_rates = {client: {} for client in st.session_state.get("client_list", [])}
            for _, row in rate_df.iterrows():
                client = _client_text(row.get("거래처명", ""))
                if not client:
                    continue
                if client not in st.session_state.client_list:
                    st.session_state.client_list.append(client)
                country = _client_text(row.get("국가", "미국"), "미국")
                transport = _client_text(row.get("운송형태", "항공(Air)"), "항공(Air)")
                item = _client_text(row.get("품명", "일반공산품"), "일반공산품")
                restored_rates.setdefault(client, {}).setdefault(country, {}).setdefault(transport, {})[item] = {
                    "기본중량": _client_safe_number(row.get("기본중량", 1.0), 1.0),
                    "기본요금": _client_safe_number(row.get("기본요금", 38000), 38000, as_int=True),
                    "추가단가": _client_safe_number(row.get("추가단가", 25000), 25000, as_int=True),
                    "1CBM당단가": _client_safe_number(row.get("1CBM당단가", 3700000), 3700000, as_int=True),
                }
            if restored_rates:
                st.session_state.client_rates = restored_rates

        # 1. 일계표(입출금장부) 복원: 엑셀 시트 실데이터 최우선 적용
        ledger_restored = False
        for sheet_name in ("일계표_입출금장부", "일계표", "입출금장부", "계정장부"):
            if sheet_name in sheets:
                df_ledger = sheets[sheet_name].copy()
                df_ledger = df_ledger.drop(columns=["SYSTEM_META"], errors="ignore")
                if not df_ledger.empty:
                    st.session_state.cashbook_list = df_ledger.fillna("").to_dict("records")
                    ledger_restored = True
                    break

        if not ledger_restored and "ledger_data" in parsed_meta:
            st.session_state.cashbook_list = parsed_meta.get("ledger_data") or []
            ledger_restored = True

        if ledger_restored:
            save_account_data(st.session_state.cashbook_list)

        # 2. 경비 지출 내역 복원
        if "경비_지출내역" in sheets and not sheets["경비_지출내역"].empty:
            st.session_state.expense_data_list = sheets["경비_지출내역"].fillna("").to_dict("records")
        elif "expense_data" in parsed_meta:
            st.session_state.expense_data_list = parsed_meta.get("expense_data") or []
        if "expense_data_list" in st.session_state:
            save_expense_data(st.session_state.expense_data_list)

        # 3. B/L 데이터 복원 (54건)
        bl_df = None
        for sheet_name in ("B_L데이터", "Bumwoon_Integrated_Backup", "BL_Data", "BL_History"):
            if sheet_name in sheets and "B/L 번호" in sheets[sheet_name].columns:
                bl_df = sheets[sheet_name].copy()
                break
        if bl_df is None:
            for df_candidate in sheets.values():
                if "B/L 번호" in df_candidate.columns:
                    bl_df = df_candidate.copy()
                    break

        if bl_df is not None:
            bl_df = bl_df.drop(columns=["SYSTEM_META"], errors="ignore")
            bl_df = bl_df[bl_df["B/L 번호"].notna()]
            st.session_state.bl_data_list = bl_df.fillna("").to_dict("records")
            save_bl_data(st.session_state.bl_data_list)

        # 고객사 계정 / 접수 내역 / 수정 이력 복원 (새 시트가 있는 경우에만 기존 파일을 갱신)
        customer_sheet_map = {
            "고객사계정": CUSTOMER_ACCOUNT_FILE,
            "고객화물접수": CUSTOMER_REQUEST_FILE,
            "고객수정이력": CUSTOMER_HISTORY_FILE,
        }
        for customer_sheet, customer_path in customer_sheet_map.items():
            if customer_sheet in sheets:
                customer_df = sheets[customer_sheet].copy().drop(columns=["SYSTEM_META"], errors="ignore")
                _write_customer_csv(customer_path, customer_df.fillna("").to_dict("records"))
        if parsed_meta:
            if "customer_accounts" in parsed_meta:
                _write_customer_csv(CUSTOMER_ACCOUNT_FILE, parsed_meta.get("customer_accounts") or [])
            if "customer_requests" in parsed_meta:
                _write_customer_csv(CUSTOMER_REQUEST_FILE, parsed_meta.get("customer_requests") or [])
            if "customer_history" in parsed_meta:
                _write_customer_csv(CUSTOMER_HISTORY_FILE, parsed_meta.get("customer_history") or [])

        # 거래처 데이터 동기화 저장
        if parsed_meta:
            save_client_data(st.session_state.client_list, st.session_state.client_rates, st.session_state.client_infos)
            save_supplier_data(st.session_state.supplier_list, st.session_state.supplier_rates, st.session_state.supplier_infos)

        st.sidebar.success(
            f"🎉 복원 완료! B/L: {len(st.session_state.get('bl_data_list', []))}건, 일계표: {len(st.session_state.get('cashbook_list', []))}건"
        )
        st.rerun()

    except Exception as e:
        st.sidebar.error(f"❌ 복원 중 오류 발생: {e}")

# ==========================================
# 사이드바 메인 메뉴 (매출/매입 거래처 완전 독립 분리)
# ==========================================
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
  menu_options.append("🏢 고객사 계정 및 화물 접수 관리")
  menu_options.append("🔑 직원 계정 관리 (대표님 전용)")

selected_menu = st.sidebar.radio("📌 메인 메뉴 이동", menu_options, key="main_menu_radio")

st.sidebar.markdown("---")
mobile_view_mode = st.sidebar.toggle(
    "📱 스마트폰 화면 최적화 모드",
    value=False,
    help="스마트폰 화면 크기에 맞춰 글자와 여백이 컴팩트하게 조정됩니다.",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🌐 고객 보안 추적 링크 안내")
st.sidebar.markdown(
    "고객들에게 아래 주소를 안내해주시면 실시간 조회가 가능합니다:<br>`https://logics-app-v6nichbmhtvezr8ia7cnii.streamlit.app/`",
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 사내 실시간 화물 추적")
if "recent_track_list" not in st.session_state:
  st.session_state.recent_track_list = []
tracking_no_input = st.sidebar.text_input(
    "운송장 / B/L 번호 입력", value="", key="sidebar_tracking_no"
)
if tracking_no_input and tracking_no_input.strip():
  clean_tno = tracking_no_input.strip()
  if clean_tno not in st.session_state.recent_track_list:
    st.session_state.recent_track_list.insert(0, clean_tno)
    if len(st.session_state.recent_track_list) > 5:
      st.session_state.recent_track_list.pop()

ups_url = (
    f"https://www.ups.com/track?loc=ko_KR&tracknum={tracking_no_input}"
    if tracking_no_input
    else "https://www.ups.com/track?loc=ko_KR"
)
st.sidebar.markdown(
    f"<a href='{ups_url}' target='_blank' style='display: block; text-align:"
    " center; background-color: #ffb500; color: #000; padding: 8px 12px;"
    " border-radius: 6px; font-weight: bold; text-decoration: none; margin-bottom:"
    " 6px;'>📦 UPS 화물 조회하기</a>",
    unsafe_allow_html=True,
)

track17_url = (
    f"https://t.17track.net/ko#nums={tracking_no_input}"
    if tracking_no_input
    else "https://t.17track.net/ko"
)
st.sidebar.markdown(
    f"<a href='{track17_url}' target='_blank' style='display: block; text-align:"
    " center; background-color: #2563eb; color: #fff; padding: 8px 12px;"
    " border-radius: 6px; font-weight: bold; text-decoration: none; margin-bottom:"
    " 10px;'>🌐 17TRACK 화물 조회하기</a>",
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧮 간이 단위 환산기")
calc_tab1, calc_tab2 = st.sidebar.tabs(["부피중량(5k/6k)", "중량(kg↔lb)"])
with calc_tab1:
  sc_w = st.text_input("가로 (cm)", value="0", key="sc_w")
  sc_l = st.text_input("세로 (cm)", value="0", key="sc_l")
  sc_h = st.text_input("높이 (cm)", value="0", key="sc_h")
  try:
    val_w, val_l, val_h = (
        float(sc_w) if sc_w else 0.0,
        float(sc_l) if sc_l else 0.0,
        float(sc_h) if sc_h else 0.0,
    )
  except ValueError:
    val_w, val_l, val_h = 0.0, 0.0, 0.0
  if val_w > 0 and val_l > 0 and val_h > 0:
    cbm_val = (val_w * val_l * val_h) / 1000000.0
    vol_wt_5k = (val_w * val_l * val_h) / 5000.0
    st.sidebar.markdown(
        f"• CBM: <b>{cbm_val:.3f}</b> | 5k: <b>{vol_wt_5k:.1f}kg</b>",
        unsafe_allow_html=True,
    )

with calc_tab2:
  if "widget_kg" not in st.session_state:
    st.session_state.widget_kg = "0"
  if "widget_lb" not in st.session_state:
    st.session_state.widget_lb = "0.00"


  def update_kg():
    try:
      val = float(st.session_state.widget_kg or 0)
      st.session_state.widget_lb = f"{val * 2.20462:.2f}"
    except:
      pass


  def update_lb():
    try:
      val = float(st.session_state.widget_lb or 0)
      st.session_state.widget_kg = f"{val / 2.20462:.2f}"
    except:
      pass

  st.sidebar.text_input(
      "킬로그램 (kg)", key="widget_kg", on_change=update_kg, placeholder="0"
  )
  st.sidebar.text_input(
      "파운드 (lb)", key="widget_lb", on_change=update_lb, placeholder="0.00"
  )

st.sidebar.markdown("---")
st.sidebar.markdown("### 💰 간이 미수·미지급 확인")
sidebar_clients = (
    st.session_state.client_list if st.session_state.client_list else ["없음"]
)
selected_side_client = st.sidebar.selectbox(
    "조회할 거래처 선택", options=sidebar_clients, key="side_client_select"
)
if selected_side_client and selected_side_client != "없음":
  side_bl_list = st.session_state.bl_data_list
  client_unpaid = sum(
      j.get("매출액(원)", 0)
      for j in side_bl_list
      if j.get("화주명(매출)") == selected_side_client
      and str(j.get("수금상태", "미수")) != "수금완료"
  )
  client_total_sales = sum(
      j.get("매출액(원)", 0)
      for j in side_bl_list
      if j.get("화주명(매출)") == selected_side_client
  )
  client_total_purchase = sum(
      j.get("매입액(원)", 0)
      for j in side_bl_list
      if j.get("매입처") == selected_side_client
  )
  st.sidebar.markdown(
      f"""
    <div style='background-color: #1e293b; padding: 10px; border-radius: 6px; color: #fff; font-size: 11.5px; line-height: 1.5;'>
        <b>📌 [{selected_side_client}] 자금 현황</b><br>
        • 총 매출(청구): <b>{client_total_sales:,} 원</b><br>
        • 미수금 잔액: <span style='color: #f87171;'><b>{client_unpaid:,} 원</b></span><br>
        <hr style='border: 0.5px solid #475569; margin: 6px 0;'>
        • 총 매입(비용): <b>{client_total_purchase:,} 원</b>
    </div>
    """,
      unsafe_allow_html=True,
  )

st.sidebar.markdown("---")

font_size_val = "12px" if mobile_view_mode else "13.5px"
container_padding = "0.5rem" if mobile_view_mode else "1.5rem"
st.markdown(
    f"""
<style>
    html, body, [class*="css"] {{
        font-size: {font_size_val} !important;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        color: #1e293b;
    }}
    .stApp {{
        background-color: #f8fafc;
    }}
    input, select, textarea {{
        font-size: {font_size_val} !important;
        border-radius: 6px !important;
    }}
    .block-container {{
        padding-top: {container_padding};
        padding-bottom: 3rem;
        max-width: 1400px;
    }}
</style>
""",
    unsafe_allow_html=True,
)

COUNTRY_LIST = [
    "미국",
    "중국",
    "호주",
    "태국",
    "인도",
    "멕시코",
    "홍콩",
    "베트남",
    "기타 국가",
]
EXPENSE_CATEGORIES = [
    "주유비 (차량유지비)",
    "식대 (복리후생비)",
    "접대비",
    "소모품비",
    "통신비",
    "공과금",
    "기타 잡비",
]
INCOME_CATEGORIES = [
    "화물운임 현금수금",
    "화물운임 통장입금",
    "미수금 회수",
    "기타 영업수입",
]

logo_html_str = ""
if encoded_sidebar_logo:
  logo_html_str = f"<img src='data:image/png;base64,{encoded_sidebar_logo}' style='height: 48px; width: auto; margin-right: 15px; border-radius: 6px;'>"

header_html = f"""
<div style='background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); padding: 20px 24px; border-radius: 12px; color: white; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);'>
    <div style='display: flex; align-items: center;'>
        {logo_html_str}
        <div>
            <h1 style='color: #ffffff; margin: 0; font-size: 21px; font-weight: 800; letter-spacing: -0.5px;'>🚢 (주)범운해운항공 종합 관리 프로그램</h1>
            <p style='margin: 4px 0 0 0; color: #93c5fd; font-size: 12px;'>Job별 Profit 정산, 거래처별 요율 관리 및 스마트 인보이스 발행 시스템</p>
        </div>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# [1] 수출입 B/L 등록
# ==========================================
if selected_menu == "📊 수출입 B/L 등록":
    approved_customer_requests = [r for r in _customer_requests() if r.get("상태", "") == "승인완료-B/L 등록대기" and str(r.get("연결 B/L 번호", "")).strip()]
    if approved_customer_requests:
        st.markdown("### 📦 승인된 고객사 화물에서 B/L 등록")
        approved_labels = [f"{r.get('접수번호','')} | {r.get('고객사상호','')} | {r.get('화주상호','')} | B/L {r.get('연결 B/L 번호','')}" for r in approved_customer_requests]
        default_req_id = st.session_state.get("customer_bl_registration_request", "")
        default_idx = next((i for i, r in enumerate(approved_customer_requests) if r.get("접수번호", "") == default_req_id), 0)
        selected_approved_label = st.selectbox("승인 접수 선택", approved_labels, index=default_idx, key="approved_customer_bl_select")
        selected_approved_req = approved_customer_requests[approved_labels.index(selected_approved_label)]
        st.caption(f"도착 국가: {selected_approved_req.get('도착국가','')} · 품목: {selected_approved_req.get('품목','')} · 중량: {selected_approved_req.get('실제중량kg','')} kg · 박스: {selected_approved_req.get('박스수량','')}")
        st.info("승인 전 수정은 고객사 계정 및 화물 접수 관리 화면에서 가능합니다. 아래 버튼을 누르면 승인 자료를 수출입 B/L 내역에 등록합니다. 매출·매입 금액은 자동 요율로 계산되며, 등록 후 B/L 수정 화면에서 조정할 수 있습니다.")
        if st.button("➡️ 선택한 승인 접수를 수출입 B/L에 등록", type="primary", use_container_width=True, key="register_approved_customer_bl"):
            req = selected_approved_req
            blno = str(req.get("연결 B/L 번호", "")).strip()
            if any(str(x.get("B/L 번호", "")).strip() == blno for x in st.session_state.bl_data_list):
                st.error(f"B/L 번호 {blno}는 이미 등록되어 있습니다. 중복 등록하지 않았습니다.")
            else:
                job_nums = []
                for x in st.session_state.bl_data_list:
                    j = str(x.get("Job 번호", ""))
                    try:
                        job_nums.append(int(j.split("-")[-1]))
                    except Exception:
                        pass
                job_no_auto = f"BW-{date.today().year}-{(max(job_nums) if job_nums else 0)+1:03d}"
                shipper_auto = str(req.get("화주상호", "")).strip()
                country_auto = str(req.get("도착국가", "미국")).strip()
                item_auto = str(req.get("품목", "기타")).strip()
                transport_auto = str(req.get("운송형태", "항공(Air)")).strip()
                weight_auto = float(req.get("실제중량kg", 0) or 0)
                width_auto = float(req.get("가로cm", 0) or 0)
                length_auto = float(req.get("세로cm", 0) or 0)
                height_auto = float(req.get("높이cm", 0) or 0)
                cartons_auto = int(float(req.get("박스수량", 1) or 1))
                cbm_auto = width_auto * length_auto * height_auto * cartons_auto / 1000000.0
                divisor_auto = 5000 if transport_auto == "항공(Air)" else 6000
                charge_auto = float(math.ceil(max(weight_auto, width_autolength_autoheight_auto*cartons_auto/divisor_auto)))
                supplier_auto = ""
                sales_auto = int(calculate_auto_price(shipper_auto, charge_auto, transport_auto, item_auto, country_auto))
                purchase_auto = int(calculate_purchase_auto_price(supplier_auto, charge_auto, transport_auto, item_auto, country_auto))
                st.session_state.bl_data_list.append({
                    "구분":"수출 (Export)", "날짜":str(date.today()), "Job 번호":job_no_auto, "B/L 번호":blno,
                    "국가":country_auto, "출발지":"대한민국 (KOREA)", "화주명(매출)":shipper_auto,
                    "해외수하인":req.get("해외수하인", ""), "해외수하인주소":req.get("해외수하인주소", ""), "해외수하인전화번호":req.get("해외수하인전화번호", ""),
                    "매입처":supplier_auto, "운송형태":transport_auto, "서비스옵션":"Door To Door", "품목":item_auto,
                    "박스수":f"{cartons_auto} 박스 (CTN)", "부피규격":f"{width_auto:g}×{length_auto:g}×{height_auto:g}cm({cartons_auto}CTN)",
                    "실중량(kg)":weight_auto, "매출실중량(kg)":weight_auto, "매입실중량(kg)":weight_auto,
                    "매출청구중량(kg)":charge_auto, "매입청구중량(kg)":charge_auto, "CBM":f"{cbm_auto:.3f} CBM",
                    "현재 상태":"📦 물류센터 입고 및 접수 완료", "수금상태":"미수", "매출액(원)":sales_auto, "매입액(원)":purchase_auto,
                    "예상Profit(원)":sales_auto-purchase_auto, "비고":f"고객사 접수번호: {req.get('접수번호','')} / {req.get('추가요청','')}",
                    "최종작성자":st.session_state.get("logged_in_user", "관리자"), "최종수정자":"-"
                })
                save_bl_data(st.session_state.bl_data_list)
                all_reqs = _customer_requests()
                for rr in all_reqs:
                    if rr.get("접수번호", "") == req.get("접수번호", ""):
                        rr["상태"] = "B/L 등록"
                        rr["B/L등록일시"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        break
                _write_customer_csv(CUSTOMER_REQUEST_FILE, all_reqs)
                _customer_history_append({"일시":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"접수번호":req.get("접수번호", ""),"고객사아이디":req.get("고객사아이디", ""),"작업자":st.session_state.get("logged_in_user", "관리자"),"작업":"승인 고객 접수에서 B/L 등록","변경내용":blno})
                st.session_state.pop("customer_bl_registration_request", None)
                st.success(f"B/L 등록 완료: {blno} / Job 번호: {job_no_auto}")
                st.rerun()
        st.markdown("---")
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 15px;'>📋 수출입 B/L 및 Profit 등록 관리</h3>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "##### 📦 박스 규격 및 카톤수 입력 (아래 입력창에 가로, 세로, 높이, 카톤수를 적어주시면 즉시 부피중량과 CBM이 계산됩니다)"
    )

    def _box_input_number(value, default=0.0):
        try:
            if value is None or pd.isna(value) or str(value).strip() == "":
                return default
            return float(value)
        except (TypeError, ValueError, OverflowError):
            return default

    # 배포된 이전 코드에서 밑줄 없는 함수명을 호출하더라도 NameError가 나지 않도록 호환 별칭 제공
    box_input_number = _box_input_number

    if "box_input_df" not in st.session_state:
        st.session_state.box_input_df = pd.DataFrame([
            {"가로(cm)": 100.0, "세로(cm)": 100.0, "높이(cm)": 100.0, "카톤수(개)": 1}
        ])

    # st.data_editor는 셀을 먼저 선택한 뒤 편집해야 하는 경우가 있어
    # 가로/세로/높이를 두 번 눌러야 입력되는 것처럼 느껴질 수 있습니다.
    # 일반 number_input으로 바꿔 한 번 클릭해 바로 입력하고, 입력 즉시 재계산되게 합니다.
    box_df = st.session_state.box_input_df.copy().reset_index(drop=True)
    action_add, action_remove, action_help = st.columns([1, 1, 3])
    with action_add:
        if st.button("➕ 규격 행 추가", key="add_box_dimension_row"):
            box_df.loc[len(box_df)] = {"가로(cm)": 100.0, "세로(cm)": 100.0, "높이(cm)": 100.0, "카톤수(개)": 1}
            st.session_state.box_input_df = box_df
            st.rerun()
    with action_remove:
        if st.button("➖ 마지막 행 삭제", key="remove_box_dimension_row", disabled=len(box_df) <= 1):
            removed_index = len(box_df) - 1
            for suffix in ("width", "length", "height", "cartons"):
                st.session_state.pop(f"box_dimension_{suffix}_{removed_index}", None)
            box_df = box_df.iloc[:-1].reset_index(drop=True)
            st.session_state.box_input_df = box_df
            st.rerun()
    with action_help:
        st.caption("각 규격 입력칸을 한 번 클릭해 입력하세요. 값이 바뀌면 CBM·부피중량이 자동 계산됩니다.")

    edited_rows = []
    for box_i, box_row in box_df.iterrows():
        dim_cols = st.columns(4)
        with dim_cols[0]:
            box_w_value = st.number_input(
                f"가로(cm) · 행 {box_i + 1}", min_value=0.0,
                value=float(box_input_number(box_row.get("가로(cm)", 100.0), 100.0)),
                step=0.5, format="%.1f", key=f"box_dimension_width{box_i}"
            )
        with dim_cols[1]:
            box_l_value = st.number_input(
                f"세로(cm) · 행 {box_i + 1}", min_value=0.0,
                value=float(box_input_number(box_row.get("세로(cm)", 100.0), 100.0)),
                step=0.5, format="%.1f", key=f"box_dimension_length{box_i}"
            )
        with dim_cols[2]:
            box_h_value = st.number_input(
                f"높이(cm) · 행 {box_i + 1}", min_value=0.0,
                value=float(box_input_number(box_row.get("높이(cm)", 100.0), 100.0)),
                step=0.5, format="%.1f", key=f"box_dimension_height{box_i}"
            )
        with dim_cols[3]:
            box_ctn_value = st.number_input(
                f"카톤수(개) · 행 {box_i + 1}", min_value=0,
                value=max(0, int(box_input_number(box_row.get("카톤수(개)", 1), 1))),
                step=1, key=f"box_dimension_cartons{box_i}"
            )
        edited_rows.append({
            "가로(cm)": float(box_w_value),
            "세로(cm)": float(box_l_value),
            "높이(cm)": float(box_h_value),
            "카톤수(개)": int(box_ctn_value),
        })

    edited_box_df = pd.DataFrame(edited_rows, columns=["가로(cm)", "세로(cm)", "높이(cm)", "카톤수(개)"])
    # 다음 Streamlit 재실행에도 현재 입력값을 유지합니다.
    st.session_state.box_input_df = edited_box_df.copy()

    def _safe_box_number(value, default=0.0):
        """Convert editable grid values safely; blank/invalid values become default."""
        try:
            if value is None or pd.isna(value) or str(value).strip() == "":
                return default
            return float(value)
        except (TypeError, ValueError, OverflowError):
            return default

    box_col1, box_col2 = st.columns([1.3, 1])
    with box_col1:
        common_gw_str = st.text_input(
            "실 중량 (kg)", value="1.15", placeholder="실중량", key="common_gw"
        )
    with box_col2:
        sub_d1_col, sub_d2_col = st.columns(2)
        with sub_d1_col:
            s_div = st.selectbox("매출 부피기준", [5000, 6000], key="s_div")
        with sub_d2_col:
            p_div = st.selectbox("매입 부피기준", [6000, 5000], key="p_div")

    total_cbm = 0.0
    total_ctn = 0
    total_vol_wt_sales = 0.0
    total_vol_wt_purchase = 0.0
    vol_str_list = []

    try:
        gw = float(common_gw_str) if common_gw_str else 0.0
    except ValueError:
        gw = 0.0

    for _, row in edited_box_df.iterrows():
        w = _safe_box_number(row.get("가로(cm)", 0))
        l = _safe_box_number(row.get("세로(cm)", 0))
        h = _safe_box_number(row.get("높이(cm)", 0))
        # Carton count is an integer quantity, while dimensions may be decimal (e.g. 51.5 cm).
        ctn_value = _safe_box_number(row.get("카톤수(개)", 0))
        ctn = max(0, int(ctn_value)) if ctn_value >= 0 else 0

        if w > 0 and l > 0 and h > 0 and ctn > 0:
            box_cbm = ((w * l * h) / 1000000.0) * ctn
            total_cbm += box_cbm
            total_ctn += ctn

            box_vol_sales = ((w * l * h) / s_div) * ctn
            box_vol_purchase = ((w * l * h) / p_div) * ctn

            total_vol_wt_sales += box_vol_sales
            total_vol_wt_purchase += box_vol_purchase

            vol_str_list.append(f"{w:g}×{l:g}×{h:g}cm({ctn}CTN)")

    calc_sales_cw = float(math.ceil(max(gw, total_vol_wt_sales)))
    calc_purchase_cw = float(math.ceil(max(gw, total_vol_wt_purchase)))
    volume_str_result = " / ".join(vol_str_list) if vol_str_list else "-"
    piece_count_val = (
        f"{total_ctn} 박스 (CTN)" if total_ctn > 0 else "1 박스 (CTN)"
    )

    st.markdown("---")
    st.markdown("#### 📝 B/L 및 청구 금액 실시간 미리보기")

    form_col1, form_col2 = st.columns(2)
    with form_col1:
        io_type = st.selectbox("수출입 구분", ["수출 (Export)", "수입 (Import)"])

        suggested_job = "BW-2026-003"
        if st.session_state.bl_data_list:
            try:
                last_job = str(
                    st.session_state.bl_data_list[-1].get("Job 번호", "BW-2026-003")
                )
                if "-" in last_job:
                    parts = last_job.split("-")
                    num_part = int(parts[-1]) + 1
                    suggested_job = f"{parts[0]}-{parts[1]}-{num_part:03d}"
            except:
                pass
        job_no = st.text_input(
            "Job 번호 (필수 입력)",
            value=suggested_job,
            placeholder="예: BW-2026-003",
        )

        suggested_bl = "BW260003"
        if st.session_state.bl_data_list:
            last_b = str(
                st.session_state.bl_data_list[-1].get("B/L 번호", "BW260003")
            )
            if last_b.startswith("BW") and len(last_b) >= 8:
                try:
                    suggested_bl = f"BW{int(last_b[2:]) + 1:06d}"
                except:
                    pass
        bl_no = st.text_input("B/L 번호 (운송장 번호)", value=suggested_bl)
        reg_date = st.date_input("선적 날짜", value=date.today())

        col1, col2 = st.columns(2)

        with col1:
            dest_country = st.selectbox("도착 국가", COUNTRY_LIST)
            item_desc = st.selectbox(
                "품목", options=["보톡스", "필러", "화장품", "특가품목", "기타"]
            )
            consignee_name = st.text_input("해외 수하인")
            consignee_addr = st.text_input("해외 수하인 주소", placeholder="예: 123 Main St, New York, NY 10001")
            consignee_tel = st.text_input("해외 수하인 전화번호", placeholder="예: +1-212-555-0199")
            transport_type = st.selectbox(
                "운송 형태", options=["항공(Air)", "해상(LCL)", "에어카고"]
            )
            tracking_status = st.selectbox(
                "현재 진행 상태 선택", options=TRACKING_STATUS_OPTIONS
            )

        with col2:
            origin_place = st.text_input("출발지", value="대한민국 (KOREA)")
            shipper_options = [""] + st.session_state.client_list
            shipper_name = st.selectbox(
                "화주명 (매출처)",
                options=shipper_options,
                index=1 if len(shipper_options) > 1 else 0,
            )
            supplier_options = (
                [""] + st.session_state.supplier_list
                if "supplier_list" in st.session_state
                else [""]
            )
            purchase_vendor = st.selectbox(
                "매입처 (비용처)",
                options=supplier_options,
                index=1 if len(supplier_options) > 1 else 0,
            )
            service_option = st.selectbox("서비스 옵션", ["Door To Door"])
            payment_status_input = st.selectbox(
                "수금 상태", options=["미수", "수금완료"], index=0
            )

        st.markdown("---")

        col3, col4 = st.columns(2)

        with col3:
            st.markdown("#### 📦 화물 및 매출 정보")
            piece_count = st.text_input("총 박스 수 (Piece)", value=piece_count_val)
            
            # 상단 실중량(gw) 값이 즉시 반영되도록 key 제거
            gross_weight_sales_str = st.text_input(
                "매출 실중량(kg)", value=str(gw), placeholder="예: 1.15"
            )
            try:
                gross_weight_sales = float(gross_weight_sales_str)
            except ValueError:
                gross_weight_sales = float(gw)

            default_sales_cw = float(math.ceil(max(gross_weight_sales, total_vol_wt_sales)))
            sales_chargeable_weight = st.number_input(
                "매출 청구중량(kg) [자동 올림 계산]",
                value=default_sales_cw,
                min_value=0.0,
                step=1.0,
            )

            auto_sales_price = calculate_auto_price(
                shipper_name, sales_chargeable_weight, transport_type, item_desc, dest_country
            )
            total_sales = st.number_input(
                "총 매출액 (원) [자동 계산 및 수정 가능]",
                value=int(auto_sales_price),
                min_value=0,
                step=1000,
                format="%d",
            )

        with col4:
            st.markdown("#### 💰 매입 정보")
            volume_dim = st.text_input("부피 규격 (Volume)", value=volume_str_result)
            
            # 상단 실중량(gw) 값이 즉시 반영되도록 key 제거
            gross_weight_purchase_str = st.text_input(
                "매입 실중량(kg)", value=str(gw), placeholder="예: 1.15"
            )
            try:
                gross_weight_purchase = float(gross_weight_purchase_str)
            except ValueError:
                gross_weight_purchase = float(gw)

            default_purchase_cw = float(math.ceil(max(gross_weight_purchase, total_vol_wt_purchase)))
            purchase_chargeable_weight = st.number_input(
                "매입 청구중량(kg) [자동 올림 계산]",
                value=default_purchase_cw,
                min_value=0.0,
                step=1.0,
            )

            auto_purchase_price = calculate_purchase_auto_price(
                purchase_vendor, purchase_chargeable_weight, transport_type, item_desc, dest_country
            )
            total_purchase = st.number_input(
                "총 매입액 (원) [자동 계산 및 수정 가능]",
                value=int(auto_purchase_price),
                min_value=0,
                step=1000,
                format="%d",
            )

        remarks = st.text_area("비고")

        if st.button("💾 B/L 등록 저장", type="primary", use_container_width=True):
            if job_no.strip() and shipper_name.strip():
                preview_profit = int(total_sales) - int(total_purchase)
                st.session_state.bl_data_list.append({
                    "구분": io_type,
                    "날짜": str(reg_date),
                    "Job 번호": job_no,
                    "B/L 번호": bl_no,
                    "국가": dest_country,
                    "출발지": origin_place,
                    "화주명(매출)": shipper_name,
                    "해외수하인": consignee_name,
                    "해외수하인주소": consignee_addr,
                    "해외수하인전화번호": consignee_tel,
                    "매입처": purchase_vendor,
                    "운송형태": transport_type,
                    "서비스옵션": service_option,
                    "품목": item_desc,
                    "박스수": piece_count,
                    "부피규격": volume_dim,
                    "실중량(kg)": float(gross_weight_sales),
                    "매출실중량(kg)": float(gross_weight_sales),
                    "매입실중량(kg)": float(gross_weight_purchase),
                    "매출청구중량(kg)": float(sales_chargeable_weight),
                    "매입청구중량(kg)": float(purchase_chargeable_weight),
                    "CBM": f"{total_cbm:.3f} CBM",
                    "현재 상태": tracking_status,
                    "수금상태": payment_status_input,
                    "매출액(원)": int(total_sales),
                    "매입액(원)": int(total_purchase),
                    "예상Profit(원)": preview_profit,
                    "비고": remarks,
                    "최종작성자": current_user_name,
                    "최종수정자": "-",
                })
                save_bl_data(st.session_state.bl_data_list)

                # 고객 접수 내역과 B/L을 안전하게 연결: 화주/수하인/국가가 일치하는 미연결 접수가 정확히 1건일 때만 자동 연결
                try:
                    customer_reqs = _customer_requests()
                    candidate_indices = [
                        i for i, req in enumerate(customer_reqs)
                        if not str(req.get("연결 B/L 번호", "")).strip()
                        and str(req.get("화주상호", "")).strip().casefold() == str(shipper_name).strip().casefold()
                        and str(req.get("해외수하인", "")).strip().casefold() == str(consignee_name).strip().casefold()
                        and str(req.get("도착국가", "")).strip().casefold() == str(dest_country).strip().casefold()
                    ]
                    if len(candidate_indices) == 1:
                        req = customer_reqs[candidate_indices[0]]
                        req["연결 B/L 번호"] = str(bl_no).strip()
                        req["상태"] = "B/L 등록"
                        _write_customer_csv(CUSTOMER_REQUEST_FILE, customer_reqs)
                        _customer_history_append({
                            "일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "접수번호": req.get("접수번호", ""),
                            "고객사아이디": req.get("고객사아이디", ""),
                            "작업자": current_user_name,
                            "작업": "B/L 등록과 자동 연결",
                            "변경내용": str(bl_no).strip(),
                        })
                        st.info(f"고객 접수 {req.get('접수번호', '')}와 B/L {bl_no}를 자동 연결했습니다.")
                    elif len(candidate_indices) > 1:
                        st.warning("동일한 화주·수하인·국가의 고객 접수가 여러 건입니다. '고객사 계정 및 화물 접수 관리'에서 해당 접수와 B/L 번호를 직접 연결해 주세요.")
                except Exception as link_error:
                    st.warning(f"B/L은 저장됐지만 고객 접수 자동 연결은 완료되지 않았습니다. 고객 접수 관리 메뉴에서 연결해 주세요. ({link_error})")

                st.success(
                    f"🎉 [성공] B/L 및 Job 번호({job_no})가 소수점 실중량({gross_weight_sales}kg) 포함하여 정상 등록되었습니다!"
                )
            else:
                st.warning(
                    "⚠️ [경고] 'Job 번호'와 '화주명'은 반드시 입력하셔야 등록됩니다."
                )

# ==========================================
# [2] 등록 B/L 수정 및 Profit 내역 (검색 및 거래처별 필터 기능 추가 완료)
# ==========================================
elif selected_menu == "📋 등록 B/L 수정 및 Profit 내역":
    st.markdown("<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>📋 등록 B/L 수정 및 Profit 내역</h3>", unsafe_allow_html=True)
    
    if st.session_state.bl_data_list:
        df_bl = pd.DataFrame(st.session_state.bl_data_list)
        
        # ---------------------------------------------------------
        # 🔍 [신규 기능] 거래처별 필터 및 전체 키워드 검색창 추가
        # ---------------------------------------------------------
        col_srch1, col_srch2 = st.columns([1.5, 2])
        
        with col_srch1:
            # 거래처 목록 추출
            client_options = ["전체 거래처 보기"]
            if "화주명(매출)" in df_bl.columns:
                unique_clients = sorted(list(set(df_bl["화주명(매출)"].dropna().astype(str).str.strip())))
                client_options.extend([c for c in unique_clients if c])
                
            selected_client_filter = st.selectbox(
                "🏢 거래처(화주명) 필터 선택",
                options=client_options,
                key="bl_edit_client_filter"
            )
            
        with col_srch2:
            search_keyword = st.text_input(
                "🔍 B/L 번호 / Job 번호 / 해외수하인 / 품목 검색",
                placeholder="예: BW260017 또는 넥서스파마...",
                key="bl_edit_search_keyword"
            )
            
        # 데이터 필터링 로직
        filtered_df = df_bl.copy()
        
        # 1) 거래처 필터링
        if selected_client_filter != "전체 거래처 보기" and "화주명(매출)" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["화주명(매출)"].astype(str).str.strip() == selected_client_filter]
            
        # 2) 키워드 검색 필터링
        if search_keyword.strip():
            kw = search_keyword.strip().lower()
            mask = pd.Series(False, index=filtered_df.index)
            for col in ["B/L 번호", "Job 번호", "화주명(매출)", "해외수하인", "품목", "매입처", "국가"]:
                if col in filtered_df.columns:
                    mask |= filtered_df[col].astype(str).str.lower().str.contains(kw, na=False)
            filtered_df = filtered_df[mask]

        st.markdown(f"📌 조회 결과: 총 {len(filtered_df)} 건의 B/L이 검색되었습니다.")
        
        # 숫자 및 소수점 포맷팅
        for col_name in ["실중량(kg)", "매출실중량(kg)", "매입실중량(kg)"]:
            if col_name in filtered_df.columns:
                filtered_df[col_name] = pd.to_numeric(filtered_df[col_name], errors="coerce").fillna(0.0).apply(lambda x: f"{x:.2f}")

        if "선택" not in filtered_df.columns:
            filtered_df.insert(0, "선택", False)
            
        st.info("💡 수정할 B/L 행의 [선택] 체크박스를 체크하시면, 아래쪽에 내용을 상세히 수정할 수 있는 **[B/L 개별 수정 입력칸]**이 나타납니다.")
        
        edited_bl_table = st.data_editor(
            filtered_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "선택": st.column_config.CheckboxColumn(required=True),
                "실중량(kg)": st.column_config.NumberColumn("실중량(kg)", format="%.2f"),
                "매출실중량(kg)": st.column_config.NumberColumn("매출실중량(kg)", format="%.2f"),
                "매입실중량(kg)": st.column_config.NumberColumn("매입실중량(kg)", format="%.2f"),
            },
            key="edit_bl_profit_table_select_filtered",
            height=300
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            delete_clicked = st.button("🚨 선택한 B/L 삭제", type="secondary", use_container_width=True)
            if delete_clicked:
                selected_rows_del = edited_bl_table[edited_bl_table["선택"] == True]
                if not selected_rows_del.empty:
                    # 원본 session_state 목록에서 B/L 번호 또는 Job 번호 기준으로 삭제
                    del_bl_nos = set(selected_rows_del["B/L 번호"].astype(str).tolist())
                    st.session_state.bl_data_list = [
                        item for item in st.session_state.bl_data_list 
                        if str(item.get("B/L 번호", "")) not in del_bl_nos
                    ]
                    save_bl_data(st.session_state.bl_data_list)
                    st.success("🗑️ 선택한 B/L 내역이 삭제되었습니다.")
                    st.rerun()
                else:
                    st.warning("⚠️ 삭제할 B/L 행의 체크박스를 선택해주세요.")
                    
        st.markdown("---")
        
        # 선택한 행 상세 수정 폼
        selected_rows = edited_bl_table[edited_bl_table["선택"] == True]
        
        if len(selected_rows) == 1:
            selected_bl_no = str(selected_rows.iloc[0].get("B/L 번호", ""))
            
            # 원본 세션 리스트에서 실제 인덱스 찾기
            target_idx = None
            for idx, item in enumerate(st.session_state.bl_data_list):
                if str(item.get("B/L 번호", "")) == selected_bl_no:
                    target_idx = idx
                    break
                    
            if target_idx is not None:
                target_item = st.session_state.bl_data_list[target_idx]
                
                st.markdown(f"### 📝 선택한 B/L 상세 수정 칸 (Job: {target_item.get('Job 번호', '')} / B/L: {target_item.get('B/L 번호', '')})")
                
                # 품목 선택은 form 바깥에 둡니다. Streamlit form 안에서는 선택 변경 시 재실행되지 않아
                # 조건부 직접입력 칸이 즉시 나타나지 않는 문제가 발생합니다.
                item_options_list = ["보톡스", "필러", "화장품", "특가품목", "의약품", "기타"]
                current_item_val = _client_text(target_item.get("품목", "보톡스"), "보톡스")
                standard_item_options = ["보톡스", "필러", "화장품", "특가품목", "의약품", "기타"]
                if current_item_val in standard_item_options:
                    item_default = current_item_val
                    custom_item_default = ""
                else:
                    # 저장된 사용자 지정 품목은 드롭다운에서 '기타'로 표시하고
                    # 아래 직접입력 칸에 원래 품목명을 유지합니다.
                    item_default = "기타"
                    custom_item_default = current_item_val

                item_widget_key = f"edit_item_dropdown_{target_item.get('B/L 번호', target_idx)}"
                custom_widget_key = f"edit_item_custom_input_{target_item.get('B/L 번호', target_idx)}"
                if item_widget_key not in st.session_state:
                    st.session_state[item_widget_key] = item_default
                if custom_widget_key not in st.session_state:
                    st.session_state[custom_widget_key] = custom_item_default

                # 품명 선택을 상세 수정 폼의 3번째 열(매입처/수금상태 위치)에 맞춰 배치합니다.
                # Streamlit form 바깥에 두어 '기타' 선택 즉시 직접입력 칸이 표시되게 합니다.
                item_layout_col1, item_layout_col2, item_layout_col3 = st.columns(3)
                with item_layout_col3:
                    e_item_choice = st.selectbox(
                        "품명 선택",
                        options=item_options_list,
                        key=item_widget_key
                    )
                    if e_item_choice == "기타":
                        e_item_custom = st.text_input(
                            "기타 품목 직접 입력",
                            placeholder="예: 의료기기, 의약품 원료 등",
                            key=custom_widget_key
                        )
                        e_item = e_item_custom.strip()
                    else:
                        e_item = e_item_choice

                with st.form("detail_bl_edit_form_filtered"):
                    d_col1, d_col2, d_col3 = st.columns(3)
                    with d_col1:
                        e_type = st.selectbox("구분", ["수출 (Export)", "수입 (Import)"], index=0 if "수출" in str(target_item.get("구분", "")) else 1)
                        
                        raw_date = str(target_item.get("날짜", str(date.today())))
                        try:
                            parsed_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
                        except:
                            parsed_date = date.today()
                        e_date = st.date_input("선적 날짜", value=parsed_date)
                        
                        e_job = st.text_input("Job 번호", value=str(target_item.get("Job 번호", "")))
                        e_bl = st.text_input("B/L 번호", value=str(target_item.get("B/L 번호", "")))
                    with d_col2:
                        current_country_val = str(target_item.get("국가", "미국")).strip()
                        country_idx = COUNTRY_LIST.index(current_country_val) if current_country_val in COUNTRY_LIST else 0
                        e_country = st.selectbox("국가 선택", options=COUNTRY_LIST, index=country_idx, key="edit_country_dropdown")

                        clients_opt = st.session_state.get("client_list", ["아코글로벌", "주식회사 조은로직스"])
                        current_shipper_val = str(target_item.get("화주명(매출)", "")).strip()
                        shipper_idx = clients_opt.index(current_shipper_val) if current_shipper_val in clients_opt else 0
                        e_shipper = st.selectbox("화주명(매출) 선택", options=clients_opt, index=shipper_idx, key="edit_shipper_dropdown")

                        e_consignee = st.text_input("해외수하인", value=str(target_item.get("해외수하인", "")))
                        e_consignee_addr = st.text_input("해외수하인주소", value=str(target_item.get("해외수하인주소", "")))
                        e_consignee_tel = st.text_input("해외수하인전화번호", value=str(target_item.get("해외수하인전화번호", "")))
                    with d_col3:
                        suppliers_opt = st.session_state.get("supplier_list", ["(주)카스익스프레스", "ESI", "윤세형"])
                        current_supplier_val = str(target_item.get("매입처", "")).strip()
                        supp_idx = suppliers_opt.index(current_supplier_val) if current_supplier_val in suppliers_opt else 0
                        e_vendor = st.selectbox("매입처 선택", options=suppliers_opt, index=supp_idx, key="edit_vendor_dropdown")

                        e_status = st.selectbox("수금 상태", ["미수", "수금완료"], index=0 if str(target_item.get("수금상태", "")) != "수금완료" else 1)
                    
                    st.markdown("---")
                    st.markdown("#### 📦 중량, 규격 및 금액 상세 수정")
                    
                    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
                    with w_col1:
                        e_box = st.text_input("박스수", value=str(target_item.get("박스수", "1 박스")))
                        e_dim = st.text_input("부피 규격", value=str(target_item.get("부피규격", "-")))
                    with w_col2:
                        e_cbm = st.text_input("CBM", value=str(target_item.get("CBM", "0.0 CBM")))
                        e_trans = st.text_input("운송형태", value=str(target_item.get("운송형태", "항공(Air)")))
                    with w_col3:
                        try:
                            def_gw = float(target_item.get("실중량(kg)", target_item.get("매출실중량(kg)", 1.0)))
                        except:
                            def_gw = 1.0
                        e_sales_gw = st.number_input("실중량 (kg) [소수점 유지]", value=def_gw, min_value=0.0, step=0.01, format="%.2f")
                        
                        try:
                            def_scw = float(target_item.get("매출청구중량(kg)", 1.0))
                        except:
                            def_scw = 1.0
                        e_sales_cw = st.number_input("매출 청구중량(kg) [kg당 올림]", value=float(math.ceil(def_scw)), min_value=0.0, step=1.0)
                    with w_col4:
                        try:
                            def_pgw = float(target_item.get("매입실중량(kg)", def_gw))
                        except:
                            def_pgw = 1.0
                        e_purchase_gw = st.number_input("매입 실중량(kg) [소수점 유지]", value=def_pgw, min_value=0.0, step=0.01, format="%.2f")
                        
                        try:
                            def_pcw = float(target_item.get("매입청구중량(kg)", 1.0))
                        except:
                            def_pcw = 1.0
                        e_purchase_cw = st.number_input("매입 청구중량(kg) [kg당 올림]", value=float(math.ceil(def_pcw)), min_value=0.0, step=1.0)
                    
                    st.markdown("---")
                    d_col4, d_col5 = st.columns(2)
                    with d_col4:
                        try:
                            def_sales = int(target_item.get("매출액(원)", 0))
                        except:
                            def_sales = 0
                        e_sales = st.number_input("매출액 (원)", value=def_sales, step=10000)
                    with d_col5:
                        try:
                            def_purchase = int(target_item.get("매입액(원)", 0))
                        except:
                            def_purchase = 0
                        e_purchase = st.number_input("매입액 (원)", value=def_purchase, step=10000)
                        
                    e_memo = st.text_area("비고", value=str(target_item.get("비고", "")))
                    
                    submitted_update = st.form_submit_button("💾 이 내용으로 B/L 수정 저장하기", type="primary", use_container_width=True)
                    if submitted_update:
                        st.session_state.bl_data_list[target_idx].update({
                            "구분": e_type,
                            "날짜": str(e_date),
                            "Job 번호": e_job,
                            "B/L 번호": e_bl,
                            "국가": e_country,
                            "화주명(매출)": e_shipper,
                            "해외수하인": e_consignee,
                            "해외수하인주소": e_consignee_addr,
                            "해외수하인전화번호": e_consignee_tel,
                            "매입처": e_vendor,
                            "품목": e_item,
                            "박스수": e_box,
                            "부피규격": e_dim,
                            "CBM": e_cbm,
                            "운송형태": e_trans,
                            "실중량(kg)": float(e_sales_gw),
                            "매출실중량(kg)": float(e_sales_gw),
                            "매입실중량(kg)": float(e_purchase_gw),
                            "매출청구중량(kg)": float(math.ceil(e_sales_cw)),
                            "매입청구중량(kg)": float(math.ceil(e_purchase_cw)),
                            "수금상태": e_status,
                            "매출액(원)": float(e_sales),
                            "매입액(원)": float(e_purchase),
                            "예상Profit(원)": float(e_sales) - float(e_purchase),
                            "비고": "" if e_memo == "nan" else e_memo,
                            "최종수정자": current_user_name
                        })
                        save_bl_data(st.session_state.bl_data_list)
                        st.success("✅ 선택하신 B/L이 성공적으로 수정 저장되었습니다!")
                        st.rerun()
        elif len(selected_rows) > 1:
            st.warning("⚠️ 상세 수정은 1개씩만 선택해서 진행해주세요.")
        else:
            st.info("📌 수정할 B/L 행의 체크박스를 1개 선택하시면 아래에 상세 수정 입력칸이 나타납니다.")
    else:
        st.info("등록된 B/L 데이터가 없습니다.")
# ==========================================
# [새로운 독립 트랙] 매출 관리 (화주별)
# ==========================================
elif selected_menu == "💰 매출 관리 (화주별 독립 트랙)":
    st.markdown("<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 5px;'>💰 매출 관리 (화주별 독립 트랙)</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 13px; margin-bottom: 15px;'>화주별 매출액, 수금 완료 금액, 미수금 잔액을 집계하고 건별 수금 상태를 관리합니다.</p>", unsafe_allow_html=True)
    
    if st.session_state.get("bl_data_list"):
        df_bl = pd.DataFrame(st.session_state.bl_data_list)
        if "화주명(매출)" in df_bl.columns and "매출액(원)" in df_bl.columns:
            df_bl["화주명(매출)"] = df_bl["화주명(매출)"].astype(str).str.strip()
            df_bl["매출액(원)"] = pd.to_numeric(df_bl["매출액(원)"], errors="coerce").fillna(0)
            if "수금상태" not in df_bl.columns:
                df_bl["수금상태"] = "미수"
            
            # 1. 화주별 매출 및 미수 요약
            sales_group = df_bl.groupby("화주명(매출)").agg(
                총매출액=("매출액(원)", "sum"),
                수금완료액=("매출액(원)", lambda x: x[df_bl.loc[x.index, "수금상태"] == "수금완료"].sum()),
                미수금잔액=("매출액(원)", lambda x: x[df_bl.loc[x.index, "수금상태"] != "수금완료"].sum()),
                건수=("B/L 번호", "count")
            ).reset_index().sort_values("미수금잔액", ascending=False)
            
            st.subheader("📋 화주별 매출 및 미수금 현황 요약")
            st.dataframe(sales_group, use_container_width=True)
            
            st.markdown("---")
            
            # 2. 특정 화주 상세 매출 내역 및 수금 상태 관리
            st.subheader("🔍 특정 화주 상세 매출 내역 및 수금 상태 관리")
            col_s1, col_s2 = st.columns([2, 1])
            with col_s1:
                sel_c = st.selectbox("조회할 화주(매출처) 선택", df_bl["화주명(매출)"].unique(), key="sales_track_client")
            with col_s2:
                only_unpaid_c = st.checkbox("📌 미수 건만 보기", value=True, key="only_unpaid_sales_client")
            
            client_detail = df_bl[df_bl["화주명(매출)"] == sel_c].copy()
            if only_unpaid_c:
                client_detail = client_detail[client_detail["수금상태"].astype(str).str.strip() != "수금완료"]
            
            if "선택" not in client_detail.columns:
                client_detail.insert(0, "선택", False)
            
            edited_sales_table = st.data_editor(
                client_detail,
                hide_index=True,
                use_container_width=True,
                column_config={"선택": st.column_config.CheckboxColumn(required=True)},
                key="sales_unpaid_edit_table"
            )
            
            selected_sales_rows = edited_sales_table[edited_sales_table["선택"] == True]
            
            if st.button("💰 선택한 매출 건 [수금완료] 일괄 처리", type="primary", use_container_width=True):
                if len(selected_sales_rows) > 0:
                    for real_idx in selected_sales_rows.index.tolist():
                        st.session_state.bl_data_list[real_idx]["수금상태"] = "수금완료"
                        st.session_state.bl_data_list[real_idx]["최종수정자"] = current_user_name
                    save_bl_data(st.session_state.bl_data_list)
                    st.success("선택하신 매출 건들이 '수금완료' 처리되었습니다!")
                    st.rerun()
                else:
                    st.warning("수금완료 처리할 B/L 행의 체크박스를 선택해주세요.")
        else:
            st.warning("데이터에 '화주명(매출)' 또는 '매출액(원)' 컬럼이 없습니다.")
    else:
        st.info("등록된 B/L 데이터가 없습니다.")
# ==========================================
# [새로운 독립 트랙] 매입 관리 (협력사별)
# ==========================================
elif selected_menu == "🤝 매입 관리 (협력사별 독립 트랙)":
    st.markdown("<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 5px;'>🤝 매입 관리 및 협력사별 미지급금(미지급 원가) 관리</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 13px; margin-bottom: 15px;'>월별 매입 원가와 협력사별 지급완료·미지급 잔액을 확인하고, 원하는 기간을 지정해 출력할 수 있습니다.</p>", unsafe_allow_html=True)

    if st.session_state.get("bl_data_list"):
        df_bl = pd.DataFrame(st.session_state.bl_data_list).copy()
        if "매입처" in df_bl.columns and "매입액(원)" in df_bl.columns:
            df_bl["매입처"] = df_bl["매입처"].fillna("").astype(str).str.strip()
            df_bl["매입액(원)"] = pd.to_numeric(
                df_bl["매입액(원)"].astype(str).str.replace(",", "", regex=False),
                errors="coerce"
            ).fillna(0)
            if "지급상태" not in df_bl.columns:
                df_bl["지급상태"] = "미지급"
            df_bl["지급상태"] = df_bl["지급상태"].fillna("미지급").astype(str).str.strip()
            if "날짜" not in df_bl.columns:
                df_bl["날짜"] = ""
            df_bl["_매입일자"] = pd.to_datetime(
                df_bl["날짜"].astype(str).str[:10], errors="coerce"
            )
            df_bl = df_bl[df_bl["매입처"] != ""].copy()

            # 월별 조회: B/L 등록일(날짜) 기준
            st.markdown("### 📅 월별 매입 관리")
            valid_dates = df_bl["_매입일자"].dropna()
            available_years = sorted(set(valid_dates.dt.year.tolist() + [date.today().year]), reverse=True)
            mc1, mc2 = st.columns([1, 2])
            with mc1:
                selected_purchase_year = st.selectbox(
                    "조회 연도", available_years, index=0, key="purchase_month_year"
                )
            with mc2:
                selected_purchase_month = st.selectbox(
                    "조회 월", list(range(1, 13)),
                    index=date.today().month - 1, format_func=lambda m: f"{m}월",
                    key="purchase_month_value"
                )

            month_start = date(int(selected_purchase_year), int(selected_purchase_month), 1)
            if selected_purchase_month == 12:
                month_end = date(int(selected_purchase_year) + 1, 1, 1) - pd.Timedelta(days=1)
            else:
                month_end = date(int(selected_purchase_year), int(selected_purchase_month) + 1, 1) - pd.Timedelta(days=1)

            month_df = df_bl[
                (df_bl["_매입일자"] >= pd.Timestamp(month_start)) &
                (df_bl["_매입일자"] < pd.Timestamp(month_end) + pd.Timedelta(days=1))
            ].copy()

            if not month_df.empty:
                month_df["_지급완료금액"] = month_df["매입액(원)"].where(month_df["지급상태"] == "지급완료", 0)
                month_df["_미지급금액"] = month_df["매입액(원)"].where(month_df["지급상태"] != "지급완료", 0)
                purchase_group = month_df.groupby("매입처", dropna=False).agg(
                    총매입액=("매입액(원)", "sum"),
                    지급완료액=("_지급완료금액", "sum"),
                    미지급잔액=("_미지급금액", "sum"),
                    건수=("매입액(원)", "size")
                ).reset_index().sort_values("미지급잔액", ascending=False)
                total_purchase = int(month_df["매입액(원)"].sum())
                total_paid = int(month_df["_지급완료금액"].sum())
                total_unpaid = int(month_df["_미지급금액"].sum())
            else:
                purchase_group = pd.DataFrame(columns=["매입처", "총매입액", "지급완료액", "미지급잔액", "건수"])
                total_purchase = total_paid = total_unpaid = 0

            st.caption(f"조회 기준: {selected_purchase_year}년 {selected_purchase_month}월")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("월 매입 총액", f"{total_purchase:,.0f}원")
            k2.metric("지급완료", f"{total_paid:,.0f}원")
            k3.metric("미지급 잔액", f"{total_unpaid:,.0f}원")
            k4.metric("매입 건수", f"{len(month_df):,}건")
            st.subheader("🤝 협력사별 월 매입·지급 현황")
            st.dataframe(purchase_group, use_container_width=True, hide_index=True)
            if month_df.empty:
                st.info("선택한 월에 등록된 매입 내역이 없습니다.")

            st.markdown("---")
            # 지정 기간 출력 및 엑셀 다운로드
            st.markdown("### 🖨️ 기간 지정 매입 내역 출력")
            p1, p2 = st.columns(2)
            with p1:
                print_start = st.date_input(
                    "시작일", value=month_start, key="purchase_print_start"
                )
            with p2:
                print_end = st.date_input(
                    "종료일", value=month_end, key="purchase_print_end"
                )

            supplier_options = ["전체 협력사"] + sorted(df_bl["매입처"].dropna().unique().tolist())
            selected_print_supplier = st.selectbox(
                "출력할 협력사", supplier_options, key="purchase_print_supplier"
            )
            if print_start > print_end:
                st.error("시작일은 종료일보다 늦을 수 없습니다.")
                print_df = df_bl.iloc[0:0].copy()
            else:
                print_df = df_bl[
                    (df_bl["_매입일자"] >= pd.Timestamp(print_start)) &
                    (df_bl["_매입일자"] < pd.Timestamp(print_end) + pd.Timedelta(days=1))
                ].copy()
                if selected_print_supplier != "전체 협력사":
                    print_df = print_df[print_df["매입처"] == selected_print_supplier]

            print_columns = [
                c for c in [
                    "날짜", "매입처", "B/L 번호", "화주명(매출)", "해외수하인",
                    "도착국가", "운송형태", "매입액(원)", "지급상태"
                ] if c in print_df.columns
            ]
            printable_df = print_df[print_columns].copy() if print_columns else pd.DataFrame()
            if not printable_df.empty:
                printable_df["매입액(원)"] = pd.to_numeric(
                    printable_df["매입액(원)"], errors="coerce"
                ).fillna(0).map(lambda v: f"{v:,.0f}")
            st.caption(f"출력 대상: {len(print_df)}건 / {print_start} ~ {print_end}")
            st.dataframe(printable_df, use_container_width=True, hide_index=True)

            if not print_df.empty:
                export_df = print_df[print_columns].copy()
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    export_df.to_excel(writer, sheet_name="매입내역", index=False)
                    summary_df = pd.DataFrame([{
                        "조회 시작일": str(print_start),
                        "조회 종료일": str(print_end),
                        "협력사": selected_print_supplier,
                        "매입 총액": int(print_df["매입액(원)"].sum()),
                        "지급완료액": int(print_df.loc[print_df["지급상태"] == "지급완료", "매입액(원)"].sum()),
                        "미지급 잔액": int(print_df.loc[print_df["지급상태"] != "지급완료", "매입액(원)"].sum()),
                        "건수": len(print_df)
                    }])
                    summary_df.to_excel(writer, sheet_name="기간요약", index=False)
                st.download_button(
                    "📥 지정 기간 매입 내역 엑셀 다운로드",
                    data=excel_buffer.getvalue(),
                    file_name=f"범운해운항공_매입내역_{print_start}_{print_end}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

                # 브라우저 인쇄: 선택한 기간의 매입 내역만 별도 인쇄 화면으로 제공
                import html as _html
                table_html = printable_df.to_html(index=False, border=0, escape=True, classes="purchase-print-table")
                total_print_amount = int(print_df["매입액(원)"].sum())
                paid_print_amount = int(print_df.loc[print_df["지급상태"] == "지급완료", "매입액(원)"].sum())
                unpaid_print_amount = int(print_df.loc[print_df["지급상태"] != "지급완료", "매입액(원)"].sum())
                print_title = "전체 협력사" if selected_print_supplier == "전체 협력사" else _html.escape(selected_print_supplier)
                print_html = f"""
                <html><head><meta charset="utf-8"><style>
                body{{font-family:Arial,'Malgun Gothic',sans-serif;padding:18px;color:#111}}
                h2{{text-align:center;margin-bottom:8px}} .meta{{text-align:center;margin-bottom:18px}}
                .summary{{display:flex;justify-content:space-around;margin:14px 0;padding:12px;border:1px solid #bbb;font-weight:bold}}
                table{{width:100%;border-collapse:collapse;font-size:10pt}}
                th,td{{border:1px solid #777;padding:7px;text-align:center}}
                th{{background:#eee}} .actions{{margin-bottom:12px}}
                @media print{{.actions{{display:none}} body{{padding:0}}}}
                </style></head><body>
                <div class="actions"><button onclick="window.print()">🖨️ 이 매입 내역 인쇄</button></div>
                <h2>(주)범운해운항공 매입 내역서</h2>
                <div class="meta">{print_start} ~ {print_end}　|　협력사: {print_title}</div>
                <div class="summary">
                <span>매입 합계: {total_print_amount:,.0f}원</span>
                <span>지급완료: {paid_print_amount:,.0f}원</span>
                <span>미지급: {unpaid_print_amount:,.0f}원</span>
                <span>총 {len(print_df)}건</span>
                </div>{table_html}</body></html>
                """
                components.html(print_html, height=650, scrolling=True)
            else:
                st.info("선택한 기간과 협력사에 해당하는 매입 내역이 없습니다.")

            st.markdown("---")
            # 협력사 상세 및 기존 지급완료 처리 기능 유지
            st.subheader("🔍 협력사 상세 매입 내역 및 지급 상태 관리")
            vendor_options = sorted(df_bl["매입처"].dropna().unique().tolist())
            sel_v = st.selectbox(
                "조회할 협력사 선택", vendor_options, key="purchase_track_vendor"
            )
            only_unpaid_v = st.checkbox(
                "📌 미지급 건만 보기", value=True, key="only_unpaid_vendor"
            )
            vendor_detail = df_bl[df_bl["매입처"] == sel_v].copy()
            if only_unpaid_v:
                vendor_detail = vendor_detail[vendor_detail["지급상태"] != "지급완료"]
            if "선택" not in vendor_detail.columns:
                vendor_detail.insert(0, "선택", False)

            edited_vendor_table = st.data_editor(
                vendor_detail.drop(columns=["_매입일자"], errors="ignore"),
                hide_index=True,
                use_container_width=True,
                column_config={"선택": st.column_config.CheckboxColumn(required=True)},
                key="vendor_unpaid_edit_table"
            )
            selected_vendor_rows = edited_vendor_table[edited_vendor_table["선택"] == True]
            if st.button("💳 선택한 매입 건 [지급완료] 일괄 처리", type="primary", use_container_width=True):
                if len(selected_vendor_rows) > 0:
                    for real_idx in selected_vendor_rows.index.tolist():
                        if 0 <= int(real_idx) < len(st.session_state.bl_data_list):
                            st.session_state.bl_data_list[int(real_idx)]["지급상태"] = "지급완료"
                            st.session_state.bl_data_list[int(real_idx)]["최종수정자"] = current_user_name
                    save_bl_data(st.session_state.bl_data_list)
                    st.success("선택하신 매입 건들이 '지급완료' 처리되었습니다!")
                    st.rerun()
                else:
                    st.warning("지급완료 처리할 B/L 행의 체크박스를 선택해주세요.")
        else:
            st.warning("데이터에 '매입처' 또는 '매입액(원)' 컬럼이 없습니다.")
    else:
        st.info("등록된 B/L 데이터가 없습니다.")

# ==========================================
# [3] B/L 운송장 출력 메뉴 (검색창 추가 버전)
# ==========================================
elif selected_menu == "🚢 B/L 운송장 출력":
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>🚢"
        " (주)범운해운항공 정식 B/L 운송장 출력</h3>",
        unsafe_allow_html=True,
    )

    if st.session_state.bl_data_list:
        # 💡 B/L 번호나 화주명을 직접 검색할 수 있는 입력창 추가
        search_filter_keyword = st.text_input(
            "🔍 B/L 번호 또는 화주명 검색 (입력하시면 아래 선택 목록이 필터링됩니다)",
            value="",
            placeholder="예: BW260017 또는 텐트리스트",
            key="bl_print_search_keyword"
        )

        # 검색어가 있으면 일치하는 항목만 필터링, 없으면 전체 목록 표시
        filtered_bl_items = []
        for item in st.session_state.bl_data_list:
            b_no = str(item.get("B/L 번호", ""))
            s_name = str(item.get("화주명(매출)", ""))
            j_no = str(item.get("Job 번호", ""))
            
            if search_filter_keyword.strip() == "":
                filtered_bl_items.append(item)
            else:
                kw = search_filter_keyword.strip().lower()
                if kw in b_no.lower() or kw in s_name.lower() or kw in j_no.lower():
                    filtered_bl_items.append(item)

        if filtered_bl_items:
            # 선택창에 보기 좋게 [B/L번호] 화주명 형태로 표시
            bl_display_options = [
                f"{item.get('B/L 번호', '')} (화주: {item.get('화주명(매출)', '-')}, Job: {item.get('Job 번호', '-')})"
                for item in filtered_bl_items
            ]
            
            selected_display_str = st.selectbox(
                "출력할 B/L 선택하기 (검색 결과)", 
                options=bl_display_options,
                key="selected_bl_print_selectbox"
            )

            # 선택된 문자열에서 B/L 번호 추출
            selected_print_bl = selected_display_str.split(" ")[0].strip()

            target_bl_data = next(
                (
                    item
                    for item in st.session_state.bl_data_list
                    if str(item.get("B/L 번호", "")) == selected_print_bl
                ),
                None,
            )

            if target_bl_data:

              def clean_val(v, default="-"):
                if v is None:
                  return default
                s = str(v).strip()
                if s == "" or s.lower() == "nan":
                  return default
                return s

              shipper_n = clean_val(target_bl_data.get("화주명(매출)"))
              shipper_inf = st.session_state.client_infos.get(shipper_n, {})
              shipper_addr = clean_val(
                  shipper_inf.get("주소"), "경기도 김포시 풍무동 326-5번지 2층"
              )
              shipper_bno = clean_val(shipper_inf.get("사업자등록번호"), "-")
              shipper_mgr = clean_val(shipper_inf.get("담당자"), "-")
              shipper_tel = clean_val(shipper_inf.get("전화번호"), "-")

              consignee_n = clean_val(target_bl_data.get("해외수하인"))
              consignee_addr = clean_val(target_bl_data.get("해외수하인주소"), "-")
              consignee_tel = clean_val(target_bl_data.get("해외수하인전화번호"), "-")
              dest_c = clean_val(target_bl_data.get("국가"))
              origin_p = clean_val(target_bl_data.get("출발지"), "대한민국 (KOREA)")
              ship_date = clean_val(target_bl_data.get("날짜"), str(date.today()))
              bl_num_str = clean_val(target_bl_data.get("B/L 번호"))
              job_num_str = clean_val(target_bl_data.get("Job 번호"), "-")
              item_name = clean_val(target_bl_data.get("품목"))
              box_cnt = clean_val(target_bl_data.get("박스수"), "1 박스")
              vol_spec = clean_val(target_bl_data.get("부피규격"), "-")
              cbm_val = clean_val(target_bl_data.get("CBM"), "-")
              sales_cw = target_bl_data.get("매출청구중량(kg)", 1.0)
              transport_t = clean_val(target_bl_data.get("운송형태"), "항공(Air)")
              service_opt = clean_val(target_bl_data.get("서비스옵션"), "Door To Door")
              current_status_str = clean_val(
                  target_bl_data.get("현재 상태"), "운송 중"
              )

              logo_embed_bl = (
                  f"<img src='data:image/png;base64,{encoded_sidebar_logo}'"
                  " style='height: 42px; vertical-align: middle; margin-right: 10px;'>"
                  if encoded_sidebar_logo
                  else ""
              )
              barcode_html = generate_barcode_html(bl_num_str)

              air_check = "☑" if "항공" in transport_t else "☐"
              sea_check = "☑" if "해상" in transport_t else "☐"
              d2d_check = "☑" if "Door" in service_opt else "☐"

              awb_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            @media print {{
                                body {{ -webkit-print-color-adjust: exact; }}
                                .no-print {{ display: none !important; }}
                                @page {{ size: A4 portrait; margin: 10mm; }}
                            }}
                            body {{ font-family: 'Pretendard', sans-serif; color: #1e293b; font-size: 9.5pt; margin: 0; padding: 10px; background: #fff; }}
                            .awb-container {{ max-width: 760px; margin: 0 auto; border: 2px solid #0f172a; padding: 20px; border-radius: 6px; }}
                            .top-table, .mid-table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
                            .top-table td, .mid-table td {{ border: 1px solid #64748b; padding: 8px 10px; vertical-align: top; }}
                            .section-header {{ background-color: #0f172a; color: white; font-weight: bold; font-size: 9pt; padding: 3px 6px; margin-bottom: 4px; }}
                            .print-btn {{ display: block; width: 100%; background-color: #2563eb; color: white; text-align: center; padding: 10px; font-size: 11pt; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; margin-bottom: 15px; }}
                        </style>
                    </head>
                    <body>
                        <div class="awb-container">
                            <button class="print-btn no-print" onclick="window.print()">🖨 B/L 운송장 인쇄 및 PDF 저장</button>
                            <table style="width: 100%; border-bottom: 2.5px solid #0f172a; padding-bottom: 10px; margin-bottom: 12px;">
                                <tr>
                                    <td style="width: 55%; border: none;">
                                        <div style="display: flex; align-items: center;">
                                            {logo_embed_bl}
                                            <div>
                                                <div style="font-size: 14pt; font-weight: 900; color: #1e3a8a;">주식회사 범운해운항공</div>
                                                <div style="font-size: 7.5pt; color: #475569; font-weight: bold;">BUMWOON OCEAN & AIR CO., LTD.</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td style="width: 45%; text-align: right; border: none;">
                                        <div style="font-size: 8.5pt; color: #64748b; font-weight: bold; margin-bottom: 2px;">AIR WAYBILL / B/L NO.</div>
                                        {barcode_html}
                                    </td>
                                </tr>
                            </table>
                            <table class="top-table">
                                <tr>
                                    <td style="width: 50%;">
                                        <div class="section-header">FROM (SHIPPER / 송하인)</div>
                                        <b>상호:</b> {shipper_n}<br>
                                        <b>사업자등록번호:</b> {shipper_bno}<br>
                                        <b>주소:</b> {shipper_addr}<br>
                                        <b>담당자 / 연락처:</b> {shipper_mgr} / {shipper_tel}
                                    </td>
                                    <td style="width: 50%;">
                                        <div class="section-header">TO (CONSIGNEE / 수하인)</div>
                                        <b>수하인명:</b> <span style="font-size: 10.5pt; color: #1e3a8a; font-weight: bold;">{consignee_n}</span><br><b>주소:</b> {consignee_addr}<br><b>연락처:</b> {consignee_tel}<br>
                                        <b>도착 국가:</b> {dest_c}<br>
                                        <b>출발지:</b> {origin_p}
                                    </td>
                                </tr>
                            </table>
                            <table class="mid-table">
                                <tr>
                                    <td style="width: 33%;"><b>CARRIER</b><br>{air_check} AIR &nbsp;&nbsp; {sea_check} SEA</td>
                                    <td style="width: 33%;"><b>SERVICE</b><br>{d2d_check} Door To Door</td>
                                    <td style="width: 34%;"><b>SCHEDULE</b><br>선적일자: <b>{ship_date}</b></td>
                                </tr>
                            </table>
                            <table class="top-table">
                                <tr>
                                    <td style="width: 60%;">
                                        <div class="section-header">DESCRIPTION OF CONTENTS</div>
                                        <div style="font-size: 11pt; font-weight: bold; color: #1e3a8a; padding: 6px 0;">{item_name}</div>
                                        • 박스 수: <b>{box_cnt}</b> | 규격: {vol_spec} ({cbm_val})
                                    </td>
                                    <td style="width: 40%;">
                                        <div class="section-header">WEIGHT</div>
                                        청구중량: <b style="color: #dc2626;">{sales_cw} KG</b>
                                    </td>
                                </tr>
                            </table>
                        </div>
                    </body>
                    </html>
                    """
              components.html(awb_html, height=750, scrolling=False)
        else:
            st.warning("🔍 검색하신 조건에 일치하는 B/L 내역이 없습니다.")
    else:
        st.info("등록된 B/L 데이터가 없습니다.")

# ==========================================
# [4] 거래처 인보이스 발행 (기간 선택 기능 추가 완료)
# ==========================================
elif selected_menu == "📑 거래처 인보이스 발행":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 5px;'>📑"
      " 거래처 인보이스 발행</h3>",
      unsafe_allow_html=True,
  )

  if st.session_state.client_list:
    col_inv1, col_inv2, col_inv3 = st.columns([1.5, 1.8, 1])
    with col_inv1:
      selected_invoice_client = st.selectbox(
          "인보이스를 발행할 거래처 선택", options=st.session_state.client_list
      )
    with col_inv2:
      # 📅 단일 날짜가 아닌 [시작일, 종료일] 범위 선택 기능 적용
      today_val = date.today()
      default_start = today_val.replace(day=1) # 해당 월 1일
      
      date_range = st.date_input(
          "조회할 선적 기간 선택 (시작일 ~ 종료일)",
          value=(default_start, today_val),
          key="invoice_target_date_range"
      )
      
      # 기간 선택 처리 (시작일과 종료일 분리)
      if isinstance(date_range, (list, tuple)):
          if len(date_range) == 2:
              start_date, end_date = date_range[0], date_range[1]
          elif len(date_range) == 1:
              start_date, end_date = date_range[0], date_range[0]
          else:
              start_date = end_date = today_val
      else:
          start_date = end_date = date_range

    with col_inv3:
      tax_mode = st.selectbox(
          "영세율 / 세금계산서 설정",
          options=[
              "영세율 적용 (세금계산서 미발행/청구확인용)",
              "과세 적용 (VAT 10%)",
          ],
      )

    start_date_str = str(start_date)
    end_date_str = str(end_date)
    date_display_text = f"{start_date_str} ~ {end_date_str}" if start_date != end_date else start_date_str

    client_infos = st.session_state.client_infos.get(
        selected_invoice_client, {}
    )

    # 지정한 기간(start_date ~ end_date) 내의 B/L 필터링
    client_bl_list = []
    if "bl_data_list" in st.session_state and st.session_state.bl_data_list:
      for j in st.session_state.bl_data_list:
        if j.get("화주명(매출)") == selected_invoice_client:
          ship_d_str = str(j.get("날짜", ""))[:10]
          try:
            ship_d = datetime.strptime(ship_d_str, "%Y-%m-%d").date()
            if start_date <= ship_d <= end_date:
              client_bl_list.append(j)
          except Exception:
            if start_date_str <= ship_d_str <= end_date_str:
              client_bl_list.append(j)

    st.markdown(
        f"#### 📌 [{selected_invoice_client}] [{date_display_text}] 청구 대상"
        f" B/L 목록 (총 {len(client_bl_list)}건)"
    )

    if client_bl_list:
      df_inv = pd.DataFrame(client_bl_list)
      preferred_cols = [
          "날짜",
          "B/L 번호",
          "국가",
          "해외수하인",
          "품목",
          "박스수",
          "부피규격",
          "매출청구중량(kg)",
          "매출액(원)",
      ]
      show_cols = [col for col in preferred_cols if col in df_inv.columns]
      st.dataframe(df_inv[show_cols], use_container_width=True)

      subtotal_amount = sum(
          int(j.get("매출액(원)", 0)) for j in client_bl_list
      )
      vat_amount = (
          0 if "영세율 적용" in tax_mode else int(subtotal_amount * 0.1)
      )
      grand_total = subtotal_amount + vat_amount

      bank_account_choice = st.selectbox(
          "입금 계좌 선택",
          options=[
              "우리은행 1005-704-932716 (주)범운해운항공",
              "카카오뱅크 3333-12-9553477 이상복((주)범운해운항공)",
          ],
      )

      if st.button(
          "🖨 정식 인보이스 인쇄 및 PDF 저장하기",
          type="primary",
          use_container_width=True,
      ):
        c_addr = client_infos.get("주소", "-")
        c_bno = client_infos.get("사업자등록번호", "-")
        c_mgr = client_infos.get("담당자", "-")

        invoice_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        @page {{ size: A4 portrait; margin: 7mm; }}
                        * {{ box-sizing: border-box; }}
                        body {{ font-family: 'Pretendard', 'Malgun Gothic', sans-serif; color: #1e293b; font-size: 8pt; margin: 0; padding: 4px; background: #fff; }}
                        .inv-box {{ width: 100%; max-width: 100%; margin: 0 auto; border: 1.5px solid #0f172a; padding: 10px; border-radius: 4px; }}
                        .t-tbl {{ width: 100%; border-collapse: collapse; margin-top: 10px; table-layout: fixed; }}
                        .t-tbl th, .t-tbl td {{ border: 1px solid #64748b; padding: 4px 2px; text-align: center; vertical-align: middle; font-size: 7pt; line-height: 1.25; overflow-wrap: anywhere; word-break: normal; }}
                        .t-tbl th {{ background-color: #0f172a; color: white; font-size: 7.2pt; }}
                        .t-tbl .dim-cell {{ white-space: normal; text-align: center; line-height: 1.35; }}
                        .t-tbl .weight-cell {{ white-space: nowrap; }}
                        .t-tbl .amount-cell {{ white-space: nowrap; text-align: right; font-weight: bold; }}
                        .p-btn {{ display: block; width: 100%; background-color: #dc2626; color: white; text-align: center; padding: 10px; font-size: 11pt; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; margin-bottom: 15px; }}
                        @media print {{ body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }} .no-print {{ display: none !important; }} .inv-box {{ border-radius: 0; border-width: 1px; padding: 6px; }} .t-tbl {{ page-break-inside: auto; }} .t-tbl tr {{ page-break-inside: avoid; page-break-after: auto; }} }}
                    </style>
                </head>
                <body>
                    <div class="inv-box">
                        <button class="p-btn no-print" onclick="window.print()">🖨 인보이스 인쇄 및 PDF 저장</button>
                        <h1 style="text-align: center; color: #1e3a8a; margin-bottom: 5px; font-size: 18pt; font-weight: 900;">청 구 서 (INVOICE)</h1>
                        <p style="text-align: center; color: #475569; font-size: 8.5pt; margin-top: 0;">(주)범운해운항공 | 발행일자: {date.today()} | 선적기간: <b>{date_display_text}</b></p>
                        <table style="width: 100%; margin-top: 12px; border-collapse: collapse;">
                            <tr>
                                <td style="border: 1px solid #64748b; padding: 8px; background: #fff; font-size: 9pt;">
                                    <b>[공급받는 자]</b> 상호: <b>{selected_invoice_client}</b> | 사업자등록번호: {c_bno} | 담당자: {c_mgr}<br>주소: {c_addr}
                                </td>
                            </tr>
                        </table>
                        <table class="t-tbl">
                            <colgroup>
                                <col style="width: 9%;"><col style="width: 10%;"><col style="width: 6%;"><col style="width: 17%;">
                                <col style="width: 13%;"><col style="width: 18%;"><col style="width: 10%;"><col style="width: 17%;">
                            </colgroup>
                            <tr>
                                <th>작성일자</th><th>B/L 번호</th><th>국가</th><th>수하인</th><th>품목 / 박스</th><th>부피규격 (cm)</th><th>청구중량</th><th>금액 (원)</th>
                            </tr>
            """
        for r in client_bl_list:
          # 규격별 카톤 수량을 보존합니다.
          # 전체 박스 수량(예: 5 CTN)은 품목/박스 열에, 각 규격별 수량(예: 3 CTN)은 부피규격 열에 표시합니다.
          raw_volume_spec = str(r.get("부피규격", "-") or "-").strip()
          volume_parts = re.split(r"\s*/\s*", raw_volume_spec)
          formatted_parts = []
          for part in volume_parts:
              part = part.strip()
              if not part or part == "-":
                  continue
              count_match = re.search(r"\(\s*(\d+)\s*CTN\s*\)", part, flags=re.IGNORECASE)
              if count_match:
                  dimension_text = re.sub(r"\s*\(\s*\d+\s*CTN\s*\)", "", part, flags=re.IGNORECASE).strip()
                  carton_count = int(count_match.group(1))
                  formatted_parts.append(f"{dimension_text} <b>({carton_count} CTN)</b>")
              else:
                  # 예전 데이터에 규격별 CTN 정보가 없는 경우에도 치수는 그대로 표시합니다.
                  formatted_parts.append(part)
          volume_spec_html = "<br>".join(formatted_parts) if formatted_parts else "-"
          invoice_html += f"""
                    <tr>
                        <td>{r.get("날짜", "-")}</td>
                        <td style="font-weight: bold;">{r.get("B/L 번호", "-")}</td>
                        <td>{r.get("국가", "-")}</td>
                        <td>{r.get("해외수하인", "-")}</td>
                        <td>{r.get("품목", "-")} ({r.get("박스수", "1 박스")})</td>
                        <td class="dim-cell">{volume_spec_html}</td>
                        <td class="weight-cell">{r.get("매출청구중량(kg)", 1.0)} kg</td>
                        <td class="amount-cell">{int(float(r.get("매출액(원)", 0) or 0)):,} 원</td>
                    </tr>
                """
        invoice_html += f"""
                            <tr><td colspan="7" style="text-align: right; font-weight: bold; background: #f1f5f9;">공급가액 합계</td><td style="text-align: right; font-weight: bold; background: #f1f5f9;">{subtotal_amount:,} 원</td></tr>
                            <tr><td colspan="7" style="text-align: right; font-weight: bold; background: #f1f5f9;">VAT [{tax_mode}]</td><td style="text-align: right; font-weight: bold; background: #f1f5f9;">{vat_amount:,} 원</td></tr>
                            <tr><td colspan="7" style="text-align: right; font-weight: bold; background: #0f172a; color: white;">총 청구금액 (GRAND TOTAL)</td><td style="text-align: right; font-weight: bold; background: #0f172a; color: white;">{grand_total:,} 원</td></tr>
                        </table>
                        <div style="margin-top: 20px; padding: 10px; border: 1px solid #cbd5e1; background: #f8fafc; font-size: 9pt;">
                            <b>📌 입금 계좌:</b> <span style="color: #1e3a8a; font-weight: bold;">{bank_account_choice}</span>
                        </div>
                        <div style="margin-top: 25px; text-align: center; font-weight: bold; font-size: 10.5pt;">
                            주식회사 범운해운항공 대표이사 이상복 [직인생략]
                        </div>
                    </div>
                </body>
                </html>
                """
        components.html(invoice_html, height=850, scrolling=True)
    else:
      st.info(
          f"[{selected_invoice_client}] 거래처의 [{date_display_text}] 기간 내"
          " 선적 데이터가 없습니다."
      )

# ==========================================
# [5] 화물 견적서 발행
# ==========================================
elif selected_menu == "📄 화물 견적서 발행":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>📄"
      " 주식회사 범운해운항공 정식 견적서 발행</h3>",
      unsafe_allow_html=True,
  )

  q_col1, q_col2 = st.columns(2)
  with q_col1:
    quote_client_options = (
        st.session_state.client_list
        if st.session_state.client_list
        else ["아코글로벌"]
    )
    selected_q_client = st.selectbox(
        "수신처 거래처 선택", options=quote_client_options
    )
    quote_date = st.date_input("시행일 (견적일자)", value=date.today())
    quote_no = st.text_input(
        "문서번호", value=f"범운-{date.today().strftime('%Y-%m%d')}-01"
    )

  with q_col2:
    quote_title = st.text_input(
        "견적 제목",
        value="보톡스 및 필러 제품 국가별 배송 스케줄, 운임 및 부피중량 기준 안내",
    )
    quote_manager = st.text_input(
        "수신 담당자 직위/성명", value="고객사 담당자 귀하"
    )

  st.markdown("---")
  if "quote_items_df" not in st.session_state:
    st.session_state.quote_items_df = pd.DataFrame([
        {
            "국가": "미국 (USA)",
            "발송 스케줄": "화요일, 토요일만 발송",
            "kg당 운임": "40,000원 / kg",
            "부피중량 적용 (Divisor)": 6000,
        }
    ])

  edited_quote_table = st.data_editor(
      st.session_state.quote_items_df,
      num_rows="dynamic",
      use_container_width=True,
      key="quote_editor_table",
  )
  st.session_state.quote_items_df = edited_quote_table.copy()

  quote_items = edited_quote_table.fillna("").to_dict("records")
  quote_html = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>범운해운항공 견적서</title>
<style>
@page {{ size: A4; margin: 16mm; }}
body {{ font-family: Arial, 'Malgun Gothic', sans-serif; color:#172033; margin:0; }}
.sheet {{ width:100%; }} h1 {{ text-align:center; font-size:26px; margin:8px 0 28px; }}
.top {{ display:flex; justify-content:space-between; gap:20px; margin-bottom:20px; }}
.meta {{ border-collapse:collapse; width:100%; margin:12px 0 20px; }}
th,td {{ border:1px solid #64748b; padding:9px; font-size:12px; text-align:left; }}
th {{ background:#f1f5f9; width:24%; }}
.items th {{ text-align:center; }} .sign {{ margin-top:42px; text-align:right; font-size:15px; font-weight:bold; }}
@media screen {{ body {{ padding:20px; }} .sheet {{ max-width:800px; margin:auto; }} }}
</style></head><body><div class="sheet">
<h1>견 적 서</h1>
<div class="top"><div><b>수신:</b> {quote_manager}<br><b>거래처:</b> {selected_q_client}</div>
<div><b>문서번호:</b> {quote_no}<br><b>시행일:</b> {quote_date}</div></div>
<p><b>제목:</b> {quote_title}</p>
<table class="meta"><tr><th>발행사</th><td>주식회사 범운해운항공</td></tr>
<tr><th>영문명</th><td>BUMWOON OCEAN &amp; AIR CO., LTD.</td></tr>
<tr><th>견적 안내</th><td>아래 조건을 기준으로 견적 내용을 안내드립니다.</td></tr></table>
<table class="meta items"><thead><tr>{''.join(f'<th>{col}</th>' for col in edited_quote_table.columns)}</tr></thead><tbody>
{''.join('<tr>'+''.join(f'<td>{str(row.get(col, ""))}</td>' for col in edited_quote_table.columns)+'</tr>' for row in quote_items)}
</tbody></table>
<p>※ 운임 및 발송 일정은 실제 화물 정보, 운송 상황 및 현지 조건에 따라 변경될 수 있습니다.</p>
<div class="sign">주식회사 범운해운항공</div>
</div><script>window.onload=function(){{setTimeout(function(){{window.print();}},300);}};</script></body></html>"""

  quote_col1, quote_col2 = st.columns(2)
  with quote_col1:
    if st.button("💾 견적서 저장", type="primary", use_container_width=True):
      quote_record = {
          "문서번호": quote_no,
          "견적일자": str(quote_date),
          "거래처": selected_q_client,
          "수신담당자": quote_manager,
          "견적제목": quote_title,
          "견적항목_JSON": json.dumps(quote_items, ensure_ascii=False),
      }
      try:
        if os.path.exists(QUOTATION_FILE):
          old_quotes = pd.read_csv(QUOTATION_FILE).to_dict("records")
        else:
          old_quotes = []
        old_quotes = [r for r in old_quotes if str(r.get("문서번호", "")) != str(quote_no)]
        old_quotes.append(quote_record)
        pd.DataFrame(old_quotes).to_csv(QUOTATION_FILE, index=False, encoding="utf-8-sig")
        st.success("견적서를 quotation_data.csv에 저장했습니다.")
      except Exception as e:
        st.error(f"견적서 저장 중 오류가 발생했습니다: {e}")
  with quote_col2:
    st.download_button(
        "📥 견적서 HTML 다운로드 / PDF 저장",
        data=quote_html.encode("utf-8-sig"),
        file_name=f"견적서_{quote_no}.html",
        mime="text/html",
        use_container_width=True,
    )
  with st.expander("견적서 미리보기"):
    components.html(quote_html.replace("<script>window.onload=function(){setTimeout(function(){window.print();},300);};</script>", ""), height=650, scrolling=True)


# ==========================================
# [6] 거래처 미팅 노트
# ==========================================
elif selected_menu == "🤝 거래처 미팅 노트":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>🤝"
      " 거래처 미팅 및 영업 상담 노트</h3>",
      unsafe_allow_html=True,
  )

  with st.form("meeting_form"):
    m_col1, m_col2 = st.columns(2)
    with m_col1:
      m_client_options = (
          st.session_state.client_list
          if st.session_state.client_list
          else ["아코글로벌"]
      )
      m_client = st.selectbox("상담 거래처", options=m_client_options)
      m_date = st.date_input("미팅 날짜", value=date.today())
    with m_col2:
      m_manager = st.text_input("상대 담당자 성명", value="담당자")
      m_title = st.text_input("미팅 제목 / 요건", value="화물 단가 협의")

    m_content = st.text_area("미팅 상세 내용", value="내용 입력...")
    m_action = st.text_area("향후 조치 사항", value="견적서 송부")

    if st.form_submit_button("💾 미팅 노트 저장하기", type="primary"):
      st.session_state.meeting_data_list.append({
          "날짜": str(m_date),
          "거래처": m_client,
          "담당자": m_manager,
          "제목": m_title,
          "상세내용": m_content,
          "향후조치": m_action,
          "작성자": current_user_name,
      })
      save_meeting_data(st.session_state.meeting_data_list)
      st.success("미팅 노트가 저장되었습니다!")
      st.rerun()

  if st.session_state.meeting_data_list:
    st.data_editor(
        pd.DataFrame(st.session_state.meeting_data_list),
        use_container_width=True,
        key="meeting_table_edit",
    )

# ==========================================
# [7] 금일발송 매니페스트 (사내용 / 거래처 공유용 탭 통합)
# ==========================================
elif selected_menu == "📋 금일발송 매니페스트":
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 15px;'>📋 날짜별 발송 화물 매니페스트 및 입고 LIST</h3>",
        unsafe_allow_html=True,
    )

    tab_internal, tab_external = st.tabs(["🔒 사내 정산용 (매출/매입/Profit 포함)", "📤 거래처 공유용 입고 LIST (금액 제외)"])

    # -------------------------------------------------------------
    # 1️⃣ [탭 1] 사내 정산용 (매출, 매입, Profit + 맨 아래 합계 행 포함 + A4 가로 맞춤 엑셀)
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
                
                # ➕ 매출, 매입, Profit 총합계 행 계산
                total_sales_sum = manifest_display_df["매출액(원)"].sum()
                total_purchase_sum = manifest_display_df["매입액(원)"].sum()
                total_profit_sum = manifest_display_df["Profit(원)"].sum()

                summary_row = pd.DataFrame([{
                    "날짜": "합계",
                    "B/L 번호": f"총 {len(manifest_display_df)}건",
                    "화주명(매출)": "",
                    "해외수하인": "",
                    "박스수": "",
                    "부피규격": "",
                    "매출청구중량(kg)": manifest_display_df["매출청구중량(kg)"].sum(),
                    "매입처": "",
                    "매출액(원)": total_sales_sum,
                    "매입액(원)": total_purchase_sum,
                    "Profit(원)": total_profit_sum,
                }])
                
                # 화면 표시용 데이터프레임 (단위 서식 적용)
                display_view_df = pd.concat([manifest_display_df, summary_row], ignore_index=True)
                display_view_df["매출청구중량(kg)"] = display_view_df["매출청구중량(kg)"].apply(lambda x: f"{x:.1f} kg" if pd.notna(x) and x != "" else "")
                display_view_df["매출액(원)"] = display_view_df["매출액(원)"].apply(lambda x: f"{int(x):,} 원" if pd.notna(x) and x != "" else "")
                display_view_df["매입액(원)"] = display_view_df["매입액(원)"].apply(lambda x: f"{int(x):,} 원" if pd.notna(x) and x != "" else "")
                display_view_df["Profit(원)"] = display_view_df["Profit(원)"].apply(lambda x: f"{int(x):,} 원" if pd.notna(x) and x != "" else "")

                st.dataframe(display_view_df, use_container_width=True)

                # A4 가로 1페이지 자동 맞춤 + 합계 행 강조 엑셀 생성
                excel_buffer = io.BytesIO()
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "사내매니페스트"

                ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
                ws.page_setup.paperSize = ws.PAPERSIZE_A4
                ws.sheet_properties.pageSetUpPr.fitToPage = True
                ws.page_setup.fitToWidth = 1
                ws.page_setup.fitToHeight = 0

                header_fill = openpyxl.styles.PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
                summary_fill = openpyxl.styles.PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
                
                header_font = openpyxl.styles.Font(name="맑은 고딕", size=10, bold=True, color="FFFFFF")
                data_font = openpyxl.styles.Font(name="맑은 고딕", size=9)
                summary_font = openpyxl.styles.Font(name="맑은 고딕", size=9.5, bold=True)
                
                thin_border = openpyxl.styles.Border(
                    left=openpyxl.styles.Side(style='thin', color='CBD5E1'),
                    right=openpyxl.styles.Side(style='thin', color='CBD5E1'),
                    top=openpyxl.styles.Side(style='thin', color='CBD5E1'),
                    bottom=openpyxl.styles.Side(style='thin', color='CBD5E1')
                )
                summary_border = openpyxl.styles.Border(
                    left=openpyxl.styles.Side(style='thin', color='CBD5E1'),
                    right=openpyxl.styles.Side(style='thin', color='CBD5E1'),
                    top=openpyxl.styles.Side(style='medium', color='0F172A'),
                    bottom=openpyxl.styles.Side(style='double', color='0F172A')
                )

                center_align = openpyxl.styles.Alignment(horizontal='center', vertical='center')
                right_align = openpyxl.styles.Alignment(horizontal='right', vertical='center')
                left_align = openpyxl.styles.Alignment(horizontal='left', vertical='center')

                # 원본 데이터와 합계 행을 결합하여 엑셀로 출력
                excel_export_df = pd.concat([manifest_display_df, summary_row], ignore_index=True)

                headers = list(excel_export_df.columns)
                ws.append(headers)

                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = center_align

                for row in excel_export_df.itertuples(index=False):
                    ws.append(list(row))

                max_r = ws.max_row
                for row_idx in range(2, max_r + 1):
                    is_summary_row = (row_idx == max_r) # 마지막 행이 합계 행
                    for col_idx in range(1, ws.max_column + 1):
                        cell = ws.cell(row=row_idx, column=col_idx)
                        
                        if is_summary_row:
                            cell.font = summary_font
                            cell.fill = summary_fill
                            cell.border = summary_border
                        else:
                            cell.font = data_font
                            cell.border = thin_border

                        # 열별 정렬 및 숫자 천단위 쉼표 서식
                        if col_idx in [1, 2, 5, 7, 8]:
                            cell.alignment = center_align
                        elif col_idx in [9, 10, 11]:
                            cell.alignment = right_align
                            cell.number_format = '#,##0'
                        else:
                            cell.alignment = left_align

                col_widths = {
                    'A': 12, 'B': 14, 'C': 18, 'D': 16, 'E': 10, 
                    'F': 18, 'G': 14, 'H': 16, 'I': 14, 'J': 14, 'K': 14
                }
                for col_letter, width in col_widths.items():
                    ws.column_dimensions[col_letter].width = width

                wb.save(excel_buffer)
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
    # 2️⃣ [탭 2] 거래처 공유용 입고 LIST (매입처별 필터 & 전화번호 포함)
    # -------------------------------------------------------------
    with tab_external:
        st.markdown("##### 📦 입고 LIST (매입처별 / 금액 제외 / 전화번호 포함)")
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
            available_suppliers = sorted(list(set(str(r.get("매입처", "-")) for r in share_shipments if str(r.get("매입처", "-")).strip())))
            supplier_filter_options = ["전체 매입처 보기"] + available_suppliers
            
            with m_col_e2:
                selected_supplier_filter = st.selectbox(
                    "2️⃣ 매입처 선택", options=supplier_filter_options, key="manifest_supplier_select_share"
                )

            filtered_share_shipments = share_shipments if selected_supplier_filter == "전체 매입처 보기" else [
                item for item in share_shipments if str(item.get("매입처", "-")).strip() == selected_supplier_filter
            ]

            if filtered_share_shipments:
                st.markdown(f"#### 📦 입고 LIST - [{share_date_str}] (총 <span style='color: #2563eb;'>{len(filtered_share_shipments)}</span>건)", unsafe_allow_html=True)

                share_rows = []
                for idx, r_m in enumerate(filtered_share_shipments, 1):
                    def clean_val(v):
                        if v is None:
                            return ""
                        s = str(v).strip()
                        if s.lower() in ["nan", "none", "", "null"]:
                            return ""
                        return s

                    gw_val = clean_val(r_m.get("실중량(kg)", r_m.get("매출실중량(kg)")))
                    if gw_val:
                        try:
                            gw_str = f"{float(gw_val):.2f}"
                        except:
                            gw_str = gw_val
                    else:
                        gw_str = ""

                    share_rows.append({
                        "NO": idx,
                        "입고날짜": str(r_m.get("날짜", share_date_str))[:10],
                        "B/L 번호": clean_val(r_m.get("B/L 번호")),
                        "실중량(kg)": gw_str,
                        "부피규격(사이즈)": clean_val(r_m.get("부피규격")),
                        "수하인": clean_val(r_m.get("해외수하인")),
                        "수하인 전화번호": clean_val(r_m.get("해외수하인전화번호")),
                        "수하인 주소": clean_val(r_m.get("해외수하인주소")),
                    })

                share_display_df = pd.DataFrame(share_rows)

                st.markdown(
                    """
                    <style>
                    table { font-size: 14px !important; }
                    th { font-size: 14.5px !important; background-color: #1e3a8a !important; color: white !important; text-align: center !important; }
                    td { font-size: 13.5px !important; padding: 10px 8px !important; }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                
                st.dataframe(share_display_df, use_container_width=True, hide_index=True)

                excel_buffer_share = io.BytesIO()
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "입고LIST"

                ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
                ws.page_setup.paperSize = ws.PAPERSIZE_A4
                ws.sheet_properties.pageSetUpPr.fitToPage = True
                ws.page_setup.fitToWidth = 1
                ws.page_setup.fitToHeight = 0

                header_fill = openpyxl.styles.PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
                header_font = openpyxl.styles.Font(name="맑은 고딕", size=10.5, bold=True, color="FFFFFF")
                data_font = openpyxl.styles.Font(name="맑은 고딕", size=9.5)
                thin_border = openpyxl.styles.Border(
                    left=openpyxl.styles.Side(style='thin', color='D9D9D9'),
                    right=openpyxl.styles.Side(style='thin', color='D9D9D9'),
                    top=openpyxl.styles.Side(style='thin', color='D9D9D9'),
                    bottom=openpyxl.styles.Side(style='thin', color='D9D9D9')
                )
                center_align = openpyxl.styles.Alignment(horizontal='center', vertical='center')
                left_align = openpyxl.styles.Alignment(horizontal='left', vertical='center')

                headers = list(share_display_df.columns)
                ws.append(headers)

                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = center_align

                for row in share_display_df.itertuples(index=False):
                    ws.append(list(row))

                for row_idx in range(2, ws.max_row + 1):
                    for col_idx in range(1, ws.max_column + 1):
                        cell = ws.cell(row=row_idx, column=col_idx)
                        cell.font = data_font
                        cell.border = thin_border
                        if col_idx in [1, 2, 3, 4]:
                            cell.alignment = center_align
                        else:
                            cell.alignment = left_align

                col_widths = {'A': 6, 'B': 12, 'C': 14, 'D': 10, 'E': 22, 'F': 14, 'G': 16, 'H': 38}
                for col_letter, width in col_widths.items():
                    ws.column_dimensions[col_letter].width = width

                wb.save(excel_buffer_share)
                excel_data_share = excel_buffer_share.getvalue()

                st.download_button(
                    label="📥 입고리스트 엑셀 다운로드 (.xlsx)",
                    data=excel_data_share,
                    file_name=f"입고LIST_{share_date_str}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.warning("⚠️ 선택하신 매입처 조건에 해당하는 선적 내역이 없습니다.")
        else:
            st.info("해당 날짜에 등록된 선적 내역이 없습니다.")
# ==========================================
# [8] 매출 거래처(화주) 관리 (메인 메뉴 독립)
# ==========================================
elif selected_menu == "🏢 매출 거래처(화주) 관리":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>🏢"
      " 매출 거래처(화주) 및 단가 요율 관리</h3>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748b; font-size: 13px; margin-bottom: 15px;'>매출"
      " 거래처(화주)의 기본 정보 및 국가·운송형태별 단가 요율표를"
      " 관리합니다.</p>",
      unsafe_allow_html=True,
  )

  with st.expander("➕ 신규 매출 거래처(화주) 추가하기", expanded=False):
    new_client_name_input = st.text_input(
        "신규 매출 거래처명 입력", key="new_client_input_key"
    )
    if st.button("매출 거래처 추가", key="btn_add_client"):
      if (
          new_client_name_input.strip()
          and new_client_name_input not in st.session_state.client_list
      ):
        st.session_state.client_list.append(new_client_name_input.strip())
        st.session_state.client_infos[new_client_name_input.strip()] = {
            "사업자등록번호": "",
            "이메일": "",
            "담당자": "",
            "전화번호": "",
            "주소": "",
        }
        save_client_data(
            st.session_state.client_list,
            st.session_state.client_rates,
            st.session_state.client_infos,
        )
        st.success(f"매출 거래처 '{new_client_name_input}'가 추가되었습니다!")
        st.rerun()

  st.markdown("---")

  if st.session_state.client_list:
    selected_client_mgr = st.selectbox(
        "관리할 매출 거래처 선택",
        options=st.session_state.client_list,
        key="select_client_mgr_key",
    )
    c_info = st.session_state.client_infos.get(selected_client_mgr, {})

    with st.form("client_info_form"):
      st.markdown(f"#### 🏢 [{selected_client_mgr}] 매출 거래처 기본 정보 수정")
      ci_bno = st.text_input(
          "사업자등록번호", value=c_info.get("사업자등록번호", "")
      )
      ci_email = st.text_input("세금계산서 이메일", value=c_info.get("이메일", ""))
      ci_mgr = st.text_input("담당자 성명", value=c_info.get("담당자", ""))
      ci_tel = st.text_input("전화번호", value=c_info.get("전화번호", ""))
      ci_addr = st.text_input("사업장 주소", value=c_info.get("주소", ""))

      if st.form_submit_button("💾 매출 거래처 정보 저장", type="primary"):
        st.session_state.client_infos[selected_client_mgr] = {
            "사업자등록번호": ci_bno,
            "이메일": ci_email,
            "담당자": ci_mgr,
            "전화번호": ci_tel,
            "주소": ci_addr,
        }
        save_client_data(
            st.session_state.client_list,
            st.session_state.client_rates,
            st.session_state.client_infos,
        )
        st.success(f"[{selected_client_mgr}] 매출 거래처 정보가 저장되었습니다!")

    st.markdown("---")
    st.markdown("#### 🗑 매출 거래처 삭제")
    if st.button("🚨 선택한 매출 거래처 삭제하기", type="secondary"):
      if len(st.session_state.client_list) > 1:
        target_c = selected_client_mgr
        st.session_state.client_list.remove(target_c)
        if target_c in st.session_state.client_infos:
          del st.session_state.client_infos[target_c]
        if target_c in st.session_state.client_rates:
          del st.session_state.client_rates[target_c]
        save_client_data(
            st.session_state.client_list,
            st.session_state.client_rates,
            st.session_state.client_infos,
        )
        st.success("매출 거래처가 삭제되었습니다.")
        st.rerun()
      else:
        st.warning("최소 1개의 매출 거래처는 유지되어야 합니다.")

    st.markdown("---")
    st.markdown(
        f"#### 📊 [{selected_client_mgr}] 국가별·운송형태별 매출 단가 및 요율표"
    )

    rates_dict = st.session_state.client_rates.get(selected_client_mgr, {})
    rate_rows = []
    for country, trans_dict in rates_dict.items():
      if isinstance(trans_dict, dict):
        for transport, item_dict in trans_dict.items():
          if isinstance(item_dict, dict):
            for item_name, r_val in item_dict.items():
              rate_rows.append({
                  "국가": country if country else "미국",
                  "운송형태": (
                      transport
                      if transport and transport != "None"
                      else "항공(Air)"
                  ),
                  "품명": (
                      item_name if item_name in ["보톡스", "필러", "화장품", "특가품목", "의약품", "일반화물", "기타"]
                      else "기타(직접입력)"
                  ),
                  "기타 품목 직접입력": (
                      "" if item_name in ["보톡스", "필러", "화장품", "특가품목", "의약품", "일반화물", "기타"]
                      else (item_name if item_name and item_name != "None" else "")
                  ),
                  "기본중량(kg)": float(r_val.get("기본중량", 1.0)),
                  "기본요금(원)": int(r_val.get("기본요금", 38000)),
                  "추가단가(원/kg)": int(r_val.get("추가단가", 25000)),
                  "1CBM당단가(원)": int(r_val.get("1CBM당단가", 3700000)),
              })

    if not rate_rows:
      rate_rows = [{
          "국가": "미국",
          "운송형태": "항공(Air)",
          "품명": "일반화물",
          "기타 품목 직접입력": "",
          "기본중량(kg)": 1.0,
          "기본요금(원)": 38000,
          "추가단가(원/kg)": 25000,
          "1CBM당단가(원)": 3700000,
      }]

    df_rates = pd.DataFrame(rate_rows)
    if "선택" not in df_rates.columns:
      df_rates.insert(0, "선택", False)

    st.caption("품목 선택: 보톡스 · 필러 · 화장품 · 특가품목 · 의약품 · 기타. 기타 품목은 오른쪽 '기타 품목 직접입력' 칸에 직접 입력하세요.")
    edited_rates_df = st.data_editor(
        df_rates,
        hide_index=True,
        use_container_width=True,
        column_config={
            "선택": st.column_config.CheckboxColumn(required=True),
            "국가": st.column_config.SelectboxColumn(
                "국가", options=COUNTRY_LIST, required=True
            ),
            "운송형태": st.column_config.SelectboxColumn(
                "운송형태",
                options=["항공(Air)", "해상(LCL)", "에어카고"],
                required=True,
            ),
            "품명": st.column_config.SelectboxColumn(
                "품명",
                options=["보톡스", "필러", "화장품", "특가품목", "의약품", "일반화물", "기타", "기타(직접입력)"],
                required=True,
            ),
            "기타 품목 직접입력": st.column_config.TextColumn("기타 품목 직접입력", help="기타를 선택한 경우 품목명을 직접 입력하세요."),
        },
        num_rows="dynamic",
        key=f"rate_editor_{selected_client_mgr}",
    )

    r_col1, r_col2 = st.columns(2)
    with r_col1:
      if st.button("💾 매출 요율표 저장하기", type="primary", use_container_width=True):
        new_rates_dict = {}
        for _, row in edited_rates_df.iterrows():
          c_cntry = str(row.get("국가", "미국")).strip()
          c_trans = str(row.get("운송형태", "항공(Air)")).strip()
          c_item = _client_text(row.get("기타 품목 직접입력", ""), "") if str(row.get("품명", "")).strip() == "기타(직접입력)" else _client_text(row.get("품명", "일반화물"), "일반화물")
          if c_cntry and c_trans and c_item:
            if c_cntry not in new_rates_dict:
              new_rates_dict[c_cntry] = {}
            if c_trans not in new_rates_dict[c_cntry]:
              new_rates_dict[c_cntry][c_trans] = {}
            new_rates_dict[c_cntry][c_trans][c_item] = {
                "기본중량": _client_safe_number(row.get("기본중량(kg)", 1.0), 1.0),
                "기본요금": _client_safe_number(row.get("기본요금(원)", 38000), 38000, as_int=True),
                "추가단가": _client_safe_number(row.get("추가단가(원/kg)", 25000), 25000, as_int=True),
                "1CBM당단가": _client_safe_number(row.get("1CBM당단가(원)", 3700000), 3700000, as_int=True),
            }
        st.session_state.client_rates[selected_client_mgr] = new_rates_dict
        save_client_data(
            st.session_state.client_list,
            st.session_state.client_rates,
            st.session_state.client_infos,
        )
        st.success("매출 단가 및 요율표가 저장되었습니다!")
        st.rerun()

    with r_col2:
      if st.button("🗑 선택한 매출 요율 행 삭제", use_container_width=True):
        selected_rate_rows = edited_rates_df[edited_rates_df["선택"] == True]
        if not selected_rate_rows.empty:
          remaining_rates_df = edited_rates_df[edited_rates_df["선택"] == False]
          new_rates_dict = {}
          for _, row in remaining_rates_df.iterrows():
            c_cntry = str(row.get("국가", "미국")).strip()
            c_trans = str(row.get("운송형태", "항공(Air)")).strip()
            c_item = _client_text(row.get("기타 품목 직접입력", ""), "") if str(row.get("품명", "")).strip() == "기타(직접입력)" else _client_text(row.get("품명", "일반화물"), "일반화물")
            if c_cntry and c_trans and c_item:
              if c_cntry not in new_rates_dict:
                new_rates_dict[c_cntry] = {}
              if c_trans not in new_rates_dict[c_cntry]:
                new_rates_dict[c_cntry][c_trans] = {}
              new_rates_dict[c_cntry][c_trans][c_item] = {
                  "기본중량": _client_safe_number(row.get("기본중량(kg)", 1.0), 1.0),
                  "기본요금": _client_safe_number(row.get("기본요금(원)", 38000), 38000, as_int=True),
                  "추가단가": _client_safe_number(row.get("추가단가(원/kg)", 25000), 25000, as_int=True),
                  "1CBM당단가": _client_safe_number(row.get("1CBM당단가(원)", 3700000), 3700000, as_int=True),
              }
          st.session_state.client_rates[selected_client_mgr] = new_rates_dict
          save_client_data(
              st.session_state.client_list,
              st.session_state.client_rates,
              st.session_state.client_infos,
          )
          st.success("선택한 요율 행이 삭제되었습니다.")
          st.rerun()
        else:
          st.warning("삭제할 요율 행의 체크박스를 선택해주세요.")


# ==========================================
# [9] 매입 거래처(선사/협력사) 관리 (메인 메뉴 독립)
# ==========================================
elif selected_menu == "🚢 매입 거래처(선사/협력사) 관리":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>🚢"
      " 매입 거래처(선사/항공사/협력사) 및 단가 요율 관리</h3>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748b; font-size: 13px; margin-bottom: 15px;'>매입"
      " 거래처의 기본 정보 및 국가·운송형태별 매입 단가 요율표를 관리합니다.</p>",
      unsafe_allow_html=True,
  )

  with st.expander("➕ 신규 매입 거래처 추가하기", expanded=False):
    new_supplier_name_input = st.text_input(
        "신규 매입 거래처명 입력", key="new_supplier_input_key"
    )
    if st.button("매입 거래처 추가", key="btn_add_supplier"):
      if (
          new_supplier_name_input.strip()
          and new_supplier_name_input not in st.session_state.supplier_list
      ):
        st.session_state.supplier_list.append(new_supplier_name_input.strip())
        st.session_state.supplier_infos[new_supplier_name_input.strip()] = {
            "사업자등록번호": "",
            "이메일": "",
            "담당자": "",
            "전화번호": "",
            "주소": "",
        }
        save_supplier_data(
            st.session_state.supplier_list,
            st.session_state.supplier_rates,
            st.session_state.supplier_infos,
        )
        st.success(f"매입 거래처 '{new_supplier_name_input}'가 추가되었습니다!")
        st.rerun()

  st.markdown("---")

  if st.session_state.supplier_list:
    selected_supplier_mgr = st.selectbox(
        "관리할 매입 거래처 선택",
        options=st.session_state.supplier_list,
        key="select_supplier_mgr_key",
    )
    s_info = st.session_state.supplier_infos.get(selected_supplier_mgr, {})

    with st.form("supplier_info_form"):
      st.markdown(f"#### 🚢 [{selected_supplier_mgr}] 매입 거래처 기본 정보 수정")
      si_bno = st.text_input(
          "사업자등록번호",
          value=s_info.get("사업자등록번호", ""),
          key="s_bno",
      )
      si_email = st.text_input(
          "세금계산서 이메일", value=s_info.get("이메일", ""), key="s_email"
      )
      si_mgr = st.text_input(
          "담당자 성명", value=s_info.get("담당자", ""), key="s_mgr"
      )
      si_tel = st.text_input(
          "전화번호", value=s_info.get("전화번호", ""), key="s_tel"
      )
      si_addr = st.text_input(
          "사업장 주소", value=s_info.get("주소", ""), key="s_addr"
      )

      if st.form_submit_button("💾 매입 거래처 정보 저장", type="primary"):
        st.session_state.supplier_infos[selected_supplier_mgr] = {
            "사업자등록번호": si_bno,
            "이메일": si_email,
            "담당자": si_mgr,
            "전화번호": si_tel,
            "주소": si_addr,
        }
        save_supplier_data(
            st.session_state.supplier_list,
            st.session_state.supplier_rates,
            st.session_state.supplier_infos,
        )
        st.success(f"[{selected_supplier_mgr}] 매입 거래처 정보가 저장되었습니다!")

    st.markdown("---")
    st.markdown("#### 🗑 매입 거래처 삭제")
    if st.button("🚨 선택한 매입 거래처 삭제하기", type="secondary"):
      if len(st.session_state.supplier_list) > 1:
        target_s = selected_supplier_mgr
        st.session_state.supplier_list.remove(target_s)
        if target_s in st.session_state.supplier_infos:
          del st.session_state.supplier_infos[target_s]
        if target_s in st.session_state.supplier_rates:
          del st.session_state.supplier_rates[target_s]
        save_supplier_data(
            st.session_state.supplier_list,
            st.session_state.supplier_rates,
            st.session_state.supplier_infos,
        )
        st.success("매입 거래처가 삭제되었습니다.")
        st.rerun()
      else:
        st.warning("최소 1개의 매입 거래처는 유지되어야 합니다.")

    st.markdown("---")
    st.markdown(
        f"#### 📊 [{selected_supplier_mgr}] 국가별·운송형태별 매입 단가 및 요율표"
    )

    supp_rates_dict = st.session_state.supplier_rates.get(
        selected_supplier_mgr, {}
    )
    supp_rate_rows = []
    for country, trans_dict in supp_rates_dict.items():
      if isinstance(trans_dict, dict):
        for transport, item_dict in trans_dict.items():
          if isinstance(item_dict, dict):
            for item_name, r_val in item_dict.items():
              supp_rate_rows.append({
                  "국가": country if country else "미국",
                  "운송형태": (
                      transport
                      if transport and transport != "None"
                      else "항공(Air)"
                  ),
                  "품명": (
                      item_name if item_name in ["보톡스", "필러", "화장품", "특가품목", "의약품", "일반화물", "기타"]
                      else "기타(직접입력)"
                  ),
                  "기타 품목 직접입력": (
                      "" if item_name in ["보톡스", "필러", "화장품", "특가품목", "의약품", "일반화물", "기타"]
                      else (item_name if item_name and item_name != "None" else "")
                  ),
                  "기본중량(kg)": float(r_val.get("기본중량", 1.0)),
                  "기본요금(원)": int(r_val.get("기본요금", 35000)),
                  "추가단가(원/kg)": int(r_val.get("추가단가", 22000)),
                  "1CBM당단가(원)": int(r_val.get("1CBM당단가", 3500000)),
              })

    if not supp_rate_rows:
      supp_rate_rows = [{
          "국가": "미국",
          "운송형태": "항공(Air)",
          "품명": "일반화물",
          "기타 품목 직접입력": "",
          "기본중량(kg)": 1.0,
          "기본요금(원)": 35000,
          "추가단가(원/kg)": 22000,
          "1CBM당단가(원)": 3500000,
      }]

    df_supp_rates = pd.DataFrame(supp_rate_rows)
    if "선택" not in df_supp_rates.columns:
      df_supp_rates.insert(0, "선택", False)

    st.caption("품목 선택: 보톡스 · 필러 · 화장품 · 특가품목 · 의약품 · 기타. 기타 품목은 오른쪽 '기타 품목 직접입력' 칸에 직접 입력하세요.")
    edited_supp_rates_df = st.data_editor(
        df_supp_rates,
        hide_index=True,
        use_container_width=True,
        column_config={
            "선택": st.column_config.CheckboxColumn(required=True),
            "국가": st.column_config.SelectboxColumn(
                "국가", options=COUNTRY_LIST, required=True
            ),
            "운송형태": st.column_config.SelectboxColumn(
                "운송형태",
                options=["항공(Air)", "해상(LCL)", "에어카고"],
                required=True,
            ),
            "품명": st.column_config.SelectboxColumn(
                "품명",
                options=["보톡스", "필러", "화장품", "특가품목", "의약품", "일반화물", "기타", "기타(직접입력)"],
                required=True,
            ),
            "기타 품목 직접입력": st.column_config.TextColumn("기타 품목 직접입력", help="기타를 선택한 경우 품목명을 직접 입력하세요."),
        },
        num_rows="dynamic",
        key=f"supp_rate_editor_{selected_supplier_mgr}",
    )

    sr_col1, sr_col2 = st.columns(2)
    with sr_col1:
      if st.button("💾 매입 요율표 저장하기", type="primary", use_container_width=True):
        new_supp_rates_dict = {}
        for _, row in edited_supp_rates_df.iterrows():
          c_cntry = str(row.get("국가", "미국")).strip()
          c_trans = str(row.get("운송형태", "항공(Air)")).strip()
          c_item = _client_text(row.get("기타 품목 직접입력", ""), "") if str(row.get("품명", "")).strip() == "기타(직접입력)" else _client_text(row.get("품명", "일반화물"), "일반화물")
          if c_cntry and c_trans and c_item:
            if c_cntry not in new_supp_rates_dict:
              new_supp_rates_dict[c_cntry] = {}
            if c_trans not in new_supp_rates_dict[c_cntry]:
              new_supp_rates_dict[c_cntry][c_trans] = {}
            new_supp_rates_dict[c_cntry][c_trans][c_item] = {
                "기본중량": _client_safe_number(row.get("기본중량(kg)", 1.0), 1.0),
                "기본요금": _client_safe_number(row.get("기본요금(원)", 35000), 35000, as_int=True),
                "추가단가": _client_safe_number(row.get("추가단가(원/kg)", 22000), 22000, as_int=True),
                "1CBM당단가": _client_safe_number(row.get("1CBM당단가(원)", 3500000), 3500000, as_int=True),
            }
        st.session_state.supplier_rates[selected_supplier_mgr] = (
            new_supp_rates_dict
        )
        save_supplier_data(
            st.session_state.supplier_list,
            st.session_state.supplier_rates,
            st.session_state.supplier_infos,
        )
        st.success("매입 단가 및 요율표가 저장되었습니다!")
        st.rerun()

    with sr_col2:
      if st.button("🗑 선택한 매입 요율 행 삭제", use_container_width=True):
        selected_supp_rate_rows = edited_supp_rates_df[
            edited_supp_rates_df["선택"] == True
        ]
        if not selected_supp_rate_rows.empty:
          remaining_supp_rates_df = edited_supp_rates_df[
              edited_supp_rates_df["선택"] == False
          ]
          new_supp_rates_dict = {}
          for _, row in remaining_supp_rates_df.iterrows():
            c_cntry = str(row.get("국가", "미국")).strip()
            c_trans = str(row.get("운송형태", "항공(Air)")).strip()
            c_item = _client_text(row.get("기타 품목 직접입력", ""), "") if str(row.get("품명", "")).strip() == "기타(직접입력)" else _client_text(row.get("품명", "일반화물"), "일반화물")
            if c_cntry and c_trans and c_item:
              if c_cntry not in new_supp_rates_dict:
                new_supp_rates_dict[c_cntry] = {}
              if c_trans not in new_supp_rates_dict[c_cntry]:
                new_supp_rates_dict[c_cntry][c_trans] = {}
              new_supp_rates_dict[c_cntry][c_trans][c_item] = {
                  "기본중량": _client_safe_number(row.get("기본중량(kg)", 1.0), 1.0),
                  "기본요금": _client_safe_number(row.get("기본요금(원)", 35000), 35000, as_int=True),
                  "추가단가": _client_safe_number(row.get("추가단가(원/kg)", 22000), 22000, as_int=True),
                  "1CBM당단가": _client_safe_number(row.get("1CBM당단가(원)", 3500000), 3500000, as_int=True),
              }
          st.session_state.supplier_rates[selected_supplier_mgr] = (
              new_supp_rates_dict
          )
          save_supplier_data(
              st.session_state.supplier_list,
              st.session_state.supplier_rates,
              st.session_state.supplier_infos,
          )
          st.success("선택한 매입 요율 행이 삭제되었습니다.")
          st.rerun()
        else:
          st.warning("삭제할 요율 행의 체크박스를 선택해주세요.")


# ==========================================
# [10] 거래처 미수금관리
# ==========================================
elif selected_menu == "💵 거래처 미수금관리":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 5px;'>💵"
      " 거래처별 및 월별 미수금 수금 현황 관리</h3>",
      unsafe_allow_html=True,
  )

  if st.session_state.bl_data_list:
    df_unpaid = pd.DataFrame(st.session_state.bl_data_list)
    if "선택" not in df_unpaid.columns:
      df_unpaid.insert(0, "선택", False)
    if "수금상태" not in df_unpaid.columns:
      df_unpaid["수금상태"] = "미수"
    if "매출액(원)" in df_unpaid.columns:
      df_unpaid["매출액(원)"] = pd.to_numeric(df_unpaid["매출액(원)"], errors="coerce").fillna(0)

    # 날짜에서 연도-월(YYYY-MM) 추출 컬럼 생성
    df_unpaid["연월"] = df_unpaid["날짜"].astype(str).str[:7]
    available_months = sorted(df_unpaid["연월"].unique().tolist(), reverse=True)
    if not available_months:
      available_months = [date.today().strftime("%Y-%m")]

    # 필터 UI 레이아웃 (거래처 선택, 월별 선택, 미수 건만 보기)
    col_f1, col_f2, col_f3 = st.columns([2, 1.5, 1])
    with col_f1:
      client_filter_options = ["전체 거래처 보기"] + st.session_state.client_list
      selected_client_filter = st.selectbox(
          "🔍 조회할 거래처 선택하기", options=client_filter_options
      )
    with col_f2:
      month_filter_options = ["전체 기간(월별 전체 보기)"] + available_months
      selected_month_filter = st.selectbox(
          "📅 조회할 월(달력) 선택하기", options=month_filter_options
      )
    with col_f3:
      st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
      only_unpaid_flag = st.checkbox("📌 미수 건만 보기", value=True)

    # 1. 거래처 필터링
    df_filtered = df_unpaid.copy()
    if selected_client_filter != "전체 거래처 보기":
      df_filtered = df_filtered[
          df_filtered["화주명(매출)"].astype(str).str.strip()
          == str(selected_client_filter).strip()
      ]

    # 2. 월별(연도-월) 필터링
    if selected_month_filter != "전체 기간(월별 전체 보기)":
      df_filtered = df_filtered[df_filtered["연월"] == selected_month_filter]

    # 금액 집계 계산 (필터링된 기준)
    total_sales_sum = df_filtered["매출액(원)"].sum() if "매출액(원)" in df_filtered.columns else 0
    total_unpaid_sum = df_filtered[df_filtered["수금상태"].astype(str).str.strip() != "수금완료"]["매출액(원)"].sum() if "매출액(원)" in df_filtered.columns else 0

    # 미수금 요약 메트릭 카드 표시
    m_col1, m_col2 = st.columns(2)
    with m_col1:
      st.metric(label="📌 선택 기간 총 청구 매출액", value=f"{int(total_sales_sum):,} 원")
    with m_col2:
      st.metric(label="🚨 선택 기간 미수금 잔액", value=f"{int(total_unpaid_sum):,} 원")

    st.markdown("---")

    # 미수 건만 보기 적용
    df_table_view = df_filtered.copy()
    if only_unpaid_flag and not df_table_view.empty:
      df_table_view = df_table_view[
          df_table_view["수금상태"].astype(str).str.strip() != "수금완료"
      ]

    # 불필요한 임시 컬럼('연월')은 화면 표시에서 제외
    if "연월" in df_table_view.columns:
      df_table_view = df_table_view.drop(columns=["연월"])

    edited_unpaid_table = st.data_editor(
        df_table_view,
        hide_index=True,
        use_container_width=True,
        column_config={"선택": st.column_config.CheckboxColumn(required=True)},
        key="unpaid_filter_table",
    )

    selected_unpaid_rows = edited_unpaid_table[
        edited_unpaid_table["선택"] == True
    ]

    if st.button("💰 선택 건 [수금완료] 일괄처리", type="primary", use_container_width=True):
      if len(selected_unpaid_rows) > 0:
        for idx in selected_unpaid_rows.index.tolist():
          bl_num_target = selected_unpaid_rows.loc[idx, "B/L 번호"]
          # 원본 세션 데이터에서 해당 B/L 찾아 수금완료로 변경
          for real_i, original_item in enumerate(st.session_state.bl_data_list):
            if str(original_item.get("B/L 번호", "")) == str(bl_num_target):
              st.session_state.bl_data_list[real_i]["수금상태"] = "수금완료"
              st.session_state.bl_data_list[real_i]["최종수정자"] = current_user_name
        save_bl_data(st.session_state.bl_data_list)
        st.success("선택하신 건들이 '수금완료' 처리되었습니다!")
        st.rerun()
      else:
        st.warning("수금완료 처리할 B/L 행의 체크박스를 선택해주세요.")
  else:
    st.info("등록된 B/L 데이터가 없습니다.")
# ==========================================
# [💳 일계표 및 입출금 장부] 메뉴 (지급상태 추가 버전)
# ==========================================
elif selected_menu == "💳 일계표 및 입출금 장부":
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 15px;'>📊 일계표 및 입출금 장부 (지급 상태 관리)</h3>",
        unsafe_allow_html=True,
    )

    if "cashbook_list" not in st.session_state:
        st.session_state.cashbook_list = load_account_data()

    cashbook_data = st.session_state.cashbook_list

    # 1. 데이터에 '지급상태' 컬럼이 없으면 기본값('미지급') 자동 채우기
    for item in cashbook_data:
        if "지급상태" not in item:
            # 수입인 경우는 보통 '지급완료' 또는 빈값, 지출인 경우는 '미지급' 기본 세팅
            item["지급상태"] = "지급완료" if "수입" in str(item.get("구분", "")) else "미지급"

    # --- 2. 상단: 날짜별 필터 (달력 위젯 표시) 및 인쇄/다운로드 버튼 ---
    st.markdown("#### 📅 날짜별 조회 및 인쇄")
    
    col_f1, col_f2 = st.columns([1.5, 2])
    with col_f1:
        date_filter_mode = st.radio("조회 방식", ["전체 기간", "특정 날짜 선택"], horizontal=True, key="cash_filter_mode")
    
    selected_target_date = str(date.today())
    if date_filter_mode == "특정 날짜 선택":
        with col_f2:
            picked_date = st.date_input("📅 조회할 날짜 선택 (달력)", value=date.today(), key="cash_date_picker_calendar")
            selected_target_date = str(picked_date)

    # 데이터 필터링
    filtered_cash_data = []
    for item in cashbook_data:
        item_date = str(item.get("날짜", ""))[:10]
        if date_filter_mode == "전체 기간" or item_date == selected_target_date:
            filtered_cash_data.append(item)

    # --- 3. 통장 잔액 및 수입/지출 총액 요약 ---
    total_income = sum(
        float(str(item.get("금액(원)", 0)).replace(",", ""))
        for item in filtered_cash_data
        if "수입" in str(item.get("구분", ""))
    )
    total_expense = sum(
        float(str(item.get("금액(원)", 0)).replace(",", ""))
        for item in filtered_cash_data
        if "지출" in str(item.get("구분", ""))
    )
    current_balance = total_income - total_expense

    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric(label="📥 조회 기간 총 수입", value=f"{int(total_income):,} 원")
    with m_col2:
        st.metric(label="📤 조회 기간 총 지출", value=f"{int(total_expense):,} 원")
    with m_col3:
        st.metric(label="💰 합계 잔액", value=f"{int(current_balance):,} 원")

    st.markdown("---")

    # --- 4. 중단: 장부 내역 조회 및 편집/삭제 (지급상태 컬럼 셀렉트박스 지원) ---
    print_title = "전체 일계표" if date_filter_mode == "전체 기간" else f"{selected_target_date} 일계표"
    title_label = f"📋 등록된 장부 내역 (전체)" if date_filter_mode == "전체 기간" else f"📋 [{selected_target_date}] 일일 장부 내역"
    st.markdown(f"#### {title_label}")

    if filtered_cash_data:
        df_cash = pd.DataFrame(filtered_cash_data)
        if "선택" not in df_cash.columns:
            df_cash.insert(0, "선택", False)

        edited_cash_table = st.data_editor(
            df_cash,
            hide_index=True,
            use_container_width=True,
            column_config={
                "선택": st.column_config.CheckboxColumn("삭제 선택", default=False),
                "지급상태": st.column_config.SelectboxColumn(
                    "지급상태",
                    options=["지급완료", "미지급", ""],
                    required=False
                )
            },
            key=f"cashbook_table_editor_v2_{date_filter_mode}_{selected_target_date}",
            height=320,
        )

        c_btn1, c_btn2, c_btn3 = st.columns(3)
        with c_btn1:
            if st.button("💾 변경된 장부 내용 저장", type="primary", use_container_width=True):
                try:
                    saved_df = edited_cash_table.drop(columns=["선택"], errors="ignore").copy()
                    edited_records = saved_df.fillna("").to_dict(orient="records")
                    
                    for row in edited_records:
                        raw_amount = str(row.get("금액(원)", 0)).replace(",", "").replace("원", "").strip()
                        try:
                            row["금액(원)"] = float(raw_amount or 0)
                            if row["금액(원)"].is_integer():
                                row["금액(원)"] = int(row["금액(원)"])
                        except:
                            row["금액(원)"] = 0

                    st.session_state.cashbook_list = edited_records
                    save_account_data(edited_records)
                    st.success("일계표 변경 내용(지급상태 포함)이 저장되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 중 오류 발생: {e}")
        with c_btn2:
            if st.button("🚨 선택한 장부 내역 삭제", type="secondary", use_container_width=True):
                selected_del = edited_cash_table[edited_cash_table["선택"] == True]
                if not selected_del.empty:
                    del_signatures = set()
                    for _, row in selected_del.iterrows():
                        sig = (str(row.get("날짜", ""))[:10], str(row.get("구분", "")), str(row.get("항목", "")), str(row.get("금액(원)", "")))
                        del_signatures.add(sig)
                    
                    new_cash_list = []
                    for item in st.session_state.cashbook_list:
                        item_sig = (str(item.get("날짜", ""))[:10], str(item.get("구분", "")), str(item.get("항목", "")), str(item.get("금액(원)", "")))
                        if item_sig not in del_signatures:
                            new_cash_list.append(item)
                            
                    st.session_state.cashbook_list = new_cash_list
                    save_account_data(new_cash_list)
                    st.success("🗑️ 선택한 장부 내역이 삭제되었습니다.")
                    st.rerun()
                else:
                    st.warning("⚠️ 삭제할 행의 체크박스를 선택해주세요.")
        with c_btn3:
            # 보고서 인쇄 HTML 생성 (지급상태 포함)
            print_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @media print {{
                        body {{ -webkit-print-color-adjust: exact; }}
                        .no-print {{ display: none !important; }}
                        @page {{ size: A4 portrait; margin: 12mm; }}
                    }}
                    body {{ font-family: 'Pretendard', sans-serif; color: #1e293b; font-size: 9.5pt; margin: 0; padding: 15px; background: #fff; }}
                    .report-box {{ max-width: 780px; margin: 0 auto; border: 1.5px solid #cbd5e1; padding: 25px; border-radius: 8px; background: #ffffff; }}
                    .header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                    .header-table td {{ border: none; vertical-align: middle; }}
                    .approval-table {{ border-collapse: collapse; float: right; }}
                    .approval-table th, .approval-table td {{ border: 1px solid #64748b; font-size: 8pt; text-align: center; padding: 4px 8px; }}
                    .approval-table th {{ background-color: #f1f5f9; color: #334155; }}
                    .approval-sign {{ height: 40px; }}
                    .summary-card {{ flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; text-align: center; }}
                    .summary-card.income {{ border-left: 4px solid #2563eb; }}
                    .summary-card.expense {{ border-left: 4px solid #dc2626; }}
                    .summary-card.balance {{ border-left: 4px solid #0f172a; background: #f1f5f9; }}
                    .card-title {{ font-size: 8pt; color: #64748b; font-weight: bold; margin-bottom: 4px; }}
                    .card-val {{ font-size: 11pt; font-weight: bold; color: #0f172a; }}
                    .data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    .data-table th, .data-table td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: center; font-size: 9pt; }}
                    .data-table th {{ background-color: #0f172a; color: white; font-weight: 600; font-size: 9.5pt; }}
                    .data-table tr:nth-child(even) {{ background-color: #f8fafc; }}
                    .p-btn {{ display: block; width: 100%; background-color: #2563eb; color: white; text-align: center; padding: 12px; font-size: 11pt; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="report-box">
                    <button class="p-btn no-print" onclick="window.print()">🖨 일계표 보고서 인쇄 / PDF 저장</button>
                    <table class="header-table">
                        <tr>
                            <td>
                                <div style="font-size: 11pt; font-weight: bold; color: #2563eb; margin-bottom: 3px;">(주)범운해운항공</div>
                                <div style="font-size: 18pt; font-weight: 900; color: #0f172a; letter-spacing: -0.5px;">일일 자금 수지 및 일계표</div>
                                <div style="font-size: 8.5pt; color: #64748b; margin-top: 4px;">조회 기준: <b>{print_title}</b> | 발행일자: {date.today()}</div>
                            </td>
                            <td style="width: 180px;">
                                <table class="approval-table">
                                    <tr><th rowspan="2" style="width: 20px; background:#f8fafc;">결<br>재</th><th>담당</th><th>대표이사</th></tr>
                                    <tr><td class="approval-sign"></td><td class="approval-sign"></td></tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; border: none;">
                        <tr>
                            <td style="border: none; padding: 0 6px 0 0; width: 33%;">
                                <div class="summary-card income">
                                    <div class="card-title">총 수입 금액</div>
                                    <div class="card-val" style="color: #2563eb;">+{int(total_income):,} 원</div>
                                </div>
                            </td>
                            <td style="border: none; padding: 0 6px; width: 33%;">
                                <div class="summary-card expense">
                                    <div class="card-title">총 지출 금액</div>
                                    <div class="card-val" style="color: #dc2626;">-{int(total_expense):,} 원</div>
                                </div>
                            </td>
                            <td style="border: none; padding: 0 0 0 6px; width: 34%;">
                                <div class="summary-card balance">
                                    <div class="card-title">마감 잔액 (통장 잔액)</div>
                                    <div class="card-val">{int(current_balance):,} 원</div>
                                </div>
                            </td>
                        </tr>
                    </table>
                    <table class="data-table">
                        <tr>
                            <th style="width: 13%;">거래일자</th>
                            <th style="width: 12%;">구분</th>
                            <th style="width: 12%;">지급상태</th>
                            <th style="width: 18%;">항목</th>
                            <th style="width: 18%;">금액 (원)</th>
                            <th style="width: 27%;">적요 및 메모</th>
                        </tr>
            """
            for row in filtered_cash_data:
                io_gubun = str(row.get("구분", "-"))
                gubun_color = "#2563eb" if "수입" in io_gubun else "#dc2626"
                pay_status = str(row.get("지급상태", "미지급"))
                print_html += f"""
                        <tr>
                            <td>{row.get("날짜", "-")}</td>
                            <td style="font-weight: bold; color: {gubun_color};">{io_gubun}</td>
                            <td style="font-weight: bold;">{pay_status}</td>
                            <td>{row.get("항목", "-")}</td>
                            <td style="text-align: right; font-weight: bold;">{int(float(str(row.get("금액(원)", 0)).replace(",", "") or 0)):,} 원</td>
                            <td style="text-align: left; padding-left: 10px;">{row.get("적요", "-")}</td>
                        </tr>
                """
            print_html += f"""
                    </table>
                    <div style="margin-top: 35px; text-align: center; font-size: 10pt; color: #475569;">
                        상기와 같이 자금 입출금 내역을 보고합니다.<br><br>
                        <b style="font-size: 11pt; color: #0f172a;">주식회사 범운해운항공 대표이사 이상복 [직인생략]</b>
                    </div>
                </div>
            </body>
            </html>
            """
            
            if st.button("🖨 정식 일계표 보고서 인쇄 / PDF", type="primary", use_container_width=True):
                components.html(print_html, height=700, scrolling=True)
    else:
        st.info("조회된 장부 내역이 없습니다.")

    st.markdown("---")

    # --- 5. 하단: 새로운 수입 / 지출 등록 폼 (지급상태 선택 추가) ---
    st.markdown("#### ✍️ 새로운 수입 / 지출 장부 등록")

    with st.form("cashbook_register_form_v7"):
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            reg_date = st.date_input("거래 일자", value=date.today())
            io_gb = st.selectbox("입출금 구분", ["지출 (-)", "수입 (+)"])
        with f_col2:
            pay_status_input = st.selectbox("지급 상태", ["미지급", "지급완료", ""])
            amount = st.number_input("금액 (원)", min_value=0, step=1000, format="%d")
        with f_col3:
            cat_options = [
                "접대비",
                "주유비(차량유지비)",
                "통신비",
                "소모품비",
                "기타 잡비",
                "기타 영업수입",
                "운송료수입",
            ]
            category = st.selectbox("비용/수입 항목", cat_options)

        memo = st.text_input(
            "적요 및 메모", placeholder="예: 사무실 소모품 구입 등"
        )

        submitted_cash = st.form_submit_button(
            "➕ 장부 내역 등록하기", type="primary", use_container_width=True
        )
        if submitted_cash:
            if amount > 0:
                st.session_state.cashbook_list.append({
                    "날짜": str(reg_date),
                    "구분": io_gb,
                    "지급상태": pay_status_input,
                    "항목": category,
                    "금액(원)": int(amount),
                    "적요": memo if memo else "-",
                })
                save_account_data(st.session_state.cashbook_list)
                st.success("✅ 장부 내역이 지급 상태와 함께 등록되었습니다.")
                st.rerun()
            else:
                st.warning("⚠️ 금액은 0원보다 커야 합니다.")
# ==========================================
# [12] 업무용 일지
# ==========================================
elif selected_menu == "📝 업무용 일지":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>📝"
      " 사내 업무용 일지 및 메모장</h3>",
      unsafe_allow_html=True,
  )

  with st.form("note_form"):
    n_date = st.date_input("작성 일자", value=date.today())
    n_title = st.text_input("일지 제목", value="금일 주요 업무")
    n_body = st.text_area("일지 내용", value="업무 내용 입력...")

    if st.form_submit_button("💾 일지 저장", type="primary"):
      st.session_state.note_data_list.append({
          "날짜": str(n_date),
          "제목": n_title,
          "내용": n_body,
          "작성자": current_user_name,
      })
      save_note_data(st.session_state.note_data_list)
      st.success("업무 일지가 저장되었습니다!")
      st.rerun()


# ==========================================
# 고객사 계정 및 화물 접수 관리
# ==========================================
elif selected_menu == "🏢 고객사 계정 및 화물 접수 관리":
  _admin_customer_freight_menu()

# ==========================================
# [13] 직원 계정 관리 (대표님 전용)
# ==========================================
elif selected_menu == "🔑 직원 계정 관리 (대표님 전용)":
  if st.session_state.user_role != "관리자(대표)":
    st.error("접근 권한이 없습니다.")
    st.stop()

  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>🔑"
      " 사내 직원 계정 관리</h3>",
      unsafe_allow_html=True,
  )

  with st.form("new_account_form"):
    nc_id = st.text_input("신규 직원 아이디")
    nc_pw = st.text_input("초기 비밀번호", type="password")
    nc_name = st.text_input("직원 성명")
    nc_role = st.selectbox("권한 설정", ["직원", "관리자(대표)"])

    submit_new_acc = st.form_submit_button("➕ 사내 계정 생성하기", type="primary")

    if submit_new_acc:
      clean_id = str(nc_id).strip()
      clean_pw = str(nc_pw).strip()
      clean_name = str(nc_name).strip()

      if clean_id and clean_pw:
        # 세션 상태 및 DB 파일 업데이트
        if "user_db" not in st.session_state:
          st.session_state.user_db = load_user_db()
          
        st.session_state.user_db[clean_id] = {
            "pw": clean_pw,
            "role": nc_role,
            "name": clean_name if clean_name else clean_id,
        }
        save_user_db(st.session_state.user_db)
        st.success(f"🎉 직원 계정 [{clean_id}]({clean_name})이(가) 성공적으로 생성되었습니다!")
        st.rerun()
      else:
        st.warning("⚠️ 아이디와 비밀번호를 모두 정확히 입력해주세요.")

  # 현재 등록된 직원 계정 목록 표시
  st.markdown("---")
  st.markdown("#### 📋 등록된 사내 직원 계정 목록")
  if "user_db" in st.session_state and st.session_state.user_db:
    acc_list = []
    for uid, info in st.session_state.user_db.items():
      acc_list.append({
          "아이디": uid,
          "성명": info.get("name", ""),
          "권한": info.get("role", "직원")
      })
    st.dataframe(pd.DataFrame(acc_list), use_container_width=True)
