from datetime import date, datetime
import base64
import io
import math
import os
import re
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# 페이지 설정 (와이드 모드)
st.set_page_config(
    page_title="(주)범운해운항공 종합 관리 프로그램", page_icon="🚢", layout="wide"
)

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
      "lsb": {"pw": "7071", "role": "관리자(대표)", "name": "이상복"},
      "admin": {"pw": "bomwoon123", "role": "관리자(대표)", "name": "이상복"},
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
        " 시스템</h2>",
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

    st.markdown(
        "<p style='text-align: center; font-size: 8.5pt; color: #94a3b8;"
        " margin-top: 20px;'>* 관리자 아이디: <b>lsb</b> / 비밀번호: <b>7071</b></p>",
        unsafe_allow_html=True,
    )


# 쿼리 파라미터 확인 (고객 모드 여부)
query_params = st.query_params
is_client_mode = query_params.get("mode", "") == "client"

# 로그인이 안 되어 있고 고객 모드도 아니라면 로그인 화면 출력 후 중단
if not st.session_state.logged_in_user and not is_client_mode:
  login_screen()
  st.stop()


# 로고 파일 자동 감지
LOGO_FILE = None
for filename in os.listdir("."):
  if filename.startswith("lo"):
    LOGO_FILE = filename
    break

# 로고를 Base64로 인코딩
encoded_sidebar_logo = ""
if LOGO_FILE and os.path.exists(LOGO_FILE):
  try:
    with open(LOGO_FILE, "rb") as f:
      encoded_sidebar_logo = base64.b64encode(f.read()).decode()
  except Exception:
    pass

# 데이터 파일 경로 정의
DATA_FILE = "bl_history_data.csv"
CLIENT_FILE = "client_data.csv"
ACCOUNT_FILE = "account_ledger_data.csv"
EXPENSE_FILE = "expense_data.csv"
NOTE_FILE = "daily_note_data.csv"
MEETING_FILE = "meeting_note_data.csv"
QUOTATION_FILE = "quotation_data.csv"


def load_bl_data():
  if os.path.exists(DATA_FILE):
    try:
      df = pd.read_csv(DATA_FILE)
      if "예상마진(원)" in df.columns and "예상Profit(원)" not in df.columns:
        df = df.rename(columns={"예상마진(원)": "예상Profit(원)"})
      if "수금상태" not in df.columns:
        df["수금상태"] = "미수"
      return df.to_dict("records")
    except Exception:
      return []
  return []


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

  default_clients = ["아코글로벌", "카ส", "주식회사 조은로직스"]
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
      "카ส": {
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
      "카ส": {
          "사업자등록번호": "",
          "이메일": "",
          "담당자": "",
          "전화번호": "",
          "주소": "",
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


def load_account_data():
  if os.path.exists(ACCOUNT_FILE):
    try:
      return pd.read_csv(ACCOUNT_FILE).to_dict("records")
    except Exception:
      return []
  return []


def load_expense_data():
  if os.path.exists(EXPENSE_FILE):
    try:
      df = pd.read_csv(EXPENSE_FILE)
      for possible_col in ["금액(원)", "지출금액(원)", "금액", "비용(원)", "가격"]:
        if possible_col in df.columns:
          df = df.rename(columns={possible_col: "금액(원)"})
          break
      else:
        df["금액(원)"] = 0

      if "구분" not in df.columns:
        df.insert(1, "구분", "지출 (-)")
      return df.to_dict("records")
    except Exception:
      return []
  return []


def load_note_data():
  if os.path.exists(NOTE_FILE):
    try:
      return pd.read_csv(NOTE_FILE).to_dict("records")
    except Exception:
      return []
  return []


def load_meeting_data():
  if os.path.exists(MEETING_FILE):
    try:
      df = pd.read_csv(MEETING_FILE)
      if "거래처" not in df.columns:
        df["거래처"] = "일반거래처"
      if "담당자" not in df.columns:
        df["담당자"] = "-"
      if "제목" not in df.columns:
        df["제목"] = "-"
      if "상세내용" not in df.columns:
        df["상세내용"] = "-"
      if "향후조치" not in df.columns:
        df["향후조치"] = "-"
      return df.to_dict("records")
    except Exception:
      return []
  return []


def save_bl_data(data_list):
  if data_list:
    df = pd.DataFrame(data_list)
    if "예상마진(원)" in df.columns and "예상Profit(원)" not in df.columns:
      df = df.rename(columns={"예상마진(원)": "예상Profit(원)"})
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
  else:
    if os.path.exists(DATA_FILE):
      os.remove(DATA_FILE)


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
          "품명": "보톡스 필러 (Botox & Filler)",
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


def save_account_data(data_list):
  if data_list:
    pd.DataFrame(data_list).to_csv(
        ACCOUNT_FILE, index=False, encoding="utf-8-sig"
    )
  else:
    if os.path.exists(ACCOUNT_FILE):
      os.remove(ACCOUNT_FILE)


def save_expense_data(data_list):
  if data_list:
    df_exp_save = pd.DataFrame(data_list)
    if "지출금액(원)" in df_exp_save.columns and "금액(원)" not in df_exp_save.columns:
      df_exp_save = df_exp_save.rename(columns={"지출금액(원)": "금액(원)"})
    df_exp_save.to_csv(EXPENSE_FILE, index=False, encoding="utf-8-sig")
  else:
    if os.path.exists(EXPENSE_FILE):
      os.remove(EXPENSE_FILE)


def save_note_data(data_list):
  if data_list:
    pd.DataFrame(data_list).to_csv(NOTE_FILE, index=False, encoding="utf-8-sig")
  else:
    if os.path.exists(NOTE_FILE):
      os.remove(NOTE_FILE)


def save_meeting_data(data_list):
  if data_list:
    pd.DataFrame(data_list).to_csv(
        MEETING_FILE, index=False, encoding="utf-8-sig"
    )
  else:
    if os.path.exists(MEETING_FILE):
      os.remove(MEETING_FILE)


def calculate_auto_price(client_name, cw, transport_mode="항공(Air)"):
  rates_dict = st.session_state.get("client_rates", {}).get(client_name, {})
  if rates_dict:
    for country, trans_dict in rates_dict.items():
      if isinstance(trans_dict, dict):
        item_dict = trans_dict.get(
            transport_mode, trans_dict.get("항공(Air)", {})
        )
        if isinstance(item_dict, dict):
          for item_name, r_val in item_dict.items():
            base_w = float(r_val.get("기본중량", 1.0))
            base_p = int(r_val.get("기본요금", 38000))
            add_p = int(r_val.get("추가단가", 25000))
            if cw <= base_w:
              return base_p
            else:
              return int(base_p + math.ceil(cw - base_w) * add_p)
  return int(38000 + max(0.0, cw - 1.0) * 25000)


# 세션 상태 초기화
if "client_list" not in st.session_state or not st.session_state.client_list:
  c_list, c_rates, c_infos = load_client_data()
  st.session_state.client_list = c_list
  st.session_state.client_rates = c_rates
  st.session_state.client_infos = c_infos
if "bl_data_list" not in st.session_state:
  st.session_state.bl_data_list = load_bl_data()
if "account_data_list" not in st.session_state:
  st.session_state.account_data_list = load_account_data()
if "expense_data_list" not in st.session_state:
  st.session_state.expense_data_list = load_expense_data()
if "note_data_list" not in st.session_state:
  st.session_state.note_data_list = load_note_data()
if "meeting_data_list" not in st.session_state:
  st.session_state.meeting_data_list = load_meeting_data()

TRACKING_STATUS_OPTIONS = [
    "📦 물류센터 입고 및 접수 완료",
    "🔄 수출입 통관 진행 중",
    "✈️ 항공/해상 선적 완료 (운송 중)",
    "📍 현지 공항/항만 도착",
    "🚚 현지 배송 진행 중 (Out for Delivery)",
    "✅ 배송 완료 (Delivered)",
    "⚠ 운송 지연 또는 보류",
]

# ==========================================
# [A] 고객 및 모바일 보안 화물 추적 화면 (?mode=client)
# ==========================================
if is_client_mode:
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

          barcode_b64_m = ""
          try:
            from barcode import Code128
            from barcode.writer import ImageWriter

            rv = io.BytesIO()
            Code128(str(bl_num), writer=ImageWriter()).write(
                rv, {
                    "write_text": False,
                    "module_width": 0.6,
                    "module_height": 15,
                }
            )
            barcode_b64_m = base64.b64encode(rv.getvalue()).decode()
          except:
            pass

          barcode_html_m = f"""
                        <div style="text-align: right
