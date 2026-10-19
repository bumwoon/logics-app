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
  bl_data = st.session_state.get("bl_data_list", [])
  client_list = st.session_state.get("client_list", [])
  client_rates = st.session_state.get("client_rates", {})
  client_infos = st.session_state.get("client_infos", {})
  supplier_list = st.session_state.get("supplier_list", [])
  supplier_rates = st.session_state.get("supplier_rates", {})
  supplier_infos = st.session_state.get("supplier_infos", {})
  ledger_data = st.session_state.get("expense_data_list", [])
  meeting_data = st.session_state.get("meeting_data_list", [])
  note_data = st.session_state.get("note_data_list", [])
  
  if bl_data:
    df_bl = pd.DataFrame(bl_data)
  else:
    df_bl = pd.DataFrame([{"안내": "등록된 B/L 물류 내역이 없습니다. 시스템 설정 및 단가/장부 데이터가 복원용으로 보관됩니다."}])

  meta_dict = {
      "client_list": client_list,
      "client_rates": client_rates,
      "client_infos": client_infos,
      "supplier_list": supplier_list,
      "supplier_rates": supplier_rates,
      "supplier_infos": supplier_infos,
      "ledger_data": ledger_data,
      "meeting_data": meeting_data,
      "note_data": note_data,
  }
  meta_json_str = json.dumps(meta_dict, ensure_ascii=False)
  df_bl["__SYSTEM_META__"] = meta_json_str

  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_bl.to_excel(writer, index=False, sheet_name="Bumwoon_Integrated_Backup")
  return output.getvalue()
  meta_json_str = json.dumps(meta_dict, ensure_ascii=False)
  df_bl["__SYSTEM_META__"] = meta_json_str

  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_bl.to_excel(writer, index=False, sheet_name="Bumwoon_Integrated_Backup")
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
    help="매출처, 매입처, 요율, 미수금, 장부 및 B/L 물류 내역이 한 번에 복원됩니다.",
)

if uploaded_integrated_file is not None:
  try:
    file_extension = uploaded_integrated_file.name.split(".")[-1].lower()
    if file_extension == "csv":
      df_in = pd.read_csv(uploaded_integrated_file)
    else:
      df_in = pd.read_excel(uploaded_integrated_file, sheet_name=0)

    if not df_in.empty:
      df_in.columns = df_in.columns.astype(str).str.strip()

      if "__SYSTEM_META__" in df_in.columns:
        meta_val = df_in["__SYSTEM_META__"].iloc[0]
        if pd.notna(meta_val) and str(meta_val).strip():
          try:
            parsed_meta = json.loads(str(meta_val))
            st.session_state.client_list = parsed_meta.get(
                "client_list", st.session_state.client_list
            )
            st.session_state.client_rates = parsed_meta.get(
                "client_rates", st.session_state.client_rates
            )
            st.session_state.client_infos = parsed_meta.get(
                "client_infos", st.session_state.client_infos
            )
            st.session_state.supplier_list = parsed_meta.get(
                "supplier_list", st.session_state.supplier_list
            )
            st.session_state.supplier_rates = parsed_meta.get(
                "supplier_rates", st.session_state.supplier_rates
            )
            st.session_state.supplier_infos = parsed_meta.get(
                "supplier_infos", st.session_state.supplier_infos
            )
            if "ledger_data" in parsed_meta:
              st.session_state.expense_data_list = parsed_meta["ledger_data"]
              save_expense_data(st.session_state.expense_data_list)

            save_client_data(
                st.session_state.client_list,
                st.session_state.client_rates,
                st.session_state.client_infos,
            )
            save_supplier_data(
                st.session_state.supplier_list,
                st.session_state.supplier_rates,
                st.session_state.supplier_infos,
            )
            if "meeting_data" in parsed_meta:
              st.session_state.meeting_data_list = parsed_meta["meeting_data"]
              save_meeting_data(st.session_state.meeting_data_list)
            if "note_data" in parsed_meta:
              st.session_state.note_data_list = parsed_meta["note_data"]
              save_note_data(st.session_state.note_data_list)     
          except Exception as me:
            print(f"Meta parse error: {me}")
        df_in = df_in.drop(columns=["__SYSTEM_META__"])

      if "B/L 번호" in df_in.columns:
        st.session_state.bl_data_list = df_in.to_dict("records")
        save_bl_data(st.session_state.bl_data_list)

      if "refresh_key" not in st.session_state:
        st.session_state.refresh_key = 0
      st.session_state.refresh_key += 1

      st.sidebar.success(
          "🎉 거래처, 요율, 미수금, 장부 및 물류 데이터 전체가 완벽하게 복원되었습니다!"
      )
      st.rerun()
  except Exception as e:
    st.sidebar.error(f"통합 데이터 복원 중 오류가 발생했습니다: {e}")


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
            
            gross_weight_sales_str = st.text_input(
                "매출 실중량(kg)", value=str(gw), placeholder="예: 1.15", key="sales_gw_input"
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
            
            gross_weight_purchase_str = st.text_input(
                "매입 실중량(kg)", value=str(gw), placeholder="예: 1.15", key="purchase_gw_input"
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
# [2] 등록 B/L 수정 및 Profit 내역
# ==========================================
elif selected_menu == "📋 등록 B/L 수정 및 Profit 내역":
    st.markdown("<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>📋 등록 B/L 수정 및 Profit 내역</h3>", unsafe_allow_html=True)
    
    if st.session_state.bl_data_list:
        df_bl = pd.DataFrame(st.session_state.bl_data_list)
        
        for col_name in ["실중량(kg)", "매출실중량(kg)", "매입실중량(kg)"]:
            if col_name in df_bl.columns:
                df_bl[col_name] = pd.to_numeric(df_bl[col_name], errors="coerce").fillna(0.0).apply(lambda x: f"{x:.2f}")

        if "선택" not in df_bl.columns:
            df_bl.insert(0, "선택", False)
            
        st.info("💡 수정할 B/L 행의 **[선택] 체크박스**를 체크하시면, 아래쪽에 내용을 상세히 수정할 수 있는 **[B/L 개별 수정 입력칸]**이 나타납니다.")
        
        edited_bl_table = st.data_editor(
            df_bl,
            hide_index=True,
            use_container_width=True,
            column_config={
                "선택": st.column_config.CheckboxColumn(required=True),
                "실중량(kg)": st.column_config.NumberColumn("실중량(kg)", format="%.2f"),
                "매출실중량(kg)": st.column_config.NumberColumn("매출실중량(kg)", format="%.2f"),
                "매입실중량(kg)": st.column_config.NumberColumn("매입실중량(kg)", format="%.2f"),
            },
            key="edit_bl_profit_table_select",
            height=300
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            delete_clicked = st.button("🚨 선택한 B/L 삭제", type="secondary", use_container_width=True)
            if delete_clicked:
                selected_rows_del = edited_bl_table[edited_bl_table["선택"] == True]
                if not selected_rows_del.empty:
                    indices_to_drop = selected_rows_del.index.tolist()
                    st.session_state.bl_data_list = [
                        item for idx, item in enumerate(st.session_state.bl_data_list) if idx not in indices_to_drop
                    ]
                    save_bl_data(st.session_state.bl_data_list)
                    st.success("🗑️ 선택한 B/L 내역이 삭제되었습니다.")
                    st.rerun()
                else:
                    st.warning("⚠️ 삭제할 B/L 행의 체크박스를 선택해주세요.")
                    
        st.markdown("---")
        
        selected_rows = edited_bl_table[edited_bl_table["선택"] == True]
        
        if len(selected_rows) == 1:
            target_idx = selected_rows.index[0]
            target_item = st.session_state.bl_data_list[target_idx]
            
            st.markdown(f"### 📝 선택한 B/L 상세 수정 칸 (Job: **{target_item.get('Job 번호', '')}** / B/L: **{target_item.get('B/L 번호', '')}**)")
            
            with st.form("detail_bl_edit_form"):
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
                    e_country = st.text_input("국가", value=str(target_item.get("국가", "")))
                    e_shipper = st.text_input("화주명(매출)", value=str(target_item.get("화주명(매출)", "")))
                    e_consignee = st.text_input("해외수하인", value=str(target_item.get("해외수하인", "")))
                    e_consignee_addr = st.text_input("해외수하인주소", value=str(target_item.get("해외수하인주소", "")))
                    e_consignee_tel = st.text_input("해외수하인전화번호", value=str(target_item.get("해외수하인전화번호", "")))
                with d_col3:
                    e_vendor = st.text_input("매입처", value=str(target_item.get("매입처", "")))
                    e_item = st.text_input("품목", value=str(target_item.get("품목", "")))
                    e_status = st.selectbox("수금 상태", ["미수", "수금완료"], index=0 if str(target_item.get("수금상태", "")) != "수금완료" else 1)
                
                st.markdown("---")
                st.markdown("#### 📦 중량(실중량 소수점 유지 / 청구중량 올림), 규격 및 금액 상세 수정")
                
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
                    st.success("✅ 선택하신 B/L의 실중량 및 청구중량이 성공적으로 수정 저장되었습니다!")
                    st.rerun()
        elif len(selected_rows) > 1:
            st.warning("⚠️ 상세 수정은 **1개씩만** 선택해서 진행해주세요.")
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
# [7] 금일발송 매니페스트
# ==========================================
elif selected_menu == "📋 금일발송 매니페스트":
    st.markdown(
        "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>📋"
        " 날짜별 발송 화물 매니페스트 (Profit 정산 포함)</h3>",
        unsafe_allow_html=True,
    )

    selected_manifest_date = st.date_input(
        "조회할 선적 날짜 선택", value=date.today(), key="manifest_date_picker"
    )
    target_date_str = str(selected_manifest_date)

    date_shipments = [
        item
        for item in st.session_state.bl_data_list
        if str(item.get("날짜", ""))[:10] == target_date_str
    ]

    if date_shipments:
        manifest_df = pd.DataFrame(date_shipments)
        
        if "실중량(kg)" not in manifest_df.columns:
            if "매출실중량(kg)" in manifest_df.columns:
                manifest_df["실중량(kg)"] = manifest_df["매출실중량(kg)"]
            else:
                manifest_df["실중량(kg)"] = manifest_df.get("매출청구중량(kg)", 1.0)
                
        base_cols = ["구분", "날짜", "Job 번호", "B/L 번호", "국가", "화주명(매출)", "해외수하인", "품목", "박스수", "부피규격", "실중량(kg)", "매출청구중량(kg)", "매입청구중량(kg)"]
        existing_cols = [c for c in base_cols if c in manifest_df.columns]
        other_cols = [c for c in manifest_df.columns if c not in existing_cols and c != "선택"]
        
        manifest_display_df = manifest_df[existing_cols + other_cols]

        st.dataframe(
            manifest_display_df,
            use_container_width=True,
            column_config={
                "실중량(kg)": st.column_config.NumberColumn(
                    "실중량(kg)", format="%.2f"
                ),
                "매출청구중량(kg)": st.column_config.NumberColumn(
                    "매출청구중량(kg)", format="%.1f"
                ),
                "매입청구중량(kg)": st.column_config.NumberColumn(
                    "매입청구중량(kg)", format="%.1f"
                ),
            },
        )

        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            csv_bytes = manifest_display_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 전체 매니페스트 다운로드 (CSV)",
                data=csv_bytes,
                file_name=f"범운해운항공_매니페스트_{target_date_str}.csv",
                mime="text/csv",
                key="manifest_csv_download",
                use_container_width=True
            )
            
        with col_dl2:
            vendor_rows = []
            for idx_v, r_v in enumerate(date_shipments, start=1):
                gw_val = r_v.get("실중량(kg)", r_v.get("매출실중량(kg)", ""))
                if gw_val == "" or gw_val is None or str(gw_val) == "-":
                    gw_val = r_v.get("매출청구중량(kg)", "-")
                
                try:
                    if float(gw_val) != int(float(gw_val)):
                        gw_val = float(gw_val)
                    else:
                        gw_val = int(float(gw_val))
                except:
                    pass

                vendor_rows.append({
                    "NO": idx_v,
                    "입고날짜": str(r_v.get("날짜", target_date_str))[:10],
                    "B/L 번호": r_v.get("B/L 번호", "-"),
                    "실중량(kg)": gw_val,
                    "부피규격(사이즈)": r_v.get("부피규격", "-"),
                    "수하인": r_v.get("해외수하인", "-"),
                    "수하인 주소": r_v.get("해외수하인주소", "-"),
                    "수하인 전화번호": r_v.get("해외수하인전화번호", "-"),
                })
            vendor_df = pd.DataFrame(vendor_rows)

            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                vendor_df.to_excel(writer, index=False, sheet_name='입고 LIST', startrow=2)
                
                workbook = writer.book
                worksheet = writer.sheets['입고 LIST']
                
                worksheet.cell(row=1, column=1, value="입고 LIST").font = openpyxl.styles.Font(size=16, bold=True, color="1E3A8A")
                
                worksheet.page_setup.orientation = worksheet.ORIENTATION_LANDSCAPE
                worksheet.page_setup.paperSize = worksheet.PAPERSIZE_A4
                worksheet.sheet_properties.pageSetUpPr.fitToPage = True
                worksheet.page_setup.fitToWidth = 1
                worksheet.page_setup.fitToHeight = 0
                
                header_fill = openpyxl.styles.PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
                header_font = openpyxl.styles.Font(color="FFFFFF", bold=True)
                thin_border = openpyxl.styles.Border(
                    left=openpyxl.styles.Side(style='thin', color='CBD5E1'),
                    right=openpyxl.styles.Side(style='thin', color='CBD5E1'),
                    top=openpyxl.styles.Side(style='thin', color='CBD5E1'),
                    bottom=openpyxl.styles.Side(style='thin', color='CBD5E1')
                )
                
                for col_num in range(1, len(vendor_df.columns) + 1):
                    cell = worksheet.cell(row=3, column=col_num)
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center")
                
                for row in worksheet.iter_rows(min_row=3, max_row=len(vendor_df) + 3, min_col=1, max_col=len(vendor_df.columns)):
                    for cell in row:
                        cell.border = thin_border
                        if cell.row > 3:
                            cell.alignment = openpyxl.styles.Alignment(vertical="center")

                for col in worksheet.columns:
                    max_len = max(len(str(cell.value or '')) for cell in col)
                    col_letter = openpyxl.utils.get_column_letter(col[0].column)
                    worksheet.column_dimensions[col_letter].width = max(max_len + 5, 12)

            st.download_button(
                "📦 [매입처 전송용] 입고 LIST 엑셀 다운로드 (.xlsx)",
                data=excel_buffer.getvalue(),
                file_name=f"입고LIST_{target_date_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="vendor_inbound_excel_download",
                use_container_width=True
            )
    else:
        st.info("선택하신 날짜로 등록된 선적 B/L 내역이 없습니다.")
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
# [11] 일계표 및 입출금 장부
# ==========================================
elif selected_menu == "💳 일계표 및 입출금 장부":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>💳"
      " 일계표 및 입출금 장부 (회계 관리)</h3>",
      unsafe_allow_html=True,
  )

  with st.form("account_form"):
    ac_col1, ac_col2 = st.columns(2)
    with ac_col1:
      acc_date = st.date_input("거래 일자", value=date.today())
      acc_type = st.selectbox("입출금 구분", ["수입 (+)", "지출 (-)"], index=1)
    with ac_col2:
      acc_category = st.selectbox(
          "비용/수입 항목", EXPENSE_CATEGORIES + INCOME_CATEGORIES
      )
      acc_amount = st.number_input("금액 (원)", value=50000, step=1000)

    acc_desc = st.text_input("적요 및 메모", value="장부 메모")

    if st.form_submit_button("💾 장부 내역 등록하기", type="primary"):
      st.session_state.expense_data_list.append({
          "날짜": str(acc_date),
          "구분": acc_type,
          "항목": acc_category,
          "금액(원)": int(acc_amount),
          "적요": acc_desc,
          "작성자": current_user_name,
      })
      save_expense_data(st.session_state.expense_data_list)
      st.success("입출금 장부에 등록되었습니다!")
      st.rerun()

  if st.session_state.expense_data_list:
    st.markdown("#### 📊 등록된 장부 내역 (수정 및 삭제 가능)")
    
    df_expense = pd.DataFrame(st.session_state.expense_data_list)
    if "선택" not in df_expense.columns:
      df_expense.insert(0, "선택", False)

    edited_expense_table = st.data_editor(
        df_expense,
        hide_index=True,
        use_container_width=True,
        column_config={"선택": st.column_config.CheckboxColumn(required=True)},
        key="edit_expense_table"
    )

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
      if st.button("💾 수정된 장부 내용 저장", type="primary", use_container_width=True):
        updated_records = edited_expense_table.drop(columns=["선택"]).to_dict("records")
        for r in updated_records:
          r["금액(원)"] = int(r.get("금액(원)", 0))
        st.session_state.expense_data_list = updated_records
        save_expense_data(st.session_state.expense_data_list)
        st.success("장부 수정 내역이 성공적으로 저장되었습니다!")
        st.rerun()
    with exp_col2:
      if st.button("🚨 선택한 장부 내역 삭제", type="secondary", use_container_width=True):
        selected_exp_rows = edited_expense_table[edited_expense_table["선택"] == True]
        if not selected_exp_rows.empty:
          indices_to_drop = selected_exp_rows.index.tolist()
          st.session_state.expense_data_list = [
              item for idx, item in enumerate(st.session_state.expense_data_list) if idx not in indices_to_drop
          ]
          save_expense_data(st.session_state.expense_data_list)
          st.success("선택한 장부 내역이 삭제되었습니다.")
          st.rerun()
        else:
          st.warning("삭제할 장부 행의 체크박스를 선택해주세요.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 📥 엑셀 다운로드 및 🖨️ PDF 인쇄용 HTML 다운로드 버튼 배치
    dl_col1, dl_col2 = st.columns(2)
    
    with dl_col1:
      output = io.BytesIO()
      with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(st.session_state.expense_data_list).to_excel(writer, index=False, sheet_name='Expense_Data')
      excel_data = output.getvalue()
      
      st.download_button(
          label="📥 엑셀 다운로드 (.xlsx)",
          data=excel_data,
          file_name=f"범운해운항공_일계표_{date.today()}.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          use_container_width=True
      )

    with dl_col2:
      # PDF 인쇄용 HTML 생성 로직
      import html as _html
      exp_print_df = pd.DataFrame(st.session_state.expense_data_list)
      
      # 합계 금액 계산
      total_amt = pd.to_numeric(exp_print_df["금액(원)"].astype(str).str.replace(r"[^\d]", "", regex=True), errors="coerce").sum() if "금액(원)" in exp_print_df.columns else 0

      table_head = "".join(f"<th>{_html.escape(str(col))}</th>" for col in exp_print_df.columns)
      table_rows = []
      for _, row in exp_print_df.iterrows():
        cells = "".join(f"<td>{_html.escape('' if pd.isna(val) else str(val))}</td>" for val in row.tolist())
        table_rows.append(f"<tr>{cells}</tr>")

      expense_html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>일계표 및 입출금 장부 - {date.today()}</title>
<style>
body{{font-family:Arial,sans-serif;margin:20px;color:#111}}
h2{{margin-bottom:4px;color:#1e3a8a}}
p{{margin-top:0;color:#555}}
button{{padding:10px 16px;margin:10px 0;background:#2563eb;color:#fff;border:none;border-radius:6px;font-weight:bold;cursor:pointer}}
table{{border-collapse:collapse;width:100%;margin-top:15px;font-size:11px}}
th,td{{border:1px solid #777;padding:8px;text-align:left}}
th{{background:#0f172a;color:#fff}}
.total-row{{background:#f1f5f9;font-weight:bold}}
@media print{{.no-print{{display:none}}@page{{size:A4 landscape;margin:10mm}}}}
</style></head>
<body>
<button class="no-print" onclick="window.print()">🖨 인쇄 및 PDF로 저장</button>
<h2>(주)범운해운항공</h2>
<p>일계표 및 입출금 장부 내역 (기준일: {date.today()})</p>
<table>
  <thead><tr>{table_head}</tr></thead>
  <tbody>
    {''.join(table_rows)}
    <tr class="total-row">
      <td colspan="3" style="text-align:right;"><b>합계 금액 (TOTAL):</b></td>
      <td colspan="{max(1, len(exp_print_df.columns)-3)}"><b>{int(total_amt):,} 원</b></td>
    </tr>
  </tbody>
</table>
</body></html>"""

      st.download_button(
          label="🖨️ 일계표 PDF 인쇄용 파일 다운로드",
          data=expense_html.encode("utf-8"),
          file_name=f"범운해운항공_일계표_{date.today()}.html",
          mime="text/html",
          use_container_width=True
      )
    
    st.caption("💡 PDF 저장 방법: 인쇄용 파일을 다운로드하여 열신 뒤, 화면 상단의 버튼을 눌러 인쇄 창에서 대상 프린터를 **'PDF로 저장'**으로 선택하시면 됩니다.")
  else:
    st.info("💡 등록된 일계표 내역이 없습니다. 위 양식을 통해 장부를 등록해 주세요.")
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
