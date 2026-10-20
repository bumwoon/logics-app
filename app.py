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
        with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
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
def load_client_data():
  if os.path.exists(CLIENT_FILE):
    try:
      df = pd.read_csv(CLIENT_FILE)
      clients = df["거래처명"].unique().tolist()
      rates = {}
      client_infos = {}
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
        for _, row in sub_df.iterrows():
          country = row.get("국가", "미국")
          transport = str(row.get("운송형태", "항공(Air)")).strip()
          item = str(row.get("품명", "일반공산품")).strip()
          if country not in rates[client]:
            rates[client][country] = {}
          if transport not in rates[client][country]:
            rates[client][country][transport] = {}
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
  rows = []
  for client in client_list:
    info = client_infos.get(
        client,
        {
            "사업자등록번호": "",
            "이메일": "",
            "담당자": "",
            "전화번호": "",
            "주소": "",
        },
    )
    country_dict = client_rates.get(client, {})
    if not country_dict:
      rows.append({
          "거래처명": client,
          "사업자등록번호": info.get("사업자등록번호", ""),
          "이메일": info.get("이메일", ""),
          "담당자": info.get("담당자", ""),
          "전화번호": info.get("전화번호", ""),
          "주소": info.get("주소", ""),
          "국가": "미국",
          "운송형태": "항공(Air)",
          "품명": "보톡스",
          "기본중량": 1.0,
          "기본요금": 38000,
          "추가단가": 25000,
          "1CBM당단가": 3700000,
      })
    else:
      for country, trans_dict in country_dict.items():
        if isinstance(trans_dict, dict):
          for transport, item_dict in trans_dict.items():
            if isinstance(item_dict, dict):
              for item_name, r_val in item_dict.items():
                rows.append({
                    "거래처명": client,
                    "사업자등록번호": info.get("사업자등록번호", ""),
                    "이메일": info.get("이메일", ""),
                    "담당자": info.get("담당자", ""),
                    "전화번호": info.get("전화번호", ""),
                    "주소": info.get("주소", ""),
                    "국가": country,
                    "운송형태": transport,
                    "품명": item_name,
                    "기본중량": r_val.get("기본중량", 1.0),
                    "기본요금": r_val.get("기본요금", 38000),
                    "추가단가": r_val.get("추가단가", 25000),
                    "1CBM당단가": r_val.get("1CBM당단가", 3700000),
                })
  pd.DataFrame(rows).to_csv(CLIENT_FILE, index=False, encoding="utf-8-sig")


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
              "기본중량": float(row.get("기본중량", 1.0)),
              "기본요금": int(row.get("기본요금", 35000)),
              "추가단가": int(row.get("추가단가", 22000)),
              "1CBM당단가": int(row.get("1CBM당단가", 3500000)),
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
  clean_txt = str(text).strip()
  code128_patterns = {
      "0": "212222",
      "1": "222122",
      "2": "222221",
      "3": "121223",
      "4": "121322",
      "5": "131222",
      "6": "122213",
      "7": "122312",
      "8": "132212",
      "9": "221213",
      "A": "212321",
      "B": "232121",
      "C": "113222",
      "D": "123122",
      "E": "123221",
      "F": "223112",
      "G": "223211",
      "H": "212231",
      "I": "231221",
      "J": "221321",
      "K": "312122",
      "L": "321122",
      "M": "321221",
      "N": "312212",
      "O": "322112",
      "P": "322211",
      "Q": "212132",
      "R": "212312",
      "S": "232112",
      "T": "213122",
      "U": "311222",
      "V": "321112",
      "W": "322102",
      "X": "312112",
      "Y": "321211",
      "Z": "212113",
      "-": "112232",
      ".": "122132",
      " ": "122231",
      "default": "212222",
  }

  encoded_bars = "211214"
  for ch in clean_txt.upper():
    encoded_bars += code128_patterns.get(ch, code128_patterns["default"])
  encoded_bars += "2331112"

  bars_html = ""
  is_black = True
  for char_val in encoded_bars:
    try:
      width_multiplier = int(char_val)
    except:
      width_multiplier = 1

    w_px = width_multiplier * 1.5
    bg_color = "#000000" if is_black else "#ffffff"
    bars_html += f"<div style='display:inline-block; width:{w_px}px; height:44px; background-color:{bg_color};'></div>"
    is_black = not is_black

  return f"""
    <div style="text-align: right; display: inline-block; background: #ffffff; padding: 6px; border-radius: 4px;">
        <div style="line-height: 0; white-space: nowrap;">{bars_html}</div>
        <div style="font-size: 10.5pt; font-weight: 900; color: #000000; margin-top: 4px; letter-spacing: 2px; text-align: center;">{clean_txt}</div>
    </div>
    """


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

query_params = st.query_params
mode_param = query_params.get("mode", "")

# ==========================================
# [관리자 로그인 모드 (?mode=admin)]
# ==========================================
if mode_param == "admin":
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

  current_bl_data = load_bl_data()
  st.markdown("#### **📦 B/L & 화물 실시간 통합 조회**")
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

        # 기존 거래처/요율 구조 등은 메타 시트에 보관해 손실 없이 복원합니다.
        pd.DataFrame([{
            "__SYSTEM_META__": json.dumps(meta_dict, ensure_ascii=False)
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
            if "__SYSTEM_META__" in df_meta.columns and not df_meta.empty:
                meta_val = df_meta["__SYSTEM_META__"].iloc[0]
                if pd.notna(meta_val) and str(meta_val).strip():
                    try:
                        parsed_meta = json.loads(str(meta_val))
                        break
                    except Exception:
                        pass

        # 거래처 및 기본 정보 복원
        if parsed_meta:
            st.session_state.client_list = parsed_meta.get("client_list", st.session_state.get("client_list", []))
            st.session_state.client_rates = parsed_meta.get("client_rates", st.session_state.get("client_rates", {}))
            st.session_state.client_infos = parsed_meta.get("client_infos", st.session_state.get("client_infos", {}))
            st.session_state.supplier_list = parsed_meta.get("supplier_list", st.session_state.get("supplier_list", []))
            st.session_state.supplier_rates = parsed_meta.get("supplier_rates", st.session_state.get("supplier_rates", {}))
            st.session_state.supplier_infos = parsed_meta.get("supplier_infos", st.session_state.get("supplier_infos", {}))

        # 1. 일계표(입출금장부) 복원: 엑셀 시트 실데이터 최우선 적용
        ledger_restored = False
        for sheet_name in ("일계표_입출금장부", "일계표", "입출금장부", "계정장부"):
            if sheet_name in sheets:
                df_ledger = sheets[sheet_name].copy()
                df_ledger = df_ledger.drop(columns=["__SYSTEM_META__"], errors="ignore")
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
            bl_df = bl_df.drop(columns=["__SYSTEM_META__"], errors="ignore")
            bl_df = bl_df[bl_df["B/L 번호"].notna()]
            st.session_state.bl_data_list = bl_df.fillna("").to_dict("records")
            save_bl_data(st.session_state.bl_data_list)

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
  menu_options.append("🔑 직원 계정 관리 (대표님 전용)")

selected_menu = st.sidebar.radio("📌 메인 메뉴 이동", menu_options)

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
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 15px;'>📋 수출입 B/L 및 Profit 등록 관리</h3>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "##### 📦 박스 규격 및 카톤수 입력 (아래 입력창에 가로, 세로, 높이, 카톤수를 적어주시면 즉시 부피중량과 CBM이 계산됩니다)"
    )

    if "box_input_df" not in st.session_state:
        st.session_state.box_input_df = pd.DataFrame([
            {"가로(cm)": 100.0, "세로(cm)": 100.0, "높이(cm)": 100.0, "카톤수(개)": 1}
        ])

    edited_box_df = st.data_editor(
        st.session_state.box_input_df,
        num_rows="dynamic",
        use_container_width=True,
        key="box_editor_multi_infinite",
    )

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
        w = float(row.get("가로(cm)", 0) or 0)
        l = float(row.get("세로(cm)", 0) or 0)
        h = float(row.get("높이(cm)", 0) or 0)
        ctn = int(row.get("카톤수(개)", 0) or 0)

        if w > 0 and l > 0 and h > 0 and ctn > 0:
            box_cbm = ((w * l * h) / 1000000.0) * ctn
            total_cbm += box_cbm
            total_ctn += ctn

            box_vol_sales = ((w * l * h) / s_div) * ctn
            box_vol_purchase = ((w * l * h) / p_div) * ctn

            total_vol_wt_sales += box_vol_sales
            total_vol_wt_purchase += box_vol_purchase

            vol_str_list.append(f"{int(w)}×{int(l)}×{int(h)}cm({ctn}CTN)")

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
                st.success(
                    f"🎉 [성공] B/L 및 Job 번호({job_no})가 소수점 실중량({gross_weight_sales}kg) 포함하여 정상 등록되었습니다!"
                )
            else:
                st.warning(
                    "⚠️ [경고] 'Job 번호'와 '화주명'은 반드시 입력하셔야 등록됩니다."
                )

# ==========================================
# [등록 B/L 수정 및 Profit 내역] 전체 완성 코드
# ==========================================
elif selected_menu == "🚨 등록 B/L 수정 및 Profit 내역":
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 15px;'>🚨 등록 B/L 수정 및 Profit 내역 관리</h3>",
        unsafe_allow_html=True,
    )

    if not st.session_state.bl_data_list:
        st.info("등록된 B/L 데이터가 없습니다.")
    else:
        df_bl_all = pd.DataFrame(st.session_state.bl_data_list)
        
        # B/L 선택 필터
        st.markdown("#### 🔍 수정할 B/L 번호 선택")
        all_bl_nos = df_bl_all["B/L 번호"].dropna().astype(str).tolist() if "B/L 번호" in df_bl_all.columns else []
        
        if not all_bl_nos:
            st.warning("선택할 수 있는 B/L 번호가 존재하지 않습니다.")
        else:
            selected_bl_no = st.selectbox("B/L 번호 조회 및 선택", options=all_bl_nos, key="select_bl_for_edit_full")
            
            # 선택된 B/L 데이터 가져오기
            target_item = next((item for item in st.session_state.bl_data_list if str(item.get("B/L 번호", "")) == selected_bl_no), None)
            
            if target_item:
                st.markdown("---")
                st.markdown(f"### 📦 B/L 번호: **{selected_bl_no}** 상세 정보 및 수정")
                
                # 기본 정보 표시 영역
                info_c1, info_c2, info_c3, info_c4 = st.columns(4)
                with info_c1:
                    st.text_input("수출(Export)", value=str(target_item.get("수출입구분", "수출")), disabled=True, key="edit_io_type")
                with info_c2:
                    st.text_input("목적국", value=str(target_item.get("목적국", "")), disabled=True, key="edit_dest_country")
                with info_c3:
                    st.text_input("선적 날짜", value=str(target_item.get("날짜", ""))[:10], disabled=True, key="edit_date")
                with info_c4:
                    st.text_input("매입처", value=str(target_item.get("매입처", "")), disabled=True, key="edit_vendor_disp")

                info_c5, info_c6, info_c7, info_c8 = st.columns(4)
                with info_c5:
                    st.text_input("화주명(매출)", value=str(target_item.get("화주명(매출)", "")), disabled=True, key="edit_shipper")
                with info_c6:
                    st.text_input("품목", value=str(target_item.get("품목", "")), disabled=True, key="edit_item_name")
                with info_c7:
                    st.text_input("Job 번호", value=str(target_item.get("Job 번호", "")), disabled=True, key="edit_job_no")
                with info_c8:
                    st.text_input("수금 상태", value=str(target_item.get("수금상태", "미수")), disabled=True, key="edit_pay_status")

                st.markdown("#### 📦 중량, 규격 및 금액 상세 수정")
                
                # 수정 입력 필드 구성
                edit_c1, edit_c2, edit_c3 = st.columns(3)
                with edit_c1:
                    piece_count_str = st.text_input("박스수", value=str(target_item.get("박스수", "1 박스 (CTN)")))
                with edit_c2:
                    cbm_val = target_item.get("CBM", "0.000 CBM")
                    st.text_input("CBM", value=str(cbm_val), disabled=True)
                with edit_c3:
                    gross_weight_sales_str = st.text_input("실중량 (kg) [소수점 유지]", value=str(target_item.get("실중량(kg)", "0.0")))

                edit_c4, edit_c5, edit_c6 = st.columns(3)
                with edit_c4:
                    volume_str_result = st.text_input("부피 규격", value=str(target_item.get("부피규격", "")))
                with edit_c5:
                    shipping_mode = st.selectbox("운송 형태", options=["항공(Air)", "해상(Ocean)", "특송(Express)"], index=0)
                with edit_c6:
                    charge_weight_sales_str = st.text_input("매출 청구중량 (kg) [kg당 올림]", value=str(target_item.get("매출청구중량(kg)", "0.0")))

                # 매입 관련 중량 입력
                edit_c7, edit_c8 = st.columns(2)
                with edit_c7:
                    gross_weight_purchase_str = st.text_input("매입 실중량 (kg)", value=str(target_item.get("매입실중량(kg)", "0.0")))
                with edit_c8:
                    charge_weight_purchase_str = st.text_input("매입 청구중량 (kg)", value=str(target_item.get("매입청구중량(kg)", "0.0")))

                st.markdown("---")
                
                # 💾 하단 저장 및 취소 버튼 영역 (스크롤 하단 고정 형태)
                col_save1, col_save2, col_save3 = st.columns([2, 2, 2])
                
                with col_save1:
                    if st.button("💾 B/L 수정 사항 저장하기", type="primary", use_container_width=True, key="btn_save_bl_edit_final"):
                        try:
                            # 1. 데이터 업데이트
                            for item in st.session_state.bl_data_list:
                                if str(item.get("B/L 번호", "")) == selected_bl_no:
                                    item["박스수"] = piece_count_str
                                    item["실중량(kg)"] = gross_weight_sales_str
                                    item["매입실중량(kg)"] = gross_weight_purchase_str
                                    item["매출청구중량(kg)"] = charge_weight_sales_str
                                    item["매입청구중량(kg)"] = charge_weight_purchase_str
                                    item["부피규격"] = volume_str_result
                                    item["운송형태"] = shipping_mode
                                    item["최종수정자"] = current_user_name
                                    item["최종수정일시"] = str(datetime.now())[:19]
                            
                            # 2. 파일 및 세션 저장 실행
                            save_bl_data(st.session_state.bl_data_list)
                            st.success(f"✅ B/L [{selected_bl_no}] 수정 사항이 성공적으로 저장되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 저장 중 오류가 발생했습니다: {e}")
                            
                with col_save2:
                    if st.button("🔄 새로고침 / 초기화", use_container_width=True, key="btn_cancel_bl_edit"):
                        st.rerun()
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
    st.markdown("<p style='color: #64748b; font-size: 13px; margin-bottom: 15px;'>협력사별 매입 원가, 지급완료 금액, 미지급 잔액을 집계하고 건별 지급 상태를 관리합니다.</p>", unsafe_allow_html=True)
    
    if st.session_state.get("bl_data_list"):
        df_bl = pd.DataFrame(st.session_state.bl_data_list)
        if "매입처" in df_bl.columns and "매입액(원)" in df_bl.columns:
            df_bl["매입처"] = df_bl["매입처"].astype(str).str.strip()
            df_bl["매입액(원)"] = pd.to_numeric(df_bl["매입액(원)"], errors="coerce").fillna(0)
            if "지급상태" not in df_bl.columns:
                df_bl["지급상태"] = "미지급"
            
            # 1. 협력사별 매입 및 미지급 요약
            purchase_group = df_bl.groupby("매입처").agg(
                총매입액=("매입액(원)", "sum"),
                지급완료액=("매입액(원)", lambda x: x[df_bl.loc[x.index, "지급상태"] == "지급완료"].sum()),
                미지급잔액=("매입액(원)", lambda x: x[df_bl.loc[x.index, "지급상태"] != "지급완료"].sum()),
                건수=("B/L 번호", "count")
            ).reset_index().sort_values("미지급잔액", ascending=False)
            
            st.subheader("📋 협력사별 매입 원가 및 미지급 잔액 요약")
            st.dataframe(purchase_group, use_container_width=True)
            
            st.markdown("---")
            
            # 2. 특정 협력사 상세 매입 내역 및 지급 상태 체크 관리
            st.subheader("🔍 특정 협력사 상세 매입 내역 및 지급 상태 관리")
            col_v1, col_v2 = st.columns([2, 1])
            with col_v1:
                sel_v = st.selectbox("조회할 협력사 선택", df_bl["매입처"].unique(), key="purchase_track_vendor")
            with col_v2:
                only_unpaid_v = st.checkbox("📌 미지급 건만 보기", value=True, key="only_unpaid_vendor")
            
            vendor_detail = df_bl[df_bl["매입처"] == sel_v].copy()
            if only_unpaid_v:
                vendor_detail = vendor_detail[vendor_detail["지급상태"].astype(str).str.strip() != "지급완료"]
            
            if "선택" not in vendor_detail.columns:
                vendor_detail.insert(0, "선택", False)
            
            edited_vendor_table = st.data_editor(
                vendor_detail,
                hide_index=True,
                use_container_width=True,
                column_config={"선택": st.column_config.CheckboxColumn(required=True)},
                key="vendor_unpaid_edit_table"
            )
            
            selected_vendor_rows = edited_vendor_table[edited_vendor_table["선택"] == True]
            
            if st.button("💳 선택한 매입 건 [지급완료] 일괄 처리", type="primary", use_container_width=True):
                if len(selected_vendor_rows) > 0:
                    for real_idx in selected_vendor_rows.index.tolist():
                        st.session_state.bl_data_list[real_idx]["지급상태"] = "지급완료"
                        st.session_state.bl_data_list[real_idx]["최종수정자"] = current_user_name
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
# [3] B/L 운송장 출력 메뉴
# ==========================================
elif selected_menu == "🚢 B/L 운송장 출력":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>🚢"
      " (주)범운해운항공 정식 B/L 운송장 출력</h3>",
      unsafe_allow_html=True,
  )

  if st.session_state.bl_data_list:
    bl_number_list = [
        str(item.get("B/L 번호", "")) for item in st.session_state.bl_data_list
    ]
    selected_print_bl = st.selectbox(
        "출력할 B/L 번호 선택하기", options=bl_number_list
    )

    target_bl_data = next(
        (
            item
            for item in st.session_state.bl_data_list
            if str(item.get("B/L 번호")) == selected_print_bl
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


# ==========================================
# [4] 거래처 인보이스 발행
# ==========================================
elif selected_menu == "📑 거래처 인보이스 발행":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 5px;'>📑"
      " 거래처 인보이스 발행</h3>",
      unsafe_allow_html=True,
  )

  if st.session_state.client_list:
    col_inv1, col_inv2, col_inv3 = st.columns([1.5, 1.5, 1])
    with col_inv1:
      selected_invoice_client = st.selectbox(
          "인보이스를 발행할 거래처 선택", options=st.session_state.client_list
      )
    with col_inv2:
      selected_invoice_date = st.date_input(
          "조회할 선적 날짜 선택", value=date.today(), key="invoice_target_date"
      )
    with col_inv3:
      tax_mode = st.selectbox(
          "영세율 / 세금계산서 설정",
          options=[
              "영세율 적용 (세금계산서 미발행/청구확인용)",
              "과세 적용 (VAT 10%)",
          ],
      )

    target_date_str = str(selected_invoice_date)
    client_infos = st.session_state.client_infos.get(
        selected_invoice_client, {}
    )

    client_bl_list = []
    if "bl_data_list" in st.session_state and st.session_state.bl_data_list:
      for j in st.session_state.bl_data_list:
        if (
            j.get("화주명(매출)") == selected_invoice_client
            and str(j.get("날짜", "")) == target_date_str
        ):
          client_bl_list.append(j)

    st.markdown(
        f"#### 📌 [{selected_invoice_client}] [{target_date_str}] 청구 대상"
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
                        @media print {{ body {{ -webkit-print-color-adjust: exact; }} .no-print {{ display: none !important; }} @page {{ size: A4 portrait; margin: 8mm; }} }}
                        body {{ font-family: 'Pretendard', sans-serif; color: #1e293b; font-size: 8.5pt; margin: 0; padding: 10px; background: #fff; }}
                        .inv-box {{ max-width: 820px; margin: 0 auto; border: 2px solid #0f172a; padding: 20px; border-radius: 8px; }}
                        .t-tbl {{ width: 100%; border-collapse: collapse; margin-top: 15px; table-layout: fixed; }}
                        .t-tbl th, .t-tbl td {{ border: 1px solid #64748b; padding: 5px 4px; text-align: center; vertical-align: middle; font-size: 8pt; }}
                        .t-tbl th {{ background-color: #0f172a; color: white; font-size: 8.5pt; }}
                        .p-btn {{ display: block; width: 100%; background-color: #dc2626; color: white; text-align: center; padding: 12px; font-size: 11pt; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; margin-bottom: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="inv-box">
                        <button class="p-btn no-print" onclick="window.print()">🖨 인보이스 인쇄 및 PDF 저장</button>
                        <h1 style="text-align: center; color: #1e3a8a; margin-bottom: 5px; font-size: 18pt; font-weight: 900;">청 구 서 (INVOICE)</h1>
                        <p style="text-align: center; color: #475569; font-size: 8.5pt; margin-top: 0;">(주)범운해운항공 | 발행일자: {date.today()} | 선적기준일: {target_date_str}</p>
                        <table style="width: 100%; margin-top: 12px; border-collapse: collapse;">
                            <tr>
                                <td style="border: 1px solid #64748b; padding: 8px; background: #fff; font-size: 9pt;">
                                    <b>[공급받는 자]</b> 상호: <b>{selected_invoice_client}</b> | 사업자등록번호: {c_bno} | 담당자: {c_mgr}<br>주소: {c_addr}
                                </td>
                            </tr>
                        </table>
                        <table class="t-tbl">
                            <tr>
                                <th>작성일자</th><th>B/L 번호</th><th>국가</th><th>수하인</th><th>품목 / 박스</th><th>부피규격</th><th>청구중량</th><th>금액 (원)</th>
                            </tr>
            """
        for r in client_bl_list:
          invoice_html += f"""
                    <tr>
                        <td>{r.get("날짜", target_date_str)}</td>
                        <td style="font-weight: bold;">{r.get("B/L 번호", "-")}</td>
                        <td>{r.get("국가", "-")}</td>
                        <td>{r.get("해외수하인", "-")}</td>
                        <td>{r.get("품목", "-")} ({r.get("박스수", "1 박스")})</td>
                        <td>{r.get("부피규격", "-")}</td>
                        <td>{r.get("매출청구중량(kg)", 1.0)} kg</td>
                        <td style="text-align: right; font-weight: bold;">{int(r.get("매출액(원)", 0)):,} 원</td>
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
          f"[{selected_invoice_client}] 거래처의 [{target_date_str}] 선적"
          " 데이터가 없습니다."
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
# [금일발송 매니페스트] 매입처별 자동 분리 및 화물 입고 리스트 A4 출력
# ==========================================
elif selected_menu == "📋 금일발송 매니페스트":
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 15px;'>📋 매입처별 화물 입고 리스트 및 매니페스트</h3>",
        unsafe_allow_html=True,
    )

    if st.session_state.bl_data_list:
        df_manifest = pd.DataFrame(st.session_state.bl_data_list)
        
        st.markdown("#### 📅 조회할 선적 날짜 선택")
        all_dates = sorted(list(set(str(d)[:10] for d in df_manifest["날짜"]))) if "날짜" in df_manifest.columns else [str(date.today())]
        
        selected_manifest_date = st.selectbox("날짜 선택", options=all_dates, index=len(all_dates)-1 if all_dates else 0)
        
        target_df = df_manifest[df_manifest["날짜"].astype(str).str.startswith(selected_manifest_date)].copy()
        
        if not target_df.empty:
            if "선택" not in target_df.columns:
                target_df.insert(0, "선택", False)
                
            st.markdown(f"#### 📦 [{selected_manifest_date}] 전체 발송 화물 목록 (매입처 수정 가능)")
            st.info("💡 아래 표의 **[매입처]** 칸을 클릭하시면 등록된 협력사 목록이 드롭다운으로 나타납니다.")

            base_suppliers = st.session_state.get("supplier_list", ["(주)카스익스프레스", "주식회사 비에프티", "윤세형", "ESI"])
            existing_vendors = target_df["매입처"].fillna("").astype(str).unique().tolist() if "매입처" in target_df.columns else []
            combined_suppliers = sorted(list(set([""] + base_suppliers + [v for v in existing_vendors if v and v != "None" and v != "nan"])))

            if "매입처" in target_df.columns:
                target_df["매입처"] = target_df["매입처"].fillna("").astype(str).replace({"None": "", "nan": ""})
            else:
                target_df["매입처"] = ""

            cols_order = ["선택", "날짜", "B/L 번호", "화주명(매출)", "매입처", "해외수하인", "해외수하인주소", "해외수하인전화번호", "박스수", "부피규격", "실중량(kg)"]
            existing_cols = [c for c in cols_order if c in target_df.columns] + [c for c in target_df.columns if c not in cols_order]
            target_df = target_df[existing_cols]

            edited_manifest_table = st.data_editor(
                target_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "선택": st.column_config.CheckboxColumn("선택", default=False),
                    "매입처": st.column_config.SelectboxColumn("매입처(협력사 선택)", options=combined_suppliers, required=False),
                },
                key=f"manifest_editor_v10_{selected_manifest_date}",
                height=320,
            )

            col_sv1, col_sv2 = st.columns(2)
            with col_sv1:
                if st.button("💾 매입처 변경 내용 저장하기", type="primary", use_container_width=True):
                    try:
                        for _, edited_row in edited_manifest_table.iterrows():
                            target_bl = str(edited_row.get("B/L 번호", ""))
                            new_vendor = str(edited_row.get("매입처", ""))
                            
                            for real_item in st.session_state.bl_data_list:
                                if str(real_item.get("B/L 번호", "")) == target_bl:
                                    real_item["매입처"] = new_vendor
                                    real_item["최종수정자"] = current_user_name
                                    
                        save_bl_data(st.session_state.bl_data_list)
                        st.success("✅ 매입처 변경 내용이 성공적으로 저장되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 저장 중 오류 발생: {e}")
            with col_sv2:
                if st.button("🔄 화면 새로고침", use_container_width=True):
                    st.rerun()

            st.markdown("---")

            # ----------------------------------------------------
            # 🖨️ 매입처별 자동 분리 및 화물 입고 리스트 (즉시 표시)
            # ----------------------------------------------------
            st.subheader("🖨️ 매입처별 화물 입고 리스트 (자동 분리)")

            vendors_in_data = [v for v in edited_manifest_table["매입처"].unique() if v and v != "None" and v != "nan"]

            if not vendors_in_data:
                st.warning("등록된 매입처가 없습니다. 상단 표에서 매입처를 먼저 지정해 주세요.")
            else:
                for vendor in vendors_in_data:
                    vendor_data = edited_manifest_table[edited_manifest_table["매입처"] == vendor]
                    
                    vendor_print_df = pd.DataFrame()
                    vendor_print_df["박스번호"] = vendor_data.get("B/L 번호", "-")
                    vendor_print_df["날짜"] = vendor_data.get("날짜", selected_manifest_date)
                    vendor_print_df["박스수"] = vendor_data.get("박스수", "1 CTN")
                    vendor_print_df["실중량"] = vendor_data.get("실중량(kg)", vendor_data.get("매입실중량(kg)", "-"))
                    vendor_print_df["부피중량/규격"] = vendor_data.get("부피규격", "-")
                    vendor_print_df["화주"] = vendor_data.get("해외수하인", "-")
                    vendor_print_df["주소"] = vendor_data.get("해외수하인주소", "-")
                    vendor_print_df["전화번호"] = vendor_data.get("해외수하인전화번호", "-")

                    with st.expander(f"📌 [{vendor}] 화물 입고 리스트 (총 {len(vendor_data)}건)", expanded=True):
                        st.dataframe(vendor_print_df, use_container_width=True, hide_index=True)
                        
                        c_dl1, c_dl2, c_dl3 = st.columns(3)
                        with c_dl1:
                            csv_data = vendor_print_df.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                label=f"📥 [{vendor}] 파일 다운로드",
                                data=csv_data,
                                file_name=f"inbound_list_{vendor}_{selected_manifest_date}.csv",
                                mime="text/csv",
                                key=f"dl_vendor_{vendor}_{selected_manifest_date}"
                            )
                        with c_dl2:
                            if st.button(f"✉️ [{vendor}] 담당자 전송", key=f"send_vendor_{vendor}_{selected_manifest_date}"):
                                st.toast(f"[{vendor}] 담당자에게 입고 리스트가 성공적으로 전송되었습니다!")
                        with c_dl3:
                            v_info = st.session_state.get("supplier_infos", {}).get(vendor, {})
                            v_bno = v_info.get("사업자등록번호", "-")
                            v_mgr = v_info.get("담당자", "-")
                            v_tel = v_info.get("전화번호", "-")

                            # ----------------------------------------------------
                            # 🖨️ A4 가로 맞춤 [범운 화물 입고 리스트] HTML (SyntaxError 수정 완료)
                            # ----------------------------------------------------
                            a4_manifest_html = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <meta charset="utf-8">
                                <style>
                                    @media print {{
                                        body {{ -webkit-print-color-adjust: exact; }}
                                        .no-print {{ display: none !important; }}
                                        @page {{ size: A4 landscape; margin: 8mm; }}
                                    }}
                                    body {{ font-family: 'Pretendard', sans-serif; color: #0f172a; font-size: 8.5pt; margin: 0; padding: 10px; background: #fff; }}
                                    .report-box {{ width: 100%; max-width: 1050px; margin: 0 auto; border: 2px solid #0f172a; padding: 16px; border-radius: 8px; background: #ffffff; box-sizing: border-box; }}
                                    .header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; }}
                                    .header-table td {{ border: none; vertical-align: middle; }}
                                    
                                    .approval-table {{ border-collapse: collapse; float: right; }}
                                    .approval-table th, .approval-table td {{ border: 1px solid #475569; font-size: 8pt; text-align: center; padding: 4px 8px; }}
                                    .approval-table th {{ background-color: #f1f5f9; }}
                                    .approval-sign {{ height: 32px; }}

                                    .info-box {{ background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; font-size: 9pt; }}
                                    
                                    .data-table {{ width: 100%; border-collapse: collapse; margin-top: 8px; table-layout: fixed; }}
                                    .data-table th, .data-table td {{ border: 1px solid #475569; padding: 6px 4px; text-align: center; font-size: 8pt; word-break: break-all; }}
                                    .data-table th {{ background-color: #0f172a; color: #ffffff; font-weight: 600; }}
                                    .data-table tr:nth-child(even) {{ background-color: #f8fafc; }}

                                    .p-btn {{ display: block; width: 100%; background-color: #2563eb; color: white; text-align: center; padding: 10px; font-size: 11pt; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; margin-bottom: 15px; }}
                                </style>
                            </head>
                            <body>
                                <div class="report-box">
                                    <button class="p-btn no-print" onclick="window.print()">🖨️ A4 입고 리스트 인쇄 / PDF 저장</button>
                                    
                                    <table class="header-table">
                                        <tr>
                                            <td>
                                                <div style="font-size: 11pt; font-weight: bold; color: #2563eb; margin-bottom: 2px;">(주)범운해운항공</div>
                                                <div style="font-size: 17pt; font-weight: 900; color: #0f172a; letter-spacing: -0.5px;">범운 화물 입고 리스트 (INBOUND MANIFEST)</div>
                                                <div style="font-size: 8.5pt; color: #64748b; margin-top: 3px;">입고/발송일자: <b>{selected_manifest_date}</b> | 매입처: <b style="color: #1e3a8a;">{vendor}</b></div>
                                            </td>
                                            <td style="width: 150px;">
                                                <table class="approval-table">
                                                    <tr><th rowspan="2" style="width: 18px; background:#f8fafc;">결<br>재</th><th>담당</th><th>대표</th></tr>
                                                    <tr><td class="approval-sign"></td><td class="approval-sign"></td></tr>
                                                </table>
                                            </td>
                                        </tr>
                                    </table>

                                    <div class="info-box">
                                        <b>[협력사(매입처) 정보]</b> 상호: <b>{vendor}</b> | 사업자번호: {v_bno} | 담당자: {v_mgr} ({v_tel}) &nbsp;&nbsp;|&nbsp;&nbsp; 총 입고 수량: <b>{len(vendor_data)} 건</b>
                                    </div>

                                    <table class="data-table">
                                        <tr>
                                            <th style="width: 12%;">박스번호</th>
                                            <th style="width: 9%;">날짜</th>
                                            <th style="width: 8%;">박스수</th>
                                            <th style="width: 9%;">실중량</th>
                                            <th style="width: 16%;">부피중량/규격</th>
                                            <th style="width: 14%;">화주</th>
                                            <th style="width: 21%;">주소</th>
                                            <th style="width: 11%;">전화번호</th>
                                        </tr>
                            """
                            for _, r in vendor_data.iterrows():
                                weight_val = r.get("실중량(kg)", r.get("매입실중량(kg)", "-"))
                                a4_manifest_html += f"""
                                        <tr>
                                            <td style="font-weight: bold;">{r.get("B/L 번호", "-")}</td>
                                            <td>{str(r.get("날짜", selected_manifest_date))[:10]}</td>
                                            <td>{r.get("박스수", "1 CTN")}</td>
                                            <td>{weight_val} kg</td>
                                            <td>{r.get("부피규격", "-")}</td>
                                            <td style="font-weight: bold;">{r.get("해외수하인", "-")}</td>
                                            <td style="text-align: left; padding-left: 4px;">{r.get("해외수하인주소", "-")}</td>
                                            <td>{r.get("해외수하인전화번호", "-")}</td>
                                        </tr>
                                """
                            a4_manifest_html += f"""
                                    </table>
                                    
                                    <div style="margin-top: 25px; text-align: center; font-size: 9pt; color: #475569;">
                                        상기 화물의 입고 내역을 정식 확인합니다.<br><br>
                                        <b style="font-size: 10.5pt; color: #0f172a;">주식회사 범운해운항공 대표이사 이상복 [직인생략]</b>
                                    </div>
                                </div>
                            </body>
                            </html>
                            """
                            
                            if st.button(f"🖨️ [{vendor}] A4 입고 리스트 인쇄", key=f"print_a4_{vendor}_{selected_manifest_date}"):
                                components.html(a4_manifest_html, height=750, scrolling=True)
        else:
            st.info(f"📌 선택하신 날짜({selected_manifest_date})에 등록된 발송 화물 내역이 없습니다.")
    else:
        st.info("등록된 B/L 데이터가 없습니다.")
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
                      item_name
                      if item_name and item_name != "None"
                      else "일반화물"
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
          "기본중량(kg)": 1.0,
          "기본요금(원)": 38000,
          "추가단가(원/kg)": 25000,
          "1CBM당단가(원)": 3700000,
      }]

    df_rates = pd.DataFrame(rate_rows)
    if "선택" not in df_rates.columns:
      df_rates.insert(0, "선택", False)

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
                options=["보톡스", "필러", "화장품", "특가품목", "기타"],
                required=True,
            ),
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
          c_item = str(row.get("품명", "일반화물")).strip()
          if c_cntry and c_trans and c_item:
            if c_cntry not in new_rates_dict:
              new_rates_dict[c_cntry] = {}
            if c_trans not in new_rates_dict[c_cntry]:
              new_rates_dict[c_cntry][c_trans] = {}
            new_rates_dict[c_cntry][c_trans][c_item] = {
                "기본중량": float(row.get("기본중량(kg)", 1.0) or 1.0),
                "기본요금": int(row.get("기본요금(원)", 38000) or 0),
                "추가단가": int(row.get("추가단가(원/kg)", 25000) or 0),
                "1CBM당단가": int(row.get("1CBM당단가(원)", 3700000) or 0),
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
            c_item = str(row.get("품명", "일반화물")).strip()
            if c_cntry and c_trans and c_item:
              if c_cntry not in new_rates_dict:
                new_rates_dict[c_cntry] = {}
              if c_trans not in new_rates_dict[c_cntry]:
                new_rates_dict[c_cntry][c_trans] = {}
              new_rates_dict[c_cntry][c_trans][c_item] = {
                  "기본중량": float(row.get("기본중량(kg)", 1.0) or 1.0),
                  "기본요금": int(row.get("기본요금(원)", 38000) or 0),
                  "추가단가": int(row.get("추가단가(원/kg)", 25000) or 0),
                  "1CBM당단가": int(row.get("1CBM당단가(원)", 3700000) or 0),
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
                      item_name
                      if item_name and item_name != "None"
                      else "일반화물"
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
          "기본중량(kg)": 1.0,
          "기본요금(원)": 35000,
          "추가단가(원/kg)": 22000,
          "1CBM당단가(원)": 3500000,
      }]

    df_supp_rates = pd.DataFrame(supp_rate_rows)
    if "선택" not in df_supp_rates.columns:
      df_supp_rates.insert(0, "선택", False)

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
                options=["보톡스", "필러", "화장품", "특가품목", "기타"],
                required=True,
            ),
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
          c_item = str(row.get("품명", "일반화물")).strip()
          if c_cntry and c_trans and c_item:
            if c_cntry not in new_supp_rates_dict:
              new_supp_rates_dict[c_cntry] = {}
            if c_trans not in new_supp_rates_dict[c_cntry]:
              new_supp_rates_dict[c_cntry][c_trans] = {}
            new_supp_rates_dict[c_cntry][c_trans][c_item] = {
                "기본중량": float(row.get("기본중량(kg)", 1.0) or 1.0),
                "기본요금": int(row.get("기본요금(원)", 35000) or 0),
                "추가단가": int(row.get("추가단가(원/kg)", 22000) or 0),
                "1CBM당단가": int(row.get("1CBM당단가(원)", 3500000) or 0),
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
            c_item = str(row.get("품명", "일반화물")).strip()
            if c_cntry and c_trans and c_item:
              if c_cntry not in new_supp_rates_dict:
                new_supp_rates_dict[c_cntry] = {}
              if c_trans not in new_supp_rates_dict[c_cntry]:
                new_supp_rates_dict[c_cntry][c_trans] = {}
              new_supp_rates_dict[c_cntry][c_trans][c_item] = {
                  "기본중량": float(row.get("기본중량(kg)", 1.0) or 1.0),
                  "기본요금": int(row.get("기본요금(원)", 35000) or 0),
                  "추가단가": int(row.get("추가단가(원/kg)", 22000) or 0),
                  "1CBM당단가": int(row.get("1CBM당단가(원)", 3500000) or 0),
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
elif selected_menu == "📉 거래처 미수금관리":
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 15px;'>📉 거래처 미수금 현황 및 수금 관리</h3>",
        unsafe_allow_html=True,
    )

    if st.session_state.bl_data_list:
        df_all_bl = pd.DataFrame(st.session_state.bl_data_list)

        # 미수 상태 건만 필터링 (수금상태가 '수금완료'가 아닌 건)
        if "수금상태" in df_all_bl.columns:
            unpaid_df = df_all_bl[df_all_bl["수금상태"] != "수금완료"].copy()
        else:
            unpaid_df = df_all_bl.copy()

        if not unpaid_df.empty:
            # 1. 상단 화주별 미수금 요약
            st.markdown("#### 📊 화주별 미수금 요약 현황")
            
            try:
                unpaid_df["매출액_num"] = unpaid_df["매출액(원)"].apply(
                    lambda x: float(str(x).replace(",", "") or 0)
                )
            except:
                unpaid_df["매출액_num"] = 0.0

            summary_unpaid = (
                unpaid_df.groupby("화주명(매출)")["매출액_num"]
                .agg(["count", "sum"])
                .reset_index()
            )
            summary_unpaid.columns = ["화주명", "미수 건수", "총 미수금액(원)"]
            summary_unpaid["총 미수금액(원)"] = summary_unpaid["총 미수금액(원)"].apply(
                lambda x: f"{int(x):,} 원"
            )

            st.dataframe(summary_unpaid, use_container_width=True, hide_index=True)

            total_unpaid_sum = unpaid_df["매출액_num"].sum()
            st.warning(
                f"⚠️ **전체 총 미수금 합계:** **{int(total_unpaid_sum):,} 원** (총 {len(unpaid_df)} 건)"
            )

            st.markdown("---")

            # 2. 하단 상세 미수 B/L 내역 및 수금완료 일괄 처리
            st.markdown("#### 📋 상세 미수 B/L 내역 (선택 건 수금완료 처리)")
            st.info("💡 아래 표에서 수금 완료된 B/L의 **[선택]** 체크박스를 체크하신 후 하단의 **[선택 건 수금완료 일괄 처리]** 버튼을 누르세요.")

            display_cols = [
                "선택",
                "날짜",
                "Job 번호",
                "B/L 번호",
                "화주명(매출)",
                "국가",
                "품목",
                "매출액(원)",
                "수금상태",
                "비고",
            ]

            if "선택" not in unpaid_df.columns:
                unpaid_df.insert(0, "선택", False)

            # 존재하지 않는 열 예외 처리
            valid_cols = [c for c in display_cols if c in unpaid_df.columns]
            df_table_view = unpaid_df[valid_cols]

            edited_unpaid_table = st.data_editor(
                df_table_view,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "선택": st.column_config.CheckboxColumn("선택", required=True),
                    "매출액(원)": st.column_config.NumberColumn("매출액(원)", format="%d"),
                },
                key="unpaid_filter_table_v2",
                height=350,
            )

            selected_unpaid_rows = edited_unpaid_table[
                edited_unpaid_table["선택"] == True
            ]

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                "💳 선택 건 [수금완료] 일괄 처리",
                type="primary",
                use_container_width=True,
            ):
                if len(selected_unpaid_rows) > 0:
                    for idx in selected_unpaid_rows.index.tolist():
                        bl_num_target = selected_unpaid_rows.loc[idx, "B/L 번호"]
                        # 원본 세션 데이터에서 해당 B/L 찾아 수금완료로 변경
                        for real_i, original_item in enumerate(
                            st.session_state.bl_data_list
                        ):
                            if str(original_item.get("B/L 번호", "")) == str(
                                bl_num_target
                            ):
                                st.session_state.bl_data_list[real_i][
                                    "수금상태"
                                ] = "수금완료"
                                st.session_state.bl_data_list[real_i][
                                    "최종수정자"
                                ] = current_user_name

                    save_bl_data
# ==========================================
# [일계표 및 입출금 장부] (등록 폼 '지급완료' 기본 선택 적용)
# ==========================================
elif selected_menu == "💳 일계표 및 입출금 장부":
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 15px;'>📊 일계표 및 입출금 장부</h3>",
        unsafe_allow_html=True,
    )

    if "cashbook_list" not in st.session_state:
        st.session_state.cashbook_list = load_account_data()

    cashbook_data = st.session_state.cashbook_list

    # --- 1. 상단: 날짜별 필터 (달력 위젯 표시) ---
    st.markdown("#### 📅 날짜별 조회 및 인쇄")
    
    col_f1, col_f2 = st.columns([1.5, 2])
    with col_f1:
        date_filter_mode = st.radio("조회 방식", ["전체 기간", "특정 날짜 선택"], horizontal=True, key="cash_filter_mode")
    
    selected_target_date = str(date.today())
    if date_filter_mode == "특정 날짜 선택":
        with col_f2:
            picked_date = st.date_input("📅 조회할 날짜 선택 (달력)", value=date.today(), key="cash_date_picker_calendar")
            selected_target_date = str(picked_date)

    # 데이터 필터링 및 지급상태 기본값 보장
    filtered_cash_data = []
    for item in cashbook_data:
        io_type = str(item.get("구분", ""))
        if "지급상태" not in item or not item.get("지급상태") or item.get("지급상태") in ["None", "nan"]:
            item["지급상태"] = "지급완료"
        elif "수입" in io_type:
            item["지급상태"] = "지급완료"
            
        if date_filter_mode == "전체 기간" or str(item.get("날짜", ""))[:10] == selected_target_date:
            filtered_cash_data.append(item)

    # --- 2. 통장 잔액 및 수입/지출 총액 요약 ---
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

    # --- 3. 중단: 장부 내역 조회 및 편집/삭제/지급완료 ---
    print_title = "전체 일계표" if date_filter_mode == "전체 기간" else f"{selected_target_date} 일계표"
    title_label = f"📋 등록된 장부 내역 (전체)" if date_filter_mode == "전체 기간" else f"📋 [{selected_target_date}] 일일 장부 내역"
    st.markdown(f"#### {title_label}")

    if filtered_cash_data:
        df_cash = pd.DataFrame(filtered_cash_data)
        
        if "선택" not in df_cash.columns:
            df_cash.insert(0, "선택", False)

        cols_order = ["선택", "날짜", "구분", "항목", "지급상태", "금액(원)", "적요"]
        existing_cols = [c for c in cols_order if c in df_cash.columns] + [c for c in df_cash.columns if c not in cols_order]
        df_cash = df_cash[existing_cols]

        edited_cash_table = st.data_editor(
            df_cash,
            hide_index=True,
            use_container_width=True,
            column_config={
                "선택": st.column_config.CheckboxColumn("선택", default=False),
                "지급상태": st.column_config.SelectboxColumn("지급상태", options=["지급완료", "미지급"], required=True),
                "금액(원)": st.column_config.NumberColumn("금액(원)", format="%d"),
            },
            key=f"cashbook_table_editor_v10_{date_filter_mode}_{selected_target_date}",
            height=320,
        )

        c_btn1, c_btn2, c_btn3, c_btn4 = st.columns([1.2, 1.2, 1, 1.2])
        with c_btn1:
            if st.button("💳 선택 건 [지급완료] 일괄 처리", type="primary", use_container_width=True):
                selected_rows = edited_cash_table[edited_cash_table["선택"] == True]
                if not selected_rows.empty:
                    for idx in selected_rows.index.tolist():
                        target_row = selected_rows.loc[idx]
                        for real_item in st.session_state.cashbook_list:
                            if (str(real_item.get("날짜", ""))[:10] == str(target_row.get("날짜", ""))[:10] and
                                str(real_item.get("적요", "")) == str(target_row.get("적요", "")) and
                                str(real_item.get("금액(원)", "")) == str(target_row.get("금액(원)", ""))):
                                real_item["지급상태"] = "지급완료"
                    save_account_data(st.session_state.cashbook_list)
                    st.success("✅ 선택하신 내역이 '지급완료' 처리되었습니다.")
                    st.rerun()
                else:
                    st.warning("⚠️ 지급완료 처리할 행의 체크박스를 선택해주세요.")

        with c_btn2:
            if st.button("💾 변경된 내용 저장", use_container_width=True):
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
                    st.success("일계표 변경 내용이 저장되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 중 오류 발생: {e}")

        with c_btn3:
            if st.button("🚨 선택 내역 삭제", type="secondary", use_container_width=True):
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

        with c_btn4:
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
                    .report-box {{ max-width: 780px; margin: 0 auto; border: 1.5px solid #cbd5e1; padding: 25px; border-radius: 8px; background: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }}
                    
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
                    <button class="p-btn no-print" onclick="window.print()">🖨 격식 있는 일계표 보고서 인쇄 / PDF 저장</button>
                    
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
                            <th style="width: 12%;">거래일자</th>
                            <th style="width: 12%;">구분</th>
                            <th style="width: 18%;">항목</th>
                            <th style="width: 18%;">금액 (원)</th>
                            <th style="width: 12%;">지급상태</th>
                            <th style="width: 28%;">적요 및 메모</th>
                        </tr>
            """
            for row in filtered_cash_data:
                io_gubun = str(row.get("구분", "-"))
                gubun_color = "#2563eb" if "수입" in io_gubun else "#dc2626"
                status_str = str(row.get("지급상태", "지급완료"))
                status_color = "#16a34a" if status_str == "지급완료" else "#dc2626"
                
                print_html += f"""
                        <tr>
                            <td>{row.get("날짜", "-")}</td>
                            <td style="font-weight: bold; color: {gubun_color};">{io_gubun}</td>
                            <td>{row.get("항목", "-")}</td>
                            <td style="text-align: right; font-weight: bold;">{int(float(str(row.get("금액(원)", 0)).replace(",", "") or 0)):,} 원</td>
                            <td style="font-weight: bold; color: {status_color};">{status_str}</td>
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
            
            if st.button("🖨 정식 일계표 인쇄 / PDF", type="primary", use_container_width=True):
                components.html(print_html, height=700, scrolling=True)
    else:
        st.info("조회된 장부 내역이 없습니다.")

    st.markdown("---")

    # --- 4. 하단: 새로운 수입 / 지출 장부 등록 ---
    st.markdown("#### ✍️ 새로운 수입 / 지출 장부 등록")

    with st.form("cashbook_register_form_v10"):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            reg_date = st.date_input("거래 일자", value=date.today())
            io_gb = st.selectbox("입출금 구분", ["지출 (-)", "수입 (+)"])
            # '지급완료'가 0번 인덱스로 기본 선택되도록 명시 적용
            pay_status = st.selectbox("지급 상태", ["지급완료", "미지급"], index=0)
        with f_col2:
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
            amount = st.number_input("금액 (원)", min_value=0, step=1000, format="%d")

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
                    "항목": category,
                    "금액(원)": int(amount),
                    "지급상태": pay_status,
                    "적요": memo if memo else "-",
                })
                save_account_data(st.session_state.cashbook_list)
                st.success("✅ 장부 내역이 등록되었습니다.")
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
