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

    st.markdown(
        "<p style='text-align: center; font-size: 8.5pt; color: #94a3b8;"
        " margin-top: 20px;'>* 관리자 아이디: <b>lsb</b> / 비밀번호: <b>7071</b></p>",
        unsafe_allow_html=True,
    )


# 데이터 파일 경로 및 로고 공통 정의 (에러 방지를 위해 최상단 선언)
DATA_FILE = "bl_history_data.csv"
CLIENT_FILE = "client_data.csv"
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
      return df
    except Exception:
      pass
  return pd.DataFrame()


# ==========================================
# [안전한 요율표 선택 및 수정 컴포넌트 예시]
# ==========================================
def render_rate_editor_section(df_clients):
  """기존 로직을 건드리지 않고 드롭다운으로 선택하여 안전하게 수정하는 섹션"""
  st.markdown("---")
  st.subheader("📋 거래처·국가·운송형태별 단가 및 요율표 설정 (선택 수정)")

  if df_clients is None or df_clients.empty:
    st.info("등록된 데이터가 없습니다.")
    return

  # 컬럼 존재 여부 확인 후 안전하게 드롭다운 목록 생성
  col_client = "거래처" if "거래처" in df_clients.columns else df_clients.columns[0]
  col_country = "국가" if "국가" in df_clients.columns else df_clients.columns[1] if len(df_clients.columns) > 1 else col_client
  col_transport = "운송형태" if "운송형태" in df_clients.columns else df_clients.columns[2] if len(df_clients.columns) > 2 else col_client

  c1, c2, c3 = st.columns(3)
  with c1:
    client_options = df_clients[col_client].dropna().unique().tolist()
    sel_client = st.selectbox("거래처 선택", client_options, key="edit_sel_client")
  with c2:
    country_options = df_clients[df_clients[col_client] == sel_client][col_country].dropna().unique().tolist()
    sel_country = st.selectbox("국가 선택", country_options, key="edit_sel_country")
  with c3:
    transport_options = df_clients[(df_clients[col_client] == sel_client) & (df_clients[col_country] == sel_country)][col_transport].dropna().unique().tolist()
    sel_transport = st.selectbox("운송형태 선택", transport_options, key="edit_sel_transport")

  # 선택된 조건에 맞는 행 필터링
  matched_rows = df_clients[
      (df_clients[col_client] == sel_client) & 
      (df_clients[col_country] == sel_country) & 
      (df_clients[col_transport] == sel_transport)
  ]

  if not matched_rows.empty:
    st.write("선택하신 조건의 기존 데이터입니다. 아래에서 값을 변경한 뒤 저장하세요.")
    
    target_idx = matched_rows.index[0]
    row_data = matched_rows.iloc[0]

    with st.form("safe_edit_form"):
      # 기존 데이터 값을 기본값으로 세팅하되 NoneType 에러 원천 차단
      curr_item = str(row_data.get("품명", "")) if "품명" in df_clients.columns else ""
      curr_weight = float(row_data.get("기본중량(kg)", 1.0) or 1.0) if "기본중량(kg)" in df_clients.columns else 1.0
      curr_price = float(row_data.get("기본요금(원)", 0) or 0) if "기본요금(원)" in df_clients.columns else 0.0

      new_item = st.text_input("품명", value=curr_item)
      new_weight = st.number_input("기본중량(kg)", value=curr_weight)
      new_price = st.number_input("기본요금(원)", value=curr_price)

      submitted = st.form_submit_button("요율표 최종 저장하기")
      if submitted:
        # 기존 데이터프레임의 해당 인덱스만 안전하게 수정 후 저장
        if "품명" in df_clients.columns:
          df_clients.at[target_idx, "품명"] = new_item
        if "기본중량(kg)" in df_clients.columns:
          df_clients.at[target_idx, "기본중량(kg)"] = new_weight
        if "기본요금(원)" in df_clients.columns:
          df_clients.at[target_idx, "기본요금(원)"] = new_price
        
        df_clients.to_csv(CLIENT_FILE, index=False, encoding="utf-8-sig")
        st.success("기존 데이터 손상 없이 성공적으로 수정 및 저장되었습니다!")
        st.rerun()
  else:
    st.warning("선택된 조건에 일치하는 데이터가 없습니다.")
