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
    """복잡한 인증 없이 내 컴퓨터와 구글 드라이브 양쪽에 최신 백업 파일을 동시에 자동 저장하는 이중 백업 함수"""
    file_name = "범운해운항공_전체데이터_통합백업.xlsx"

    try:
        excel_buffer = io.BytesIO()
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
        excel_buffer.seek(0)
        with open(file_name, "wb") as f:
            f.write(excel_buffer.getvalue())

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
# 🔄 백업 엑셀 파일 자동 복원 로직
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
        target_sheet = "B_L데이터" if "B_L데이터" in excel_data.sheet_names else excel_data.sheet_names[0]
        df_bl = pd.read_excel(excel_data, sheet_name=target_sheet)
        st.session_state.bl_data_list = df_bl.to_dict(orient="records")
        
        if "지출내역" in excel_data.sheet_names:
            df_exp = pd.read_excel(excel_data, sheet_name="지출내역")
            st.session_state.expense_list = df_exp.to_dict(orient="records")
            
        st.session_state["auto_backup_loaded"] = True
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
  if os.path.exists(ACCOUNT_FILE):
    try:
      return pd.read_csv(ACCOUNT_FILE).fillna("").to_dict("records")
    except Exception as e:
      print(f"일계표 데이터 읽기 오류: {e}")
  return []

def save_account_data(data_list):
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
      "0": "212222", "1": "222122", "2": "222221", "3": "121223", "4": "121322",
      "5": "131222", "6": "122213", "7": "122312", "8": "132212", "9": "221213",
      "A": "212321", "B": "232121", "C": "113222", "D": "123122", "E": "123221",
      "F": "223112", "G": "223211", "H": "212231", "I": "231221", "J": "221321",
      "K": "312122", "L": "321122", "M": "321221", "N": "312212", "O": "322112",
      "P": "322211", "Q": "212132", "R": "212312", "S": "232112", "T": "213122",
      "U": "311222", "V": "321112", "W": "322102", "X": "312112", "Y": "321211",
      "Z": "212113", "-": "112232", ".": "122132", " ": "122231", "default": "212222",
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

# 세션 초기화
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
    # 관리자 메뉴 화면
    st.sidebar.markdown("### 🛠️ 관리자 메뉴")
    admin_menu = st.sidebar.radio("메뉴 선택", ["화물 관리", "매출/정산", "백업 관리"])
    if admin_menu == "백업 관리":
      st.markdown("### 💾 데이터 이중 백업 시스템")
      if st.button("🔄 지금 즉시 컴퓨터 & 구글드라이브 이중 백업 실행", type="primary"):
        simple_dual_backup()
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

  # ==========================================
  # 📦 [첫 화면 바로 아래에 노출되는 화주(고객) 전용 입고 리스트 작성 칸]
  # ==========================================
  st.markdown("---")
  st.markdown(
      "<div style='background-color: #f1f5f9; padding: 18px; border-radius: 10px; border-left: 6px solid #2563eb; margin-top: 15px;'>"
      "<h3 style='color: #1e3a8a; margin: 0 0 5px 0;'>📦 화주(고객) 전용 화물 입고 리스트 직접 작성 시스템</h3>"
      "<p style='color: #475569; font-size: 13.5px; margin: 0;'>고객 계정으로 로그인하시면, 카톤수·실중량·5000 부피중량·수하인 주소 및 전화번호를 직접 입력하고 사내 시스템에 즉시 등록하실 수 있습니다.</p>"
      "</div>",
      unsafe_allow_html=True
  )
  st.markdown("<br>", unsafe_allow_html=True)

  if "client_logged_in" not in st.session_state:
      st.session_state.client_logged_in = False
  if "client_user_id" not in st.session_state:
      st.session_state.client_user_id = ""

  client_user_db = {}
  for uid, info in st.session_state.get("user_db", {}).items():
      if info.get("role") == "화주(고객)":
          client_user_db[uid] = info

  if not client_user_db:
      client_user_db = {"ako": {"pw": "1234", "role": "화주(고객)", "name": "아코글로벌"}}

  # [로그인 전] 화주 아이디 / 비밀번호 입력 폼
  if not st.session_state.get("client_logged_in"):
      col_lf1, col_lf2, col_lf3 = st.columns([1, 1.5, 1])
      with col_lf2:
          with st.form("home_client_direct_login_form"):
              st.markdown("##### 🔐 화주(고객) 로그인")
              input_cid = st.text_input("고객 아이디 (ID)")
              input_cpw = st.text_input("비밀번호 (Password)", type="password")
              submit_cl = st.form_submit_button("로그인", use_container_width=True)
              
              if submit_cl:
                  if input_cid in client_user_db and client_user_db[input_cid]["pw"] == input_cpw:
                      st.session_state.client_logged_in = True
                      st.session_state.client_user_id = input_cid
                      st.success("로그인 성공!")
                      st.rerun()
                  else:
                      st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

  # [로그인 후] 고객이 직접 입고 리스트를 작성하는 칸
  else:
      c_uid = st.session_state.client_user_id
      c_info = client_user_db.get(c_uid, {"name": "고객사"})
      c_name = c_info.get("name", "고객사")

      top_col1, top_col2 = st.columns([4, 1])
      with top_col1:
          st.markdown(f"### 🎉 [{c_name}]님 환영합니다! 입고 리스트를 작성해 주세요.")
      with top_col2:
          if st.button("로그아웃"):
              st.session_state.client_logged_in = False
              st.session_state.client_user_id = ""
              st.rerun()

      with st.form("client_inline_inbound_form"):
          st.markdown("#### 📝 입고 정보 및 배송지(수하인) 입력")
          
          ic1, ic2 = st.columns(2)
          with ic1:
              inbound_date = st.date_input("입고 예정일", value=date.today())
              item_name = st.selectbox("품목 선택", ["보톡스", "필러", "화장품", "일반공산품", "기타"])
              consignee_name = st.text_input("해외 수하인 성명 (Consignee)", placeholder="예: John Doe")
              consignee_tel = st.text_input("해외 수하인 전화번호", placeholder="예: +1-212-555-0199")
          with ic2:
              carton_cnt = st.number_input("카톤 수 (박스 수 CTN)", min_value=1, value=1, step=1)
              gross_weight = st.number_input("실중량 (kg) [소수점 가능]", min_value=0.0, value=1.0, step=0.01, format="%.2f")
              consignee_addr = st.text_input("해외 수하인 상세 주소", placeholder="예: 123 Main St, New York, NY 10001")

          st.markdown("---")
          st.markdown("#### 📐 박스 규격 입력 (부피중량 5000 Divisor 자동 계산)")
          
          b_c1, b_c2, b_c3 = st.columns(3)
          with b_c1:
              w_cm = st.number_input("가로 (cm)", min_value=0.0, value=0.0)
          with b_c2:
              l_cm = st.number_input("세로 (cm)", min_value=0.0, value=0.0)
          with b_c3:
              h_cm = st.number_input("높이 (cm)", min_value=0.0, value=0.0)

          cbm_calc = 0.0
          vol_weight_5000 = 0.0
          if w_cm > 0 and l_cm > 0 and h_cm > 0:
              cbm_calc = ((w_cm * l_cm * h_cm) / 1000000.0) * carton_cnt
              vol_weight_5000 = ((w_cm * l_cm * h_cm) / 5000.0) * carton_cnt

          st.info(f"💡 자동 계산 결과: CBM = {cbm_calc:.3f} CBM | 5000기준 부피중량 = {vol_weight_5000:.2f} kg")

          memo = st.text_area("요청사항 및 메모")
          
          submit_btn = st.form_submit_button("🚀 입고 리스트 등록 및 사내 시스템 전송", type="primary", use_container_width=True)
          
          if submit_btn:
              if not consignee_name.strip() or not consignee_addr.strip():
                  st.warning("⚠️ 해외 수하인 성명과 상세 주소는 필수 입력 사항입니다.")
              else:
                  bl_list = st.session_state.get("bl_data_list", [])
                  dim_str = f"{int(w_cm)}×{int(l_cm)}×{int(h_cm)}cm({carton_cnt}CTN)" if w_cm > 0 else "-"
                  
                  new_record = {
                      "구분": "수출 (Export)",
                      "날짜": str(inbound_date),
                      "Job 번호": f"INB-{date.today().strftime('%Y%m%d')}-{len(bl_list)+1:03d}",
                      "B/L 번호": "접수대기 (사내확인)",
                      "국가": "미국",
                      "출발지": "대한민국 (KOREA)",
                      "화주명(매출)": c_name,
                      "해외수하인": consignee_name,
                      "해외수하인주소": consignee_addr,
                      "해외수하인전화번호": consignee_tel,
                      "매입처": "-",
                      "운송형태": "항공(Air)",
                      "서비스옵션": "Door To Door",
                      "품목": item_name,
                      "박스수": f"{carton_cnt} 박스(CTN)",
                      "부피규격": dim_str,
                      "실중량(kg)": float(gross_weight),
                      "매출실중량(kg)": float(gross_weight),
                      "매입실중량(kg)": float(gross_weight),
                      "매출청구중량(kg)": float(math.ceil(max(gross_weight, vol_weight_5000))),
                      "매입청구중량(kg)": float(math.ceil(max(gross_weight, vol_weight_5000))),
                      "CBM": f"{cbm_calc:.3f} CBM",
                      "현재 상태": "📦 고객 입고 제출 완료",
                      "수금상태": "미수",
                      "매출액(원)": 0,
                      "매입액(원)": 0,
                      "예상Profit(원)": 0,
                      "비고": memo,
                      "최종작성자": f"고객({c_name})",
                      "최종수정자": "-",
                  }

                  if "bl_data_list" not in st.session_state:
                      st.session_state.bl_data_list = []
                  st.session_state.bl_data_list.append(new_record)
                  save_bl_data(st.session_state.bl_data_list)
                  st.success("🎉 입고 리스트가 성공적으로 등록되어 사내 시스템에 연동되었습니다!")
                  st.rerun()

      # 고객이 본인이 등록한 내역 확인하는 표
      st.markdown("---")
      st.markdown(f"#### 📋 [{c_name}] 내 입고 등록 및 처리 내역")
      my_inbound_list = [
          item for item in st.session_state.get("bl_data_list", [])
          if str(item.get("화주명(매출)", "")).strip() == c_name
      ]
      if my_inbound_list:
          df_my = pd.DataFrame(my_inbound_list)[
              ["날짜", "Job 번호", "B/L 번호", "해외수하인", "해외수하인전화번호", "해외수하인주소", "박스수", "부피규격", "실중량(kg)", "현재 상태"]
          ]
          st.dataframe(df_my, use_container_width=True, hide_index=True)
      else:
          st.info("등록된 입고 내역이 없습니다.")

  st.stop()
