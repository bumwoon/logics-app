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
# [로고 이미지 Base64 직접 내장 (파일 불필요)]
# ==========================================
LOGO_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAZAAAADQAQMAAADbT29PAAAABlBMVEUAAAD///+l2Z/dAAAACXBIWXMAAA7DAAAOwwHHb6hkAAAA"
    "B3RJTUUH5gYQESkX3f3qTwAAAAlwSFlzAAALEgAACxIB0t1+/AAAAARnQU1BAACxjwv8YQUAAABJSURBVHja7cExAQAAAMKg9U9t"
    "DB8gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIDvARJbAAE0y0oZAAAAAElFTkSuQmCC"
)

# ==========================================
# [데이터 파일 경로 정의 및 로드 함수]
# ==========================================
ACCOUNT_USER_FILE = "system_user_accounts.csv"
DATA_FILE = "bl_history_data.csv"
CLIENT_FILE = "client_data.csv"
ACCOUNT_FILE = "account_ledger_data.csv"
EXPENSE_FILE = "expense_data.csv"
NOTE_FILE = "daily_note_data.csv"
MEETING_FILE = "meeting_note_data.csv"
QUOTATION_FILE = "quotation_data.csv"


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
      "admin": {"pw": "bomwoon123", "role": "관리자(대표)", "name": "이상복"}
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
  st.session_state.account_data_list = (
      pd.read_csv(ACCOUNT_FILE).to_dict("records")
      if os.path.exists(ACCOUNT_FILE)
      else []
  )
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
# [외부 고객용 화물 추적 화면 - 로그인 불필요]
# ==========================================
query_params = st.query_params
is_client_mode = query_params.get("mode", "") == "client"

if is_client_mode:
  st.image(
      base64.b64decode(LOGO_BASE64), width=220
  )  # 외부 파일 없이 바로 출력
  st.markdown("### **(주)범운해운항공**")
  st.markdown("BUMWOON OCEAN & AIR CO., LTD.")
  st.markdown("---")

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

          logo_html_tag = (
              f"<img src='data:image/png;base64,{LOGO_BASE64}'"
              " style='height: 38px;'>"
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
                        <div style="text-align: right;">
                            {f"<img src='data:image/png;base64,{barcode_b64_m}' style='height: 32px; max-width: 150px; display: block; margin-left: auto;'>" if barcode_b64_m else ""}
                            <div style="font-size: 9.5pt; font-weight: 900; color: #0f172a; margin-top: 2px;">{bl_num}</div>
                        </div>
                    """

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
                                            {logo_html_tag}
                                            <div style="margin-left: 8px;">
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
                                        <b>수하인:</b> <span style="color: #1e3a8a; font-weight: bold;">{consignee_n}</span><br>
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
          components.html(mobile_awb_html, height=750, scrolling=True)
  st.stop()


# ==========================================
# [내부 로그인 화면]
# ==========================================
def login_screen():
  st.markdown("<br><br>", unsafe_allow_html=True)
  col1, col2, col3 = st.columns([1, 1.2, 1])

  with col2:
    st.image(base64.b64decode(LOGO_BASE64), width=150)
    st.markdown("### 🚢 범운해운항공 물류 시스템")
    st.markdown("관계자 외 접속이 제한된 보안 구역입니다.")
    st.markdown("<br>", unsafe_allow_html=True)

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
        "* 초기 관리자 아이디: **admin** / 비밀번호: **bomwoon123**"
    )


if not st.session_state.logged_in_user:
  login_screen()
  st.stop()


# ==========================================
# [B] 사장님 전용 관리자 프로그램 화면
# ==========================================
st.sidebar.image(base64.b64decode(LOGO_BASE64), width=180)

st.sidebar.markdown("### (주)범운해운항공")
st.sidebar.markdown("BUMWOON OCEAN & AIR CO., LTD.")
st.sidebar.markdown("---")

st.sidebar.info(
    f"현재 접속자: **{st.session_state.user_db[st.session_state.logged_in_user]['name']}**님\n\n(권한:"
    f" {st.session_state.user_role})"
)
if st.sidebar.button("로그아웃"):
  st.session_state.logged_in_user = None
  st.session_state.user_role = None
  st.rerun()

st.sidebar.markdown("---")

menu_options = [
    "📊 수출입 B/L 등록",
    "📋 등록 B/L 수정 및 Profit 내역",
    "🚢 B/L 운송장 출력",
    "📑 거래처 인보이스 발행",
    "📄 화물 견적서 발행",
    "🤝 거래처 미팅 노트",
    "📋 금일발송 매니페스트",
    "🏢 거래처 등록 요금 상세 관리",
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
    "고객들에게 아래 주소를 안내해주시면 로그인 없이 실시간 조회가"
    " 가능합니다:<br>`https://your-app-url.streamlit.app/?mode=client`",
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

# 상단 메인 헤더 영역
header_col1, header_col2 = st.columns([1, 6])
with header_col1:
  st.image(base64.b64decode(LOGO_BASE64), width=100)
with header_col2:
  st.markdown("### 🚢 (주)범운해운항공 종합 관리 프로그램")
  st.markdown(
      "Job별 Profit 정산, 거래처별 요율 관리 및 스마트 인보이스 발행"
      " 시스템"
  )

st.markdown("---")

# ==========================================
# [1] 수출입 B/L 등록 메뉴
# ==========================================
if selected_menu == "📊 수출입 B/L 등록":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 15px;'>📋"
      " 수출입 B/L 및 Profit 등록 관리</h3>",
      unsafe_allow_html=True,
  )

  st.markdown(
      "##### 📦 박스 규격 및 카톤수 입력 (아래 입력창에 가로, 세로, 높이,"
      " 카톤수를 적어주시면 즉시 부피중량과 CBM이 계산됩니다)"
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
        "실 중량 (kg)", value="55.0", placeholder="실중량", key="common_gw"
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
    dest_country = st.selectbox("도착 국가", COUNTRY_LIST)
    origin_place = st.text_input("출발지", value="대한민국 (KOREA)")
    item_desc = st.text_input(
        "품명",
        value=(
            "보톡스, 필러 및 관련 의약품/미용용품 (Botox, Filler & Related"
            " Pharmaceuticals/Cosmetics)"
        ),
    )

    shipper_options = [""] + st.session_state.client_list
    shipper_name = st.selectbox(
        "화주명 (매출처)",
        options=shipper_options,
        index=1 if len(shipper_options) > 1 else 0,
    )

    consignee_name = st.text_input("해외 수하인")

    purchase_vendor = st.selectbox(
        "매입처 (비용처)",
        options=shipper_options,
        index=2 if len(shipper_options) > 2 else 0,
    )

    transport_type = st.selectbox("운송 형태", ["항공(Air)", "해상(LCL)"])
    service_option = st.selectbox("서비스 옵션", ["Door To Door"])
    tracking_status = st.selectbox(
        "현재 진행 상태 선택", options=TRACKING_STATUS_OPTIONS
    )
    payment_status_input = st.selectbox(
        "수금 상태", options=["미수", "수금완료"], index=0
    )

  with form_col2:
    piece_count = st.text_input("총 박스 수 (Piece)", value=piece_count_val)
    volume_dim = st.text_input("부피 규격 (Volume)", value=volume_str_result)

    gross_weight_sales = st.number_input(
        "매출 실중량(kg)", value=float(gw), min_value=0.0
    )
    sales_chargeable_weight = st.number_input(
        "매출 청구중량(kg) [자동 계산]",
        value=float(calc_sales_cw),
        min_value=0.0,
        step=1.0,
    )

    auto_sales_price = calculate_auto_price(
        shipper_name, sales_chargeable_weight, transport_type
    )

    total_sales = st.number_input(
        "총 매출액 (원) [자동 계산 및 수정 가능]",
        value=int(auto_sales_price),
        min_value=0,
        step=1000,
        format="%d",
    )

    gross_weight_purchase = st.number_input(
        "매입 실중량(kg)", value=float(gw), min_value=0.0
    )
    purchase_chargeable_weight = st.number_input(
        "매입 청구중량(kg) [자동 계산]",
        value=float(calc_purchase_cw),
        min_value=0.0,
        step=1.0,
    )

    auto_purchase_price = calculate_auto_price(
        purchase_vendor, purchase_chargeable_weight, transport_type
    )

    total_purchase = st.number_input(
        "총 매입액 (원) [자동 계산 및 수정 가능]",
        value=int(auto_purchase_price),
        min_value=0,
        step=1000,
        format="%d",
    )

  remarks = st.text_area("비고")

  st.markdown("---")
  preview_profit = int(total_sales) - int(total_purchase)
  st.markdown(
      f"""
    <div style="background-color: #f8fafc; border: 1.5px solid #2563eb; padding: 14px 18px; border-radius: 8px; margin-bottom: 12px;">
        <b>🔍 [B/L 등록 전 실시간 미리보기 요약]</b><br>
        • 총 CBM: <b>{total_cbm:.3f} CBM</b> | 총 카톤수: <b>{total_ctn}박스</b><br>
        • 화주명(매출처): <b style="color: #1e3a8a;">{shipper_name if shipper_name else '미선택'}</b> (청구중량: <b>{sales_chargeable_weight}kg</b>) → 청구금액: <b style="color: #1e3a8a; font-size: 11pt;">{int(total_sales):,} 원</b><br>
        • 매입처(비용처): <b style="color: #b91c1c;">{purchase_vendor if purchase_vendor else '미선택'}</b> (청구중량: <b>{purchase_chargeable_weight}kg</b>) → 매입금액: <b style="color: #b91c1c; font-size: 11pt;">{int(total_purchase):,} 원</b><br>
        • 예상 Profit (마진): <span style="color: #047857; font-size: 12pt;"><b>{preview_profit:,} 원</b></span> | 수금상태: <b>{payment_status_input}</b>
    </div>
    """,
      unsafe_allow_html=True,
  )

  if st.button(
      "💾 B/L 및 Profit 최종 등록하기", type="primary", use_container_width=True
  ):
    if job_no.strip() and shipper_name.strip():
      st.session_state.bl_data_list.append({
          "구분": io_type,
          "날짜": str(reg_date),
          "Job 번호": job_no,
          "B/L 번호": bl_no,
          "국가": dest_country,
          "출발지": origin_place,
          "화주명(매출)": shipper_name,
          "해외수하인": consignee_name,
          "매입처": purchase_vendor,
          "운송형태": transport_type,
          "서비스옵션": service_option,
          "품목": item_desc,
          "박스수": piece_count,
          "부피규격": volume_dim,
          "매출청구중량(kg)": sales_chargeable_weight,
          "매입청구중량(kg)": purchase_chargeable_weight,
          "CBM": f"{total_cbm:.3f} CBM",
          "현재 상태": tracking_status,
          "수금상태": payment_status_input,
          "매출액(원)": int(total_sales),
          "매입액(원)": int(total_purchase),
          "예상Profit(원)": preview_profit,
          "비고": remarks,
      })
      save_bl_data(st.session_state.bl_data_list)
      st.success(
          f"🎉 [성공] B/L 및 Job 번호({job_no})가 성공적으로 등록되었습니다!"
      )
    else:
      st.warning(
          "⚠️ [경고] 'Job 번호'와 '화주명'은 반드시 입력하셔야 등록됩니다."
      )


# ==========================================
# [2] 등록 B/L 수정 및 Profit 내역
# ==========================================
elif selected_menu == "📋 등록 B/L 수정 및 Profit 내역":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 5px;'>📋"
      " 등록 B/L 수정 및 Profit 내역</h3>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748b; font-size: 13px; margin-bottom: 15px;'>수정할"
      " B/L 행의 <b>선택(체크박스)</b>을 체크한 뒤, 아래의 <b>[✏️ 선택한 B/L"
      " 수정하기]</b> 버튼을 누르면 상세 수정 화면이 열립니다.</p>",
      unsafe_allow_html=True,
  )

  if st.session_state.bl_data_list:
    df_bl = pd.DataFrame(st.session_state.bl_data_list)
    if "선택" not in df_bl.columns:
      df_bl.insert(0, "선택", False)
    if "수금상태" not in df_bl.columns:
      df_bl["수금상태"] = "미수"

    edited_table = st.data_editor(
        df_bl,
        hide_index=True,
        use_container_width=True,
        column_config={"선택": st.column_config.CheckboxColumn(required=True)},
        key="bl_select_table",
    )

    selected_rows = edited_table[edited_table["선택"] == True]

    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
      if st.button(
          "✏️ 선택한 B/L 수정하기", type="primary", use_container_width=True
      ):
        if len(selected_rows) == 1:
          st.session_state.edit_target_index = edited_table[
              edited_table["선택"] == True
          ].index[0]
          st.rerun()
        elif len(selected_rows) == 0:
          st.warning("수정할 B/L 행의 체크박스를 선택해주세요.")
        else:
          st.warning(
              "수정은 한 번에 하나의 B/L만 선택하여 진행하실 수 있습니다."
          )

    with col_btn2:
      if st.button(
          "💰 선택 건 [수금완료] 일괄처리", use_container_width=True
      ):
        if len(selected_rows) > 0:
          for idx in selected_rows.index.tolist():
            st.session_state.bl_data_list[idx]["수금상태"] = "수금완료"
          save_bl_data(st.session_state.bl_data_list)
          st.success(
              "선택하신 B/L 건들이 '수금완료' 상태로 업데이트되었습니다!"
          )
          st.rerun()
        else:
          st.warning("수금완료 처리할 B/L 행을 선택해주세요.")

    with col_btn3:
      if st.button(
          "🗑 선택한 B/L 삭제하기", type="secondary", use_container_width=True
      ):
        if len(selected_rows) > 0:
          indices_to_drop = selected_rows.index.tolist()
          st.session_state.bl_data_list = [
              item
              for i, item in enumerate(st.session_state.bl_data_list)
              if i not in indices_to_drop
          ]
          save_bl_data(st.session_state.bl_data_list)
          st.success("선택하신 B/L 내역이 삭제되었습니다!")
          st.rerun()
        else:
          st.warning("삭제할 B/L 행의 체크박스를 선택해주세요.")

    if "edit_target_index" in st.session_state:
      idx = st.session_state.edit_target_index
      if idx < len(st.session_state.bl_data_list):
        target_item = st.session_state.bl_data_list[idx]
        st.markdown("---")
        st.markdown(
            f"#### 📝 [B/L 번호: {target_item.get('B/L 번호', '')}] 상세 수정"
            " 화면"
        )

        with st.form("detail_edit_form"):
          e_col1, e_col2 = st.columns(2)
          with e_col1:
            u_io = st.selectbox(
                "수출입 구분",
                ["수출 (Export)", "수입 (Import)"],
                index=(
                    0
                    if str(target_item.get("구분", "수출 (Export)"))
                    .startswith("수출")
                    else 1
                ),
            )
            u_job = st.text_input(
                "Job 번호", value=str(target_item.get("Job 번호", ""))
            )
            u_bl = st.text_input(
                "B/L 번호", value=str(target_item.get("B/L 번호", ""))
            )
            try:
              d_val = date.fromisoformat(
                  str(target_item.get("날짜", date.today()))
              )
            except:
              d_val = date.today()
            u_date = st.date_input("선적 날짜", value=d_val)
            u_country = st.selectbox(
                "도착 국가",
                COUNTRY_LIST,
                index=(
                    COUNTRY_LIST.index(str(target_item.get("국가", "미국")))
                    if str(target_item.get("국가")) in COUNTRY_LIST
                    else 0
                ),
            )
            u_origin = st.text_input(
                "출발지", value=str(target_item.get("출발지", ""))
            )
            u_item = st.text_input(
                "품명", value=str(target_item.get("품목", ""))
            )

            cur_status_val = str(
                target_item.get("현재 상태", TRACKING_STATUS_OPTIONS[0])
            )
            s_idx_val = (
                TRACKING_STATUS_OPTIONS.index(cur_status_val)
                if cur_status_val in TRACKING_STATUS_OPTIONS
                else 0
            )
            u_tracking_status = st.selectbox(
                "현재 진행 상태 수정",
                options=TRACKING_STATUS_OPTIONS,
                index=s_idx_val,
            )

            cur_pay_status = str(target_item.get("수금상태", "미수"))
            p_idx_val = 0 if cur_pay_status != "수금완료" else 1
            u_pay_status = st.selectbox(
                "수금 상태 (미수 / 수금완료)",
                options=["미수", "수금완료"],
                index=p_idx_val,
            )

          with e_col2:
            shipper_options = [""] + st.session_state.client_list
            s_idx = (
                shipper_options.index(str(target_item.get("화주명(매출)", "")))
                if str(target_item.get("화주명(매출)")) in shipper_options
                else 0
            )
            u_shipper = st.selectbox(
                "화주명", options=shipper_options, index=s_idx
            )
            u_consignee = st.text_input(
                "해외 수하인", value=str(target_item.get("해외수하인", ""))
            )
            v_idx = (
                shipper_options.index(str(target_item.get("매입처", "")))
                if str(target_item.get("매입처")) in shipper_options
                else 0
            )
            u_vendor = st.selectbox(
                "매입처", options=shipper_options, index=v_idx
            )
            t_options = ["항공(Air)", "해상(LCL)"]
            t_idx = (
                t_options.index(str(target_item.get("운송형태", "항공(Air)")))
                if str(target_item.get("운송형태")) in t_options
                else 0
            )
            u_transport = st.selectbox(
                "운송 형태", options=t_options, index=t_idx
            )

            u_sales_cw = st.number_input(
                "매출 청구중량 (kg)",
                value=float(target_item.get("매출청구중량(kg)", 1.0)),
                min_value=0.0,
                step=0.5,
            )
            u_purchase_cw = st.number_input(
                "매입 청구중량 (kg)",
                value=float(target_item.get("매입청구중량(kg)", 1.0)),
                min_value=0.0,
                step=0.5,
            )

            u_sales = st.number_input(
                "총 매출액 (원)",
                value=int(target_item.get("매출액(원)", 0)),
                step=1000,
                format="%d",
            )
            u_purchase = st.number_input(
                "총 매입액 (원)",
                value=int(target_item.get("매출액(원)", 0)),
                step=1000,
                format="%d",
            )
            u_remarks = st.text_area(
                "비고", value=str(target_item.get("비고", ""))
            )

          if st.form_submit_button(
              "💾 수정 완료 및 저장하기", type="primary", use_container_width=True
          ):
            st.session_state.bl_data_list[idx] = {
                "구분": u_io,
                "날짜": str(u_date),
                "Job 번호": u_job,
                "B/L 번호": u_bl,
                "국가": u_country,
                "출발지": u_origin,
                "화주명(매출)": u_shipper,
                "해외수하인": u_consignee,
                "매입처": u_vendor,
                "운송형태": u_transport,
                "서비스옵션": str(
                    target_item.get("서비스옵션", "Door To Door")
                ),
                "품목": u_item,
                "박스수": target_item.get("박스수", "1 박스"),
                "부피규격": target_item.get("부피규격", "-"),
                "CBM": target_item.get("CBM", "-"),
                "매출청구중량(kg)": u_sales_cw,
                "매입청구중량(kg)": u_purchase_cw,
                "현재 상태": u_tracking_status,
                "수금상태": u_pay_status,
                "매출액(원)": u_sales,
                "매입액(원)": u_purchase,
                "예상Profit(원)": u_sales - u_purchase,
                "비고": u_remarks,
            }
            save_bl_data(st.session_state.bl_data_list)
            del st.session_state.edit_target_index
            st.success("B/L 정보 및 수금 상태가 안전하게 수정되었습니다!")
            st.rerun()
  else:
    st.info("등록된 B/L 내역이 없습니다.")


# ==========================================
# [3] B/L 운송장 출력 메뉴
# ==========================================
elif selected_menu == "🚢 B/L 운송장 출력":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>🚢"
      " (주)범운해운항공 정식 B/L 운송장 출력</h3>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='color: #64748b; font-size: 13px; margin-bottom: 20px;'>등록된"
      " B/L 번호를 선택하시면, 범운해운항공 로고와 바코드, 화주 및 수하인"
      " 정보, 부피 규격, 청구중량이 포함된 정식 운송장(AWB) 양식이"
      " 생성됩니다.</p>",
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

      logo_embed_bl = f"<img src='data:image/png;base64,{LOGO_BASE64}' style='height: 42px; vertical-align: middle; margin-right: 10px;'>"

      barcode_b64 = ""
      try:
        from barcode import Code128
        from barcode.writer import ImageWriter

        rv = io.BytesIO()
        Code128(str(bl_num_str), writer=ImageWriter()).write(
            rv, {"write_text": False, "module_width": 0.6, "module_height": 15}
        )
        barcode_b64 = base64.b64encode(rv.getvalue()).decode()
      except:
        pass

      barcode_html = f"""
                <div style="text-align: right;">
                    {f"<img src='data:image/png;base64,{barcode_b64}' style='height: 38px; max-width: 180px; display: block; margin-left: auto;'>" if barcode_b64 else ""}
                    <div style="font-size: 10pt; font-weight: 900; color: #0f172a; margin-top: 3px; letter-spacing: 0.5px;">{bl_num_str}</div>
                </div>
            """

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
                    body {{
                        font-family: 'Pretendard', sans-serif;
                        color: #1e293b;
                        font-size: 9.5pt;
                        line-height: 1.3;
                        margin: 0;
                        padding: 10px;
                        background-color: #ffffff;
                    }}
                    .awb-container {{
                        max-width: 760px;
                        margin: 0 auto;
                        border: 2px solid #0f172a;
                        padding: 20px;
                        border-radius: 6px;
                        background-color: #ffffff;
                    }}
                    .top-table, .mid-table, .bottom-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 8px;
                    }}
                    .top-table td, .mid-table td, .bottom-table td {{
                        border: 1px solid #64748b;
                        padding: 8px 10px;
                        vertical-align: top;
                    }}
                    .section-header {{
                        background-color: #0f172a;
                        color: white;
                        font-weight: bold;
                        font-size: 9pt;
                        padding: 3px 6px;
                        margin-bottom: 4px;
                    }}
                    .print-btn {{
                        display: block;
                        width: 100%;
                        background-color: #2563eb;
                        color: white;
                        text-align: center;
                        padding: 10px;
                        font-size: 11pt;
                        font-weight: bold;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        margin-bottom: 15px;
                    }}
                    .print-btn:hover {{ background-color: #1d4ed8; }}
                </style>
            </head>
            <body>
                <div class="awb-container">
                    <button class="print-btn no-print" onclick="window.print()">🖨 B/L 운송장 인쇄 및 PDF 저장 (Print / Save as PDF)</button>

                    <table style="width: 100%; border-bottom: 2.5px solid #0f172a; padding-bottom: 10px; margin-bottom: 12px;">
                        <tr>
                            <td style="width: 55%; border: none;">
                                <div style="display: flex; align-items: center;">
                                    {logo_embed_bl}
                                    <div>
                                        <div style="font-size: 14pt; font-weight: 900; color: #1e3a8a;">주식회사 범운해운항공</div>
                                        <div style="font-size: 7.5pt; color: #475569; font-weight: bold;">BUMWOON OCEAN & AIR CO., LTD. | www.bumwoon.com</div>
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
                                <b>사업자번호:</b> {shipper_bno}<br>
                                <b>주소:</b> {shipper_addr}<br>
                                <b>담당자 / 연락처:</b> {shipper_mgr} / {shipper_tel}<br>
                                <div style="margin-top: 8px; font-size: 8pt; color: #64748b;">SENT BY: 사장실 / Date: {ship_date}</div>
                            </td>
                            <td style="width: 50%;">
                                <div class="section-header">TO (CONSIGNEE / 수하인)</div>
                                <b>수하인명:</b> <span style="font-size: 10.5pt; color: #1e3a8a; font-weight: bold;">{consignee_n}</span><br>
                                <b>도착 국가:</b> {dest_c}<br>
                                <b>출발지:</b> {origin_p}<br>
                                <div style="margin-top: 14px; font-size: 8pt; color: #64748b;">ATTENTION OF: 현지 담당자 앞 / TEL: -</div>
                            </td>
                        </tr>
                    </table>

                    <table class="mid-table">
                        <tr>
                            <td style="width: 33%;">
                                <div style="font-weight: bold; font-size: 8.5pt; color: #0f172a; margin-bottom: 4px;">CARRIER / 운송수단</div>
                                {air_check} AIR &nbsp;&nbsp;&nbsp; {sea_check} SEA (LCL)<br>
                                <span style="font-size: 8pt; color: #64748b;">Service: {transport_t}</span>
                            </td>
                            <td style="width: 33%;">
                                <div style="font-weight: bold; font-size: 8.5pt; color: #0f172a; margin-bottom: 4px;">SERVICE OPTION</div>
                                {d2d_check} Door To Door<br>
                                <span style="font-size: 8pt; color: #64748b;">Status: {current_status_str}</span>
                            </td>
                            <td style="width: 34%;">
                                <div style="font-weight: bold; font-size: 8.5pt; color: #0f172a; margin-bottom: 4px;">DATE / SCHEDULE</div>
                                선적일자: <b>{ship_date}</b><br>
                                <span style="font-size: 8pt; color: #64748b;">Job No: {job_num_str}</span>
                            </td>
                        </tr>
                    </table>

                    <table class="top-table">
                        <tr>
                            <td style="width: 60%;">
                                <div class="section-header">DESCRIPTION OF CONTENTS (품명 및 화물 내용)</div>
                                <div style="font-size: 11pt; font-weight: bold; color: #1e3a8a; padding: 6px 0;">{item_name}</div>
                                <div style="font-size: 8.5pt; color: #475569;">
                                    • 총 박스 수: <b>{box_cnt}</b><br>
                                    • 부피 규격: {vol_spec}<br>
                                    • CBM 합계: {cbm_val}
                                </div>
                            </td>
                            <td style="width: 40%;">
                                <div class="section-header">WEIGHT & MEASUREMENT</div>
                                <table style="width: 100%; border-collapse: collapse; margin-top: 4px;">
                                    <tr>
                                        <td style="border: 1px solid #cbd5e1; padding: 4px; font-size: 8pt;">청구 중량 (Chargeable Wt)</td>
                                        <td style="border: 1px solid #cbd5e1; padding: 4px; text-align: right; font-weight: bold; color: #dc2626;">{sales_cw} KG</td>
                                    </tr>
                                    <tr>
                                        <td style="border: 1px solid #cbd5e1; padding: 4px; font-size: 8pt;">총 박스 (PIECE)</td>
                                        <td style="border: 1px solid #cbd5e1; padding: 4px; text-align: right; font-weight: bold;">{box_cnt}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>

                    <div style="font-size: 7.5pt; color: #64748b; border: 1px solid #cbd5e1; padding: 8px; border-radius: 4px; background-color: #f8fafc; margin-top: 6px;">
                        <b>TERMS & CONDITIONS:</b> In consideration of the transportation charges for the movement of this shipment, it is agreed that the liability of BUMWOON OCEAN & AIR CO., LTD. shall be limited in any event to the sum of $100.00 unless insurance cover is arranged in writing in advance. SHIPPERS COPY.
                    </div>
                </div>
            </body>
            </html>
            """
      components.html(awb_html, height=750, scrolling=True)
  else:
    st.info("출력할 B/L 내역이 없습니다.")


# ==========================================
# [4] 거래처 인보이스 발행 메뉴
# ==========================================
elif selected_menu == "📑 거래처 인보이스 발행":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>📑"
      " 거래처 인보이스 (청구서) 발행</h3>",
      unsafe_allow_html=True,
  )

  if st.session_state.bl_data_list:
    inv_bl_list = [
        str(item.get("B/L 번호", "")) for item in st.session_state.bl_data_list
    ]
    selected_inv_bl = st.selectbox(
        "인보이스를 발행할 B/L 번호 선택", options=inv_bl_list
    )
    target_inv_data = next(
        (
            item
            for item in st.session_state.bl_data_list
            if str(item.get("B/L 번호")) == selected_inv_bl
        ),
        None,
    )

    if target_inv_data:
      inv_client = str(target_inv_data.get("화주명(매출)", ""))
      inv_info = st.session_state.client_infos.get(inv_client, {})
      inv_addr = inv_info.get("주소", "경기도 김포시 풍무동 326-5번지 2층")
      inv_bno = inv_info.get("사업자등록번호", "-")
      inv_mgr = inv_info.get("담당자", "-")

      inv_amount = int(target_inv_data.get("매출액(원)", 0))
      vat_amount = int(inv_amount * 0.1)
      total_with_vat = inv_amount + vat_amount

      logo_embed_inv = f"<img src='data:image/png;base64,{LOGO_BASE64}' style='height: 40px; vertical-align: middle; margin-right: 10px;'>"

      invoice_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @media print {{
                        body {{ -webkit-print-color-adjust: exact; }}
                        .no-print {{ display: none !important; }}
                        @page {{ size: A4 portrait; margin: 15mm; }}
                    }}
                    body {{
                        font-family: 'Pretendard', sans-serif;
                        color: #1e293b;
                        font-size: 10pt;
                        line-height: 1.4;
                        margin: 0;
                        padding: 10px;
                        background-color: #ffffff;
                    }}
                    .inv-box {{
                        max-width: 760px;
                        margin: 0 auto;
                        border: 2px solid #0f172a;
                        padding: 25px;
                        border-radius: 8px;
                        background-color: #ffffff;
                    }}
                    .i-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
                    .i-table td {{ border: 1px solid #64748b; padding: 8px 10px; vertical-align: middle; }}
                    .th-bg {{ background-color: #0f172a; color: white; font-weight: bold; text-align: center; }}
                    .p-btn {{
                        display: block;
                        width: 100%;
                        background-color: #2563eb;
                        color: white;
                        text-align: center;
                        padding: 12px;
                        font-size: 11pt;
                        font-weight: bold;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="inv-box">
                    <button class="p-btn no-print" onclick="window.print()">🖨 인보이스(청구서) 인쇄 및 PDF 저장하기</button>

                    <table style="width: 100%; border-bottom: 3px solid #0f172a; padding-bottom: 12px; margin-bottom: 15px;">
                        <tr>
                            <td style="width: 60%; border: none;">
                                <div style="display: flex; align-items: center;">
                                    {logo_embed_inv}
                                    <div>
                                        <div style="font-size: 16pt; font-weight: 900; color: #1e3a8a;">주식회사 범운해운항공</div>
                                        <div style="font-size: 8pt; color: #475569; font-weight: bold;">BUMWOON OCEAN & AIR CO., LTD.</div>
                                    </div>
                                </div>
                            </td>
                            <td style="width: 40%; text-align: right; border: none;">
                                <div style="font-size: 18pt; font-weight: 900; color: #0f172a; letter-spacing: 2px;">청 구 서 (INVOICE)</div>
                                <div style="font-size: 8.5pt; color: #64748b; margin-top: 4px;">B/L No: {selected_inv_bl}</div>
                            </td>
                        </tr>
                    </table>

                    <table class="i-table">
                        <tr>
                            <td style="width: 15%; background-color: #f1f5f9; font-weight: bold;">청구처</td>
                            <td style="width: 35%;"><b>{inv_client}</b> 귀하 (담당: {inv_mgr})</td>
                            <td style="width: 15%; background-color: #f1f5f9; font-weight: bold;">발행일자</td>
                            <td style="width: 35%;">{str(date.today())}</td>
                        </tr>
                        <tr>
                            <td style="background-color: #f1f5f9; font-weight: bold;">사업자번호</td>
                            <td>{inv_bno}</td>
                            <td style="background-color: #f1f5f9; font-weight: bold;">Job 번호</td>
                            <td>{target_inv_data.get('Job 번호', '-')}</td>
                        </tr>
                        <tr>
                            <td style="background-color: #f1f5f9; font-weight: bold;">주 소</td>
                            <td colspan="3">{inv_addr}</td>
                        </tr>
                    </table>

                    <div style="font-size: 10.5pt; font-weight: bold; color: #1e3a8a; margin: 15px 0 8px 0;">■ 운송비용 청구 내역</div>
                    <table class="i-table">
                        <tr class="th-bg">
                            <td>품명 및 규격</td>
                            <td>수량</td>
                            <td>공급가액 (KRW)</td>
                            <td>부가가치세 (VAT)</td>
                            <td>합계 금액</td>
                        </tr>
                        <tr>
                            <td>{target_inv_data.get('품목', '화물 운송 용역')} ({target_inv_data.get('국가', '미국')})</td>
                            <td style="text-align: center;">{target_inv_data.get('박스수', '1 박스')}</td>
                            <td style="text-align: right;">￦ {inv_amount:,} 원</td>
                            <td style="text-align: right;">￦ {vat_amount:,} 원</td>
                            <td style="text-align: right; font-weight: bold; color: #dc2626; font-size: 11pt;">￦ {total_with_vat:,} 원</td>
                        </tr>
                    </table>

                    <div style="border: 1px solid #cbd5e1; padding: 12px; border-radius: 6px; background-color: #f8fafc; margin-top: 20px;">
                        <b>입금 계좌 안내:</b> 국민은행 123-456-789012 (예금주: 주식회사 범운해운항공)<br>
                        • 위 금액을 지정된 계좌로 입금하여 주시기 바랍니다.
                    </div>

                    <table style="width: 100%; border: none; margin-top: 30px;">
                        <tr>
                            <td style="border: none; text-align: center; font-size: 11pt; font-weight: bold; color: #0f172a;">
                                (주)범운해운항공 대표이사 이상복 [직인생략]
                            </td>
                        </tr>
                    </table>
                </div>
            </body>
            </html>
            """
      components.html(invoice_html, height=750, scrolling=True)
  else:
    st.info("발행할 B/L 내역이 없습니다. 먼저 B/L을 등록해주세요.")


# ==========================================
# [5] 화물 견적서 발행 메뉴
# ==========================================
elif selected_menu == "📄 화물 견적서 발행":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>📄"
      " 거래처 화물 견적서 발행 시스템</h3>",
      unsafe_allow_html=True,
  )

  q_col1, q_col2 = st.columns(2)
  with q_col1:
    q_client = st.selectbox(
        "견적 대상 거래처",
        options=(
            st.session_state.client_list
            if st.session_state.client_list
            else ["기본거래처"]
        ),
        key="quotation_client_select",
    )
    q_country = st.selectbox(
        "도착 국가", options=COUNTRY_LIST, key="quotation_country_select"
    )
    q_transport = st.selectbox(
        "운송 형태",
        options=["항공(Air)", "해상(LCL)"],
        key="quotation_transport_select",
    )
    q_item = st.text_input(
        "견적 품목명", value="일반공산품 및 의약외품", key="quotation_item_input"
    )

  with q_col2:
    q_weight = st.number_input(
        "적용 청구중량 (kg)",
        value=10.0,
        min_value=0.1,
        step=1.0,
        key="quotation_weight_input",
    )
    q_cbm = st.number_input(
        "적용 CBM",
        value=0.1,
        min_value=0.0,
        step=0.01,
        key="quotation_cbm_input",
    )
    q_valid_date = st.date_input(
        "견적 유효일자", value=date.today(), key="quotation_date_input"
    )

  calculated_quote_price = calculate_auto_price(
      q_client, q_weight, q_transport
  )
  q_price = st.number_input(
      "견적 총 금액 (원) [요율표 자동 계산]",
      value=int(calculated_quote_price),
      step=1000,
      format="%d",
      key="quotation_price_input",
  )

  q_remark = st.text_area(
      "견적 조건 및 특이사항",
      value="1. 본 견적의 유효기간은 발행일로부터 30일입니다.\n2. 관세 및 부가세는 별도입니다.",
      key="quotation_remark_input",
  )

  client_info_dict = st.session_state.client_infos.get(q_client, {})
  c_addr = client_info_dict.get("주소", "상세 주소 미등록")
  c_bno = client_info_dict.get("사업자등록번호", "-")
  c_mgr = client_info_dict.get("담당자", "-")

  logo_embed_q = f"<img src='data:image/png;base64,{LOGO_BASE64}' style='height: 40px; vertical-align: middle; margin-right: 10px;'>"

  quotation_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @media print {{
                body {{ -webkit-print-color-adjust: exact; }}
                .no-print {{ display: none !important; }}
                @page {{ size: A4 portrait; margin: 15mm; }}
            }}
            body {{
                font-family: 'Pretendard', sans-serif;
                color: #1e293b;
                font-size: 10pt;
                line-height: 1.4;
                margin: 0;
                padding: 10px;
                background-color: #ffffff;
            }}
            .quote-box {{
                max-width: 760px;
                margin: 0 auto;
                border: 2px solid #0f172a;
                padding: 25px;
                border-radius: 8px;
                background-color: #ffffff;
            }}
            .q-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
            .q-table td {{ border: 1px solid #64748b; padding: 8px 10px; vertical-align: middle; }}
            .th-bg {{ background-color: #0f172a; color: white; font-weight: bold; text-align: center; }}
            .p-btn {{
                display: block;
                width: 100%;
                background-color: #2563eb;
                color: white;
                text-align: center;
                padding: 12px;
                font-size: 11pt;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="quote-box">
            <button class="p-btn no-print" onclick="window.print()">🖨 화물 견적서 인쇄 및 PDF 저장하기</button>

            <table style="width: 100%; border-bottom: 3px solid #0f172a; padding-bottom: 12px; margin-bottom: 15px;">
                <tr>
                    <td style="width: 60%; border: none;">
                        <div style="display: flex; align-items: center;">
                            {logo_embed_q}
                            <div>
                                <div style="font-size: 16pt; font-weight: 900; color: #1e3a8a;">주식회사 범운해운항공</div>
                                <div style="font-size: 8pt; color: #475569; font-weight: bold;">BUMWOON OCEAN & AIR CO., LTD.</div>
                            </div>
                        </div>
                    </td>
                    <td style="width: 40%; text-align: right; border: none;">
                        <div style="font-size: 18pt; font-weight: 900; color: #0f172a; letter-spacing: 2px;">화 물 견 적 서</div>
                        <div style="font-size: 8.5pt; color: #64748b; margin-top: 4px;">QUOTATION SHEET</div>
                    </td>
                </tr>
            </table>

            <table class="q-table">
                <tr>
                    <td style="width: 15%; background-color: #f1f5f9; font-weight: bold;">수 신</td>
                    <td style="width: 35%;"><b>{q_client}</b> 귀하 (담당: {c_mgr})</td>
                    <td style="width: 15%; background-color: #f1f5f9; font-weight: bold;">발행일자</td>
                    <td style="width: 35%;">{str(date.today())}</td>
                </tr>
                <tr>
                    <td style="background-color: #f1f5f9; font-weight: bold;">사업자번호</td>
                    <td>{c_bno}</td>
                    <td style="background-color: #f1f5f9; font-weight: bold;">유효기한</td>
                    <td>{str(q_valid_date)} 까지</td>
                </tr>
                <tr>
                    <td style="background-color: #f1f5f9; font-weight: bold;">주 소</td>
                    <td colspan="3">{c_addr}</td>
                </tr>
            </table>

            <div style="font-size: 10.5pt; font-weight: bold; color: #1e3a8a; margin: 15px 0 8px 0;">■ 운송 조건 및 요금 내역</div>
            <table class="q-table">
                <tr class="th-bg">
                    <td>도착국가</td>
                    <td>운송형태</td>
                    <td>품명</td>
                    <td>청구중량 / CBM</td>
                    <td>합계 금액 (KRW)</td>
                </tr>
                <tr>
                    <td style="text-align: center;">{q_country}</td>
                    <td style="text-align: center;">{q_transport}</td>
                    <td style="text-align: center;">{q_item}</td>
                    <td style="text-align: center;">{q_weight} KG / {q_cbm} CBM</td>
                    <td style="text-align: right; font-weight: bold; color: #dc2626; font-size: 11pt;">￦ {int(q_price):,} 원</td>
                </tr>
            </table>

            <div style="font-size: 10pt; font-weight: bold; color: #0f172a; margin: 15px 0 5px 0;">■ 특이사항 및 안내</div>
            <div style="border: 1px solid #cbd5e1; padding: 10px; border-radius: 4px; background-color: #f8fafc; font-size: 9pt; white-space: pre-line; margin-bottom: 25px;">
                {q_remark}
            </div>

            <table style="width: 100%; border: none; margin-top: 30px;">
                <tr>
                    <td style="border: none; text-align: center; font-size: 11pt; font-weight: bold; color: #0f172a;">
                        (주)범운해운항공 대표이사 이상복 [직인생략]
                    </td>
                </tr>
            </table>
        </div>
    </body>
    </html>
    """
  st.markdown("---")
  components.html(quotation_html, height=750, scrolling=True)


# ==========================================
# [6] 거래처 미팅 노트 메뉴
# ==========================================
elif selected_menu == "🤝 거래처 미팅 노트":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>🤝"
      " 거래처 미팅 및 상담 노트</h3>",
      unsafe_allow_html=True,
  )

  with st.form("meeting_form"):
    m_client = st.selectbox(
        "대상 거래처",
        options=(
            st.session_state.client_list
            if st.session_state.client_list
            else ["기본거래처"]
        ),
    )
    m_mgr = st.text_input("담당자명", value="")
    m_title = st.text_input("상담 제목", value="")
    m_content = st.text_area("상담 상세 내용", value="")
    m_action = st.text_area("향후 조치 및 피드백", value="")
    if st.form_submit_button("📝 미팅 노트 저장하기", type="primary"):
      st.session_state.meeting_data_list.append({
          "날짜": str(date.today()),
          "거래처": m_client,
          "담당자": m_mgr,
          "제목": m_title,
          "상세내용": m_content,
          "향후조치": m_action,
      })
      pd.DataFrame(st.session_state.meeting_data_list).to_csv(
          MEETING_FILE, index=False, encoding="utf-8-sig"
      )
      st.success("미팅 노트가 저장되었습니다!")

  if st.session_state.meeting_data_list:
    st.markdown("---")
    st.markdown("#### **📋 저장된 미팅 노트 목록**")
    st.dataframe(
        pd.DataFrame(st.session_state.meeting_data_list),
        use_container_width=True,
        hide_index=True,
    )


# ==========================================
# [7] 금일발송 매니페스트 메뉴
# ==========================================
elif selected_menu == "📋 금일발송 매니페스트":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>📋"
      " 금일발송 매니페스트 (화물 발송 리스트)</h3>",
      unsafe_allow_html=True,
  )

  target_date_str = str(
      st.date_input("조회할 발송 날짜 선택", value=date.today())
  )
  if st.session_state.bl_data_list:
    df_bl_all = pd.DataFrame(st.session_state.bl_data_list)
    df_today = df_bl_all[df_bl_all["날짜"] == target_date_str]

    if not df_today.empty:
      st.success(
          f"총 {len(df_today)}건의 화물이 {target_date_str}에 접수/발송"
          " 예정입니다."
      )
      st.dataframe(df_today, use_container_width=True, hide_index=True)
    else:
      st.info(f"선택하신 날짜({target_date_str})에 등록된 발송 건이 없습니다.")
  else:
    st.info("등록된 B/L 데이터가 없습니다.")


# ==========================================
# [8] 거래처 등록 요금 상세 관리 메뉴
# ==========================================
elif selected_menu == "🏢 거래처 등록 요금 상세 관리":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>🏢"
      " 거래처별 기본 요율 및 단가 상세 관리</h3>",
      unsafe_allow_html=True,
  )

  selected_rate_client = st.selectbox(
      "요율을 관리할 거래처 선택", options=st.session_state.client_list
  )
  if selected_rate_client:
    client_info = st.session_state.client_infos.get(selected_rate_client, {})
    with st.form("client_info_form"):
      st.markdown(f"#### **[{selected_rate_client}] 사업자 정보 관리**")
      ci_bno = st.text_input(
          "사업자등록번호", value=client_info.get("사업자등록번호", "")
      )
      ci_email = st.text_input("이메일", value=client_info.get("이메일", ""))
      ci_mgr = st.text_input("담당자명", value=client_info.get("담당자", ""))
      ci_tel = st.text_input("전화번호", value=client_info.get("전화번호", ""))
      ci_addr = st.text_input("주소", value=client_info.get("주소", ""))

      if st.form_submit_button(
          "💾 거래처 정보 저장", type="primary", use_container_width=True
      ):
        st.session_state.client_infos[selected_rate_client] = {
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
        st.success("거래처 정보가 업데이트되었습니다!")

    st.markdown("---")
    st.markdown(f"#### **[{selected_rate_client}] 운송 요율표 설정**")
    current_rates = st.session_state.client_rates.get(
        selected_rate_client, {"미국": {"항공(Air)": {"보톡스 필러": {}}}}
    )

    rate_rows = []
    for country, trans_dict in current_rates.items():
      if isinstance(trans_dict, dict):
        for transport, item_dict in trans_dict.items():
          if isinstance(item_dict, dict):
            for item_name, val in item_dict.items():
              rate_rows.append({
                  "국가": country,
                  "운송형태": transport,
                  "품명": item_name,
                  "기본중량(kg)": val.get("기본중량", 1.0),
                  "기본요금(원)": val.get("기본요금", 38000),
                  "추가단가(원/kg)": val.get("추가단가", 25000),
                  "1CBM당단가(원)": val.get("1CBM당단가", 3700000),
              })

    df_rate_editor = st.data_editor(
        pd.DataFrame(rate_rows),
        num_rows="dynamic",
        use_container_width=True,
        key="rate_editor_tbl",
    )

    if st.button("💾 요율표 최종 저장", type="primary", use_container_width=True):
      new_rates_dict = {}
      for _, r in df_rate_editor.iterrows():
        c = str(r.get("국가", "미국"))
        t = str(r.get("운송형태", "항공(Air)"))
        i = str(r.get("품명", "일반공산품"))
        if c not in new_rates_dict:
          new_rates_dict[c] = {}
        if t not in new_rates_dict[c]:
          new_rates_dict[c][t] = {}
        new_rates_dict[c][t][i] = {
            "기본중량": float(r.get("기본중량(kg)", 1.0)),
            "기본요금": int(r.get("기본요금(원)", 38000)),
            "추가단가": int(r.get("추가단가(원/kg)", 25000)),
            "1CBM당단가": int(r.get("1CBM당단가(원)", 3700000)),
        }
      st.session_state.client_rates[selected_rate_client] = new_rates_dict
      save_client_data(
          st.session_state.client_list,
          st.session_state.client_rates,
          st.session_state.client_infos,
      )
      st.success("요율표가 성공적으로 저장되었습니다!")


# ==========================================
# [9] 거래처 미수금관리 메뉴
# ==========================================
elif selected_menu == "💵 거래처 미수금관리":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>💵"
      " 거래처별 미수금 현황 및 수금 관리</h3>",
      unsafe_allow_html=True,
  )

  if st.session_state.bl_data_list:
    df_all_bl = pd.DataFrame(st.session_state.bl_data_list)
    if "수금상태" not in df_all_bl.columns:
      df_all_bl["수금상태"] = "미수"

    summary_data = []
    for client in st.session_state.client_list:
      c_df = df_all_bl[df_all_bl["화주명(매출)"] == client]
      total_sales = (
          c_df["매출액(원)"].sum() if not c_df.empty else 0
      )
      unpaid_df = c_df[c_df["수금상태"] != "수금완료"]
      unpaid_amount = (
          unpaid_df["매출액(원)"].sum() if not unpaid_df.empty else 0
      )
      summary_data.append({
          "거래처명": client,
          "총 청구금액": total_sales,
          "미수금 잔액": unpaid_amount,
      })

    st.dataframe(
        pd.DataFrame(summary_data), use_container_width=True, hide_index=True
    )

    st.markdown("---")
    st.markdown("#### **📦 미수 상태인 개별 B/L 내역**")
    unpaid_bl_df = df_all_bl[df_all_bl["수금상태"] != "수금완료"]
    if not unpaid_bl_df.empty:
      st.dataframe(unpaid_bl_df, use_container_width=True, hide_index=True)
    else:
      st.success("🎉 현재 미수금 잔액이 모두 해소되었습니다!")
  else:
    st.info("등록된 B/L 데이터가 없습니다.")


# ==========================================
# [10] 일계표 및 입출금 장부 메뉴
# ==========================================
elif selected_menu == "💳 일계표 및 입출금 장부":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>💳"
      " 일계표 및 입출금 장부 관리</h3>",
      unsafe_allow_html=True,
  )

  tab_e1, tab_e2 = st.tabs(["지출 장부 등록", "현금/통장 입출금 내역"])
  with tab_e1:
    with st.form("expense_form"):
      e_date = st.date_input("지출 일자", value=date.today())
      e_cat = st.selectbox("지출 항목", options=EXPENSE_CATEGORIES)
      e_desc = st.text_input("적요 및 상세 내용", value="")
      e_amount = st.number_input("지출 금액 (원)", value=10000, step=1000)
      if st.form_submit_button("💾 지출 내역 저장", type="primary"):
        st.session_state.expense_data_list.append({
            "날짜": str(e_date),
            "구분": "지출 (-)",
            "항목": e_cat,
            "적요": e_desc,
            "금액(원)": int(e_amount),
        })
        pd.DataFrame(st.session_state.expense_data_list).to_csv(
            EXPENSE_FILE, index=False, encoding="utf-8-sig"
        )
        st.success("지출 내역이 장부에 기록되었습니다!")

  with tab_e2:
    if st.session_state.expense_data_list:
      st.dataframe(
          pd.DataFrame(st.session_state.expense_data_list),
          use_container_width=True,
          hide_index=True,
      )
    else:
      st.info("등록된 입출금 내역이 없습니다.")


# ==========================================
# [11] 업무용 일지 메뉴
# ==========================================
elif selected_menu == "📝 업무용 일지":
  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>📝"
      " 사내 업무용 일지 및 인수인계</h3>",
      unsafe_allow_html=True,
  )

  with st.form("note_form"):
    n_date = st.date_input("일지 작성일", value=date.today())
    n_title = st.text_input("일지 제목", value="")
    n_content = st.text_area("업무 내용 및 특이사항", value="")
    if st.form_submit_button("📝 업무일지 등록", type="primary"):
      st.session_state.note_data_list.append({
          "날짜": str(n_date),
          "작성자": st.session_state.user_db[
              st.session_state.logged_in_user
          ]["name"],
          "제목": n_title,
          "내용": n_content,
      })
      pd.DataFrame(st.session_state.note_data_list).to_csv(
          NOTE_FILE, index=False, encoding="utf-8-sig"
      )
      st.success("업무일지가 등록되었습니다!")

  if st.session_state.note_data_list:
    st.markdown("---")
    st.dataframe(
        pd.DataFrame(st.session_state.note_data_list),
        use_container_width=True,
        hide_index=True,
    )


# ==========================================
# [12] 직원 계정 관리 메뉴 (관리자 전용)
# ==========================================
elif selected_menu == "🔑 직원 계정 관리 (대표님 전용)":
  if st.session_state.user_role != "관리자(대표)":
    st.error("접근 권한이 없습니다. 관리자(대표) 계정으로 로그인해주세요.")
    st.stop()

  st.markdown(
      "<h3 style='color: #0f172a; font-weight: 700; margin-bottom: 10px;'>🔑"
      " 사내 직원 계정 추가 및 관리</h3>",
      unsafe_allow_html=True,
  )

  with st.form("add_user_form"):
    new_uid = st.text_input("신규 직원 아이디 (ID)")
    new_upw = st.text_input("초기 비밀번호 (Password)", type="password")
    new_uname = st.text_input("직원 성명")
    new_role = st.selectbox("권한 설정", options=["직원", "관리자(대표)"])
    if st.form_submit_button("➕ 신규 계정 생성하기", type="primary"):
      if new_uid.strip() and new_upw.strip() and new_uname.strip():
        if new_uid in st.session_state.user_db:
          st.warning("이미 존재하는 아이디입니다.")
        else:
          st.session_state.user_db[new_uid] = {
              "pw": new_upw,
              "role": new_role,
              "name": new_uname,
          }
          save_user_db(st.session_state.user_db)
          st.success(
              f"🎉 [{new_uname}]님의 직원 계정이 성공적으로 생성되었습니다!"
          )
      else:
        st.warning("모든 필드를 올바르게 입력해주세요.")

  st.markdown("---")
  st.markdown("#### **👥 등록된 전체 계정 목록**")
  user_rows = []
  for uid, info in st.session_state.user_db.items():
    user_rows.append({
        "아이디": uid,
        "성명": info.get("name", ""),
        "권한": info.get("role", "직원"),
    })
  st.dataframe(
      pd.DataFrame(user_rows), use_container_width=True, hide_index=True
  )
