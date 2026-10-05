import base64
from datetime import date
import json
import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

# ==========================================
# 페이지 설정 및 기본 스타일
# ==========================================
st.set_page_config(
    page_title="주식회사 범운해운항공 물류 관리 시스템",
    page_icon="✈️",
    layout="wide",
)

# 데이터 저장 파일명 정의
USER_DB_FILE = "user_db.json"
BL_DATA_FILE = "bl_data.json"
CLIENT_DATA_FILE = "client_data.json"
EXPENSE_DATA_FILE = "expense_data.json"
MEETING_DATA_FILE = "meeting_data.json"
NOTE_DATA_FILE = "note_data.json"

# 기본 국가 목록
COUNTRY_LIST = [
    "미국 (USA)",
    "중국 (China)",
    "홍콩 (Hong Kong)",
    "태국 (Thailand)",
    "인도네시아 (Indonesia)",
    "인디아 (India)",
    "호주 (Australia)",
    "멕시코 (Mexico)",
    "싱가포르 (Singapore)",
    "기타 국가",
]

# 입출금 카테고리
INCOME_CATEGORIES = ["운임 매출 입금", "기타 수입", "선수금"]
EXPENSE_CATEGORIES = [
    "차량 주유비",
    "차량 정비/유지비",
    "식대 및 복리후생",
    "사무용품 및 소모품",
    "통신비 및 공과금",
    "기타 지출",
]


# ==========================================
# 데이터 로드 및 저장 함수
# ==========================================
def load_user_db():
  if os.path.exists(USER_DB_FILE):
    try:
      with open(USER_DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return {
      "admin": {
          "pw": "bumwoon1971!",
          "role": "관리자(대표)",
          "name": "이상복",
      },
      "staff1": {"pw": "1234", "role": "직원", "name": "물류담당자"},
  }


def save_user_db(db):
  with open(USER_DB_FILE, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=4)


def load_bl_data():
  if os.path.exists(BL_DATA_FILE):
    try:
      with open(BL_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return []


def save_bl_data(data):
  with open(BL_DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def load_client_data():
  if os.path.exists(CLIENT_DATA_FILE):
    try:
      with open(CLIENT_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  # 기본 거래처 및 요율 구조
  default_clients = ["(주)디알하이텍", "글로벌메디칼", "K-뷰티코리아", "한성무역"]
  default_rates = {
      c: {
          "미국 (USA)": {
              "항공(Air)": {
                  "보톡스 및 의약품": {
                      "기본중량": 1.0,
                      "기본요금": 38000,
                      "추가단가": 25000,
                      "1CBM당단가": 3700000,
                  }
              }
          }
      }
      for c in default_clients
  }
  default_infos = {
      c: {
          "사업자등록번호": "123-88-00" + str(10 + i),
          "이메일": f"contact@{c.lower()}.com",
          "담당자": "담당자",
          "전화번호": "031-980-0000",
          "주소": "경기도 김포시",
      }
      for i, c in enumerate(default_clients)
  }
  return default_clients, default_rates, default_infos


def save_client_data(client_list, client_rates, client_infos):
  data = {
      "client_list": client_list,
      "client_rates": client_rates,
      "client_infos": client_infos,
  }
  with open(CLIENT_DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def load_expense_data():
  if os.path.exists(EXPENSE_DATA_FILE):
    try:
      with open(EXPENSE_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return []


def save_expense_data(data):
  with open(EXPENSE_DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def load_meeting_data():
  if os.path.exists(MEETING_DATA_FILE):
    try:
      with open(MEETING_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return []


def save_meeting_data(data):
  with open(MEETING_DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def load_note_data():
  if os.path.exists(NOTE_DATA_FILE):
    try:
      with open(NOTE_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      pass
  return []


def save_note_data(data):
  with open(NOTE_DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


# ==========================================
# 세션 상태 초기화
# ==========================================
if "user_db" not in st.session_state:
  st.session_state.user_db = load_user_db()
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
if "username" not in st.session_state:
  st.session_state.username = ""
if "user_role" not in st.session_state:
  st.session_state.user_role = ""
if "user_name" not in st.session_state:
  st.session_state.user_name = ""

if "bl_data_list" not in st.session_state:
  st.session_state.bl_data_list = load_bl_data()

c_list, c_rates, c_infos = load_client_data()
if "client_list" not in st.session_state:
  st.session_state.client_list = c_list
if "client_rates" not in st.session_state:
  st.session_state.client_rates = c_rates
if "client_infos" not in st.session_state:
  st.session_state.client_infos = c_infos

if "expense_data_list" not in st.session_state:
  st.session_state.expense_data_list = load_expense_data()
if "meeting_data_list" not in st.session_state:
  st.session_state.meeting_data_list = load_meeting_data()
if "note_data_list" not in st.session_state:
  st.session_state.note_data_list = load_note_data()


# ==========================================
# 로그인 화면 처리
# ==========================================
if not st.session_state.logged_in:
  st.markdown(
      """
        <div style='text-align: center; padding: 40px 0;'>
            <h2 style='color: #1e3a8a; font-weight: 900;'>주식회사 범운해운항공</h2>
            <p style='color: #64748b; font-size: 14px;'>BUMWOON OCEAN & AIR LOGISTICS SYSTEM</p>
        </div>
        """,
      unsafe_allow_html=True,
  )

  col1, col2, col3 = st.columns([1, 1.2, 1])
  with col2:
    with st.form("login_form"):
      st.markdown("#### 🔐 시스템 로그인")
      uid_input = st.text_input("아이디 (ID)")
      upw_input = st.text_input("비밀번호 (Password)", type="password")
      submit_btn = st.form_submit_button("로그인", use_container_width=True)

      if submit_btn:
        user_info = st.session_state.user_db.get(uid_input.strip())
        if user_info and user_info["pw"] == upw_input.strip():
          st.session_state.logged_in = True
          st.session_state.username = uid_input.strip()
          st.session_state.user_role = user_info["role"]
          st.session_state.user_name = user_info["name"]
          st.success(
              f"환영합니다, {user_info['name']} ({user_info['role']})님!"
          )
          st.rerun()
        else:
          st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
  st.stop()


# ==========================================
# 메인 사이드바 및 네비게이션
# ==========================================
current_user_name = st.session_state.user_name
current_user_role = st.session_state.user_role

with st.sidebar:
  st.markdown(
      """
        <div style='padding: 10px 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 15px;'>
            <div style='font-size: 14pt; font-weight: 900; color: #1e3a8a;'>주식회사 범운해운항공</div>
            <div style='font-size: 8.5pt; color: #64748b; font-weight: bold;'>BUMWOON OCEAN & AIR</div>
        </div>
        """,
      unsafe_allow_html=True,
  )

  st.info(
      f"👤 접속자: **{current_user_name}**님\n\n📌 직급/권한:"
      f" **{current_user_role}**"
  )

  selected_menu = st.radio(
      "📁 메뉴 선택",
      [
          "📊 물류 요약 대시보드",
          "📦 수출입 B/L 등록 및 관리",
          "🖨 B/L 운송장 인쇄",
          "📑 거래처 인보이스 발행",
          "📄 화물 견적서 발행",
          "🤝 거래처 미팅 노트",
          "📋 금일발송 매니페스트",
          "🏢 거래처 등록 요금 상세 관리",
          "💵 거래처 미수금관리",
          "💳 일계표 및 입출금 장부",
          "📝 업무용 일지",
          "🔑 직원 계정 관리 (대표님 전용)",
      ],
  )

  st.markdown("---")
  if st.button("🚪 로그아웃", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# 사이드바 로고 이미지 인코딩용 변수 준비
logo_path = "logo.png"
encoded_sidebar_logo = ""
if os.path.exists(logo_path):
  with open(logo_path, "rb") as image_file:
    encoded_sidebar_logo = base64.b64encode(image_file.read()).decode("utf-8")


# ==========================================
# 요금 자동 계산 헬퍼 함수
# ==========================================
def calculate_auto_price(client_name, weight, transport_type):
  rates = st.session_state.client_rates.get(client_name, {})
  # 기본값 설정
  base_w = 1.0
  base_p = 38000
  add_p = 25000

  try:
    for country, transports in rates.items():
      if transport_type in transports:
        for item, vals in transports[transport_type].items():
          base_w = float(vals.get("기본중량", 1.0))
          base_p = int(vals.get("기본요금", 38000))
          add_p = int(vals.get("추가단가", 25000))
          break
  except:
    pass

  if weight <= base_w:
