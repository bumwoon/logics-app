import streamlit as st
import pandas as pd
from datetime import date
import math
import os
import base64
from io import BytesIO

# ============================================================
# (주)범운해운항공 종합 관리 프로그램
# 최종본 - A4 PDF 직접 저장 / 마진 정산서 + 매출 Invoice 분리
# ============================================================

st.set_page_config(
    page_title="(주)범운해운항공 종합 관리 프로그램",
    page_icon="🚢",
    layout="wide"
)

# ------------------------------------------------------------
# 기본 경로 / 파일
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "bl_history_data.csv")
CLIENT_FILE = os.path.join(BASE_DIR, "client_data.csv")
ACCOUNT_FILE = os.path.join(BASE_DIR, "account_ledger_data.csv")
EXPENSE_FILE = os.path.join(BASE_DIR, "expense_data.csv")

COUNTRY_LIST = [
    "미국", "중국", "호주", "태국", "인도",
    "멕시코", "홍콩", "베트남", "기타 국가"
]

EXPENSE_CATEGORIES = [
    "주유비 (차량유지비)",
    "식대 (복리후생비)",
    "접대비",
    "소모품비",
    "통신비",
    "공과금",
    "기타 잡비"
]


# ------------------------------------------------------------
# 회사 로고 자동 감지
# ------------------------------------------------------------
LOGO_FILE = None

for filename in os.listdir(BASE_DIR):
    lower_name = filename.lower()
    if lower_name.startswith("lo") and lower_name.endswith(
        (".png", ".jpg", ".jpeg", ".webp")
    ):
        LOGO_FILE = os.path.join(BASE_DIR, filename)
        break


# ------------------------------------------------------------
# 안전한 데이터 변환
# ------------------------------------------------------------
def safe_text(value, default=""):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    return str(value)


def safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        text = str(value).strip().replace(",", "")
        if text == "" or text.lower() in {"nan", "none", "null"}:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(round(safe_float(value, default)))
    except Exception:
        return default


def normalize_bl_record(record):
    record = dict(record)

    # 이전 버전 컬럼명 호환
    if not safe_text(record.get("화주명(매출)")).strip() and "화주명(매출처)" in record:
        record["화주명(매출)"] = record.get("화주명(매출처)")
    if not safe_text(record.get("예상마진(원)")).strip() and "예상Profit(원)" in record:
        record["예상마진(원)"] = record.get("예상Profit(원)")
    if not safe_text(record.get("예상Profit(원)")).strip() and "예상마진(원)" in record:
        record["예상Profit(원)"] = record.get("예상마진(원)")

    # 오래된 CSV에 일부 컬럼이 없더라도 화면이 중단되지 않게 기본값 보완
    defaults = {
        "구분": "",
        "날짜": "",
        "Job 번호": "",
        "B/L 번호": "",
        "국가": "",
        "화주명(매출)": "",
        "매입처": "",
        "운송형태": "",
        "품목": "",
        "매출실중량(kg)": 0,
        "매출청구중량(kg)": 0,
        "매출액(원)": 0,
        "매입실중량(kg)": 0,
        "매입청구중량(kg)": 0,
        "매입액(원)": 0,
        "예상마진(원)": 0,
        "비고": "",
    }
    for key, default in defaults.items():
        if key not in record:
            record[key] = default

    return record


# ------------------------------------------------------------
# 데이터 불러오기
# ------------------------------------------------------------
def load_bl_data():
    if not os.path.exists(DATA_FILE):
        return []

    for encoding in ("utf-8-sig", "cp949", "utf-8"):
        try:
            df = pd.read_csv(DATA_FILE, encoding=encoding)
            if "예상Profit(원)" in df.columns and "예상마진(원)" not in df.columns:
                df["예상마진(원)"] = df["예상Profit(원)"]
            return [normalize_bl_record(x) for x in df.to_dict("records")]
        except Exception:
            continue
    return []


def load_client_data():
    if os.path.exists(CLIENT_FILE):
        for encoding in ("utf-8-sig", "cp949", "utf-8"):
            try:
                df = pd.read_csv(CLIENT_FILE, encoding=encoding)
                if "거래처명" not in df.columns:
                    continue

                clients = [safe_text(x).strip() for x in df["거래처명"].dropna().unique().tolist() if safe_text(x).strip()]
                rates = {}
                client_infos = {}

                for client in clients:
                    rates[client] = {}
                    sub_df = df[df["거래처명"].astype(str) == client]
                    if sub_df.empty:
                        continue

                    first_row = sub_df.iloc[0]
                    client_infos[client] = {
                        "사업자등록번호": safe_text(first_row.get("사업자등록번호", "")),
                        "이메일": safe_text(first_row.get("이메일", "")),
                        "담당자": safe_text(first_row.get("담당자", ""))
                    }

                    for _, row in sub_df.iterrows():
                        country = safe_text(row.get("국가", "기타 국가")).strip() or "기타 국가"
                        item = safe_text(row.get("품명", "일반공산품")).strip() or "일반공산품"
                        rates[client].setdefault(country, {})
                        rates[client][country][item] = {
                            "기본중량": safe_float(row.get("기본중량", 1.0), 1.0),
                            "기본요금": safe_int(row.get("기본요금", 35000), 35000),
                            "추가단가": safe_int(row.get("추가단가", 25000), 25000),
                            "1CBM당단가": safe_int(row.get("1CBM당단가", 0), 0),
                        }

                if clients:
                    return clients, rates, client_infos
            except Exception:
                continue

    default_clients = [
        "(주)홍길동상사",
        "ABC로지스틱스",
        "글로벌쉬핑",
        "글루오필메디앤코",
        "대한항공(KE)",
        "아시아나(OZ)",
        "캐세이퍼시픽(CX)",
        "카스항운",
        "글로우필"
    ]

    default_rates = {}
    default_infos = {
        c: {
            "사업자등록번호": "000-00-00000",
            "이메일": "example@bumwoon.com",
            "담당자": "담당자"
        }
        for c in default_clients
    }

    for client in default_clients:
        default_rates[client] = {}
        for country in COUNTRY_LIST:
            default_rates[client][country] = {
                "일반공산품": {
                    "기본중량": 1.0,
                    "기본요금": 35000 if client == "카스항운" else 30000,
                    "추가단가": 25000,
                    "1CBM당단가": 0
                },
                "화장품": {
                    "기본중량": 1.0,
                    "기본요금": 38000,
                    "추가단가": 28000,
                    "1CBM당단가": 0
                }
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
            return pd.read_csv(EXPENSE_FILE).to_dict("records")
        except Exception:
            return []
    return []


# ------------------------------------------------------------
# 데이터 저장
# ------------------------------------------------------------
def save_bl_data(data_list):
    if data_list:
        pd.DataFrame(data_list).to_csv(
            DATA_FILE,
            index=False,
            encoding="utf-8-sig"
        )
    elif os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)


def save_client_data(client_list, client_rates, client_infos):
    rows = []

    for client in client_list:
        info = client_infos.get(
            client,
            {
                "사업자등록번호": "",
                "이메일": "",
                "담당자": ""
            }
        )

        country_dict = client_rates.get(client, {})

        for country, item_dict in country_dict.items():
            if not isinstance(item_dict, dict):
                continue

            for item_name, r_val in item_dict.items():
                rows.append({
                    "거래처명": client,
                    "사업자등록번호": info.get(
                        "사업자등록번호", ""
                    ),
                    "이메일": info.get("이메일", ""),
                    "담당자": info.get("담당자", ""),
                    "국가": country,
                    "품명": item_name,
                    "기본중량": r_val.get("기본중량", 1.0),
                    "기본요금": r_val.get("기본요금", 35000),
                    "추가단가": r_val.get("추가단가", 25000)
                })

    pd.DataFrame(rows).to_csv(
        CLIENT_FILE,
        index=False,
        encoding="utf-8-sig"
    )


def save_account_data(data_list):
    if data_list:
        pd.DataFrame(data_list).to_csv(
            ACCOUNT_FILE,
            index=False,
            encoding="utf-8-sig"
        )
    elif os.path.exists(ACCOUNT_FILE):
        os.remove(ACCOUNT_FILE)


def save_expense_data(data_list):
    if data_list:
        pd.DataFrame(data_list).to_csv(
            EXPENSE_FILE,
            index=False,
            encoding="utf-8-sig"
        )
    elif os.path.exists(EXPENSE_FILE):
        os.remove(EXPENSE_FILE)


# ------------------------------------------------------------
# 계산
# ------------------------------------------------------------
def calculate_tier_price(
    chargeable_weight,
    base_weight,
    base_price,
    add_price
):
    weight = max(0.0, safe_float(chargeable_weight, 0.0))
    base_w = max(0.0, safe_float(base_weight, 1.0))
    base_p = safe_int(base_price, 35000)
    add_p = safe_int(add_price, 25000)

    if weight <= 0:
        return 0
    if weight <= base_w:
        return base_p

    excess_weight = math.ceil(weight - base_w)
    return int(base_p + excess_weight * add_p)


# ------------------------------------------------------------
# PDF 생성
# ReportLab이 설치되어 있어야 합니다.
# Streamlit Cloud / 일반 Python 환경에서:
# pip install reportlab
# ------------------------------------------------------------
def get_pdf_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    font_name = "HYSMyeongJo-Medium"

    try:
        pdfmetrics.getFont(font_name)
    except Exception:
        pdfmetrics.registerFont(
            UnicodeCIDFont(font_name)
        )

    return font_name


def make_margin_pdf(item):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image
    )

    font = get_pdf_fonts()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"JOB 마진 정산서 - {item.get('Job 번호', '')}"
    )

    normal = ParagraphStyle(
        "NormalKR",
        fontName=font,
        fontSize=9.5,
        leading=14
    )

    small = ParagraphStyle(
        "SmallKR",
        fontName=font,
        fontSize=8.5,
        leading=12
    )

    title_style = ParagraphStyle(
        "TitleKR",
        fontName=font,
        fontSize=17,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "SubtitleKR",
        fontName=font,
        fontSize=11,
        leading=15,
        alignment=TA_CENTER
    )

    right_style = ParagraphStyle(
        "RightKR",
        fontName=font,
        fontSize=12,
        leading=17,
        alignment=TA_RIGHT
    )

    story = []

    # 로고
    if LOGO_FILE and os.path.exists(LOGO_FILE):
        try:
            logo = Image(LOGO_FILE)
            logo.drawHeight = 14 * mm
            logo.drawWidth = 42 * mm
            story.append(
                Table(
                    [[logo]],
                    colWidths=[180 * mm]
                )
            )
            story.append(Spacer(1, 3 * mm))
        except Exception:
            pass

    story.append(
        Paragraph(
            "(주)범운해운항공 / BUMWOON OCEAN & AIR., LTD.",
            title_style
        )
    )

    story.append(
        Paragraph(
            "[ JOB 마진 정산서 ]",
            subtitle_style
        )
    )

    story.append(Spacer(1, 5 * mm))

    info_data = [
        [
            Paragraph(
                f"<b>Job 번호:</b> {item.get('Job 번호', '')}",
                normal
            ),
            Paragraph(
                f"<b>등록 일자:</b> {item.get('날짜', '')}",
                normal
            )
        ],
        [
            Paragraph(
                f"<b>B/L 번호:</b> {item.get('B/L 번호', '')}",
                normal
            ),
            Paragraph(
                f"<b>운송 형태:</b> {item.get('운송형태', '')} "
                f"({item.get('구분', '')})",
                normal
            )
        ],
        [
            Paragraph(
                f"<b>화주명 (매출처):</b> "
                f"{item.get('화주명(매출)', '')}",
                normal
            ),
            Paragraph(
                f"<b>매입처:</b> {item.get('매입처', '')}",
                normal
            )
        ],
        [
            Paragraph(
                f"<b>목적 국가:</b> {item.get('국가', '')}",
                normal
            ),
            Paragraph(
                f"<b>품목명:</b> {item.get('품목', '')}",
                normal
            )
        ]
    ]

    info_table = Table(
        info_data,
        colWidths=[90 * mm, 90 * mm]
    )

    info_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ])
    )

    story.append(info_table)
    story.append(Spacer(1, 5 * mm))

    sales_amount = safe_int(item.get("매출액(원)", 0), 0)
    purchase_amount = safe_int(item.get("매입액(원)", 0), 0)
    margin_amount = safe_int(item.get("예상마진(원)", 0), 0)

    amount_data = [
        [
            Paragraph("<b>구분</b>", normal),
            Paragraph("<b>실중량 (kg)</b>", normal),
            Paragraph("<b>청구중량 (kg)</b>", normal),
            Paragraph("<b>금액 (KRW)</b>", normal)
        ],
        [
            Paragraph("<b>매출 (Sales)</b>", normal),
            Paragraph(
                str(item.get("매출실중량(kg)", 0)),
                normal
            ),
            Paragraph(
                str(item.get("매출청구중량(kg)", 0)),
                normal
            ),
            Paragraph(
                f"{sales_amount:,} 원",
                normal
            )
        ],
        [
            Paragraph("<b>매입 (Purchase)</b>", normal),
            Paragraph(
                str(item.get("매입실중량(kg)", 0)),
                normal
            ),
            Paragraph(
                str(item.get("매입청구중량(kg)", 0)),
                normal
            ),
            Paragraph(
                f"{purchase_amount:,} 원",
                normal
            )
        ]
    ]

    amount_table = Table(
        amount_data,
        colWidths=[45 * mm, 40 * mm, 45 * mm, 50 * mm],
        repeatRows=1
    )

    amount_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.7, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(amount_table)
    story.append(Spacer(1, 7 * mm))

    story.append(
        Paragraph(
            f"<b>예상 수익 마진: {margin_amount:,} 원</b>",
            right_style
        )
    )

    story.append(Spacer(1, 8 * mm))

    remarks = str(
        item.get("비고", "") or "특이사항 없음"
    ).replace("\n", "<br/>")

    story.append(
        Paragraph(
            f"<b>비고:</b> {remarks}",
            normal
        )
    )

    story.append(Spacer(1, 25 * mm))

    story.append(
        Paragraph(
            "주식회사 범운해운항공 (직인생략)",
            ParagraphStyle(
                "SignKR",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_CENTER
            )
        )
    )

    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()


def make_invoice_pdf(item, client_info, apply_vat, invoice_status):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image
    )

    font = get_pdf_fonts()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Invoice - {item.get('Job 번호', '')}"
    )

    normal = ParagraphStyle(
        "InvoiceNormalKR",
        fontName=font,
        fontSize=8.5,
        leading=12
    )

    small = ParagraphStyle(
        "InvoiceSmallKR",
        fontName=font,
        fontSize=7.5,
        leading=10
    )

    title_style = ParagraphStyle(
        "InvoiceTitleKR",
        fontName=font,
        fontSize=19,
        leading=24,
        alignment=TA_CENTER
    )

    center = ParagraphStyle(
        "InvoiceCenterKR",
        fontName=font,
        fontSize=8.5,
        leading=12,
        alignment=TA_CENTER
    )

    right = ParagraphStyle(
        "InvoiceRightKR",
        fontName=font,
        fontSize=9.5,
        leading=14,
        alignment=TA_RIGHT
    )

    total_style = ParagraphStyle(
        "InvoiceTotalKR",
        fontName=font,
        fontSize=12,
        leading=17,
        alignment=TA_RIGHT
    )

    story = []

    # 상단 로고 + 제목
    header_cells = []

    if LOGO_FILE and os.path.exists(LOGO_FILE):
        try:
            logo = Image(LOGO_FILE)
            logo.drawHeight = 14 * mm
            logo.drawWidth = 40 * mm
            header_cells.append(logo)
        except Exception:
            header_cells.append("")
    else:
        header_cells.append("")

    header_cells.append(
        Paragraph(
            "<b>INVOICE (청구서)</b><br/>"
            "<font size='9'>"
            "(주)범운해운항공 | BUMWOON OCEAN & AIR., LTD."
            "</font>",
            title_style
        )
    )

    header_table = Table(
        [header_cells],
        colWidths=[45 * mm, 135 * mm]
    )

    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    story.append(header_table)
    story.append(Spacer(1, 3 * mm))

    # 공급자 / 공급받는 자
    client_name = str(
        item.get("화주명(매출)", "")
    )

    supplier_text = (
        "<b>[ 공급자 (Supplier) ]</b><br/>"
        "<b>상호:</b> (주)범운해운항공 "
        "(BUMWOON OCEAN & AIR., LTD.)<br/>"
        "<b>대표이사:</b> 이상복<br/>"
        "<b>본사:</b> 경기도 김포시 풍무동 326-5번지 2동<br/>"
        "<b>1창고:</b> 경기도 김포시 승가로 110-30 가동<br/>"
        "<b>2창고:</b> 경기도 김포시 승가로 87-47<br/>"
        "<b>Tel:</b> 031-989-7071 "
        "&nbsp;&nbsp; <b>Fax:</b> 031-989-7072<br/>"
        "<b>E-mail:</b> bumwoon11@naver.com"
    )

    client_text = (
        "<b>[ 공급받는 자 (Client / Bill To) ]</b><br/>"
        f"<b>상호:</b> {client_name}<br/>"
        f"<b>사업자등록번호:</b> "
        f"{client_info.get('사업자등록번호', '-') or '-'}<br/>"
        f"<b>담당자:</b> "
        f"{client_info.get('담당자', '-') or '-'}<br/>"
        f"<b>이메일:</b> "
        f"{client_info.get('이메일', '-') or '-'}"
    )

    party_table = Table(
        [[
            Paragraph(supplier_text, normal),
            Paragraph(client_text, normal)
        ]],
        colWidths=[90 * mm, 90 * mm]
    )

    party_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cccccc")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f7f7f7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(party_table)
    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            f"<b>Job No. : {item.get('Job 번호', '')}</b>",
            normal
        )
    )

    story.append(Spacer(1, 3 * mm))

    supply_amount = safe_int(item.get("매출액(원)", 0), 0)

    vat_amount = (
        int(supply_amount * 0.1)
        if apply_vat else 0
    )

    grand_total = supply_amount + vat_amount

    invoice_data = [
        [
            Paragraph("<b>순서</b>", center),
            Paragraph("<b>날짜</b>", center),
            Paragraph("<b>B/L No.</b>", center),
            Paragraph("<b>목적지</b>", center),
            Paragraph("<b>청구중량</b>", center),
            Paragraph("<b>품명</b>", center),
            Paragraph("<b>공급가액</b>", center)
        ],
        [
            Paragraph("1", center),
            Paragraph(
                str(item.get("날짜", "")),
                center
            ),
            Paragraph(
                str(item.get("B/L 번호", "")),
                center
            ),
            Paragraph(
                str(item.get("국가", "")),
                center
            ),
            Paragraph(
                f"{item.get('매출청구중량(kg)', 0)} kg",
                center
            ),
            Paragraph(
                str(item.get("품목", "")),
                center
            ),
            Paragraph(
                f"<b>{supply_amount:,}</b>",
                center
            )
        ]
    ]

    invoice_table = Table(
        invoice_data,
        colWidths=[
            12 * mm,
            23 * mm,
            32 * mm,
            23 * mm,
            24 * mm,
            38 * mm,
            28 * mm
        ],
        repeatRows=1
    )

    invoice_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#888888")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeaf7")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ])
    )

    story.append(invoice_table)
    story.append(Spacer(1, 5 * mm))

    vat_text = (
        "(영세율 적용)"
        if not apply_vat
        else "(부가세 10% 적용)"
    )

    summary_data = [
        [
            "",
            Paragraph(
                f"공급가액: <b>{supply_amount:,} 원</b>",
                right
            )
        ],
        [
            "",
            Paragraph(
                f"부가세(VAT): <b>{vat_amount:,} 원</b> "
                f"{vat_text}",
                right
            )
        ],
        [
            "",
            Paragraph(
                f"<b>총 청구금액: {grand_total:,} 원</b>",
                total_style
            )
        ]
    ]

    summary_table = Table(
        summary_data,
        colWidths=[80 * mm, 100 * mm]
    )

    summary_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )

    story.append(summary_table)
    story.append(Spacer(1, 5 * mm))

    if "미발행" in invoice_status:
        account_text = (
            "<b>[ 입금 계좌 안내 - 계산서 미발행 건 ]</b><br/>"
            "카카오뱅크: 3333-12-9553477 "
            "(예금주: 이상복 / 범운해운항공)<br/>"
            "우리은행: 1005-704-932716 "
            "(예금주: 주식회사 범운해운항공)"
        )
    else:
        account_text = (
            "<b>[ 입금 계좌 안내 - 계산서 발행 완료 건 ]</b><br/>"
            "우리은행: 1005-704-932716 "
            "(예금주: 주식회사 범운해운항공)"
        )

    account_table = Table(
        [[Paragraph(account_text, normal)]],
        colWidths=[180 * mm]
    )

    account_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#e0c45c")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbe6")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )

    story.append(account_table)
    story.append(Spacer(1, 13 * mm))

    story.append(
        Paragraph(
            "주식회사 범운해운항공 대표이사 이상복",
            ParagraphStyle(
                "InvoiceSignKR",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_CENTER
            )
        )
    )

    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()


# ------------------------------------------------------------
# PDF 파일명
# ------------------------------------------------------------
def safe_filename(value):
    value = str(value or "").strip()

    if not value:
        value = "NO_JOB"

    for char in '\\/:*?"<>|':
        value = value.replace(char, "_")

    return value


# ------------------------------------------------------------
# 상단 제목 / 로고
# ------------------------------------------------------------
if LOGO_FILE and os.path.exists(LOGO_FILE):
    col_logo, col_title = st.columns([1, 4])

    with col_logo:
        st.image(LOGO_FILE, width=150)

    with col_title:
        st.markdown(
            """
            <div style="padding-top:5px;">
                <h1 style="color:#1f77b4;margin:0;font-size:28px;">
                    🚢 ✈️ (주)범운해운항공 종합 관리 프로그램
                </h1>
                <p style="margin:5px 0 0 0;color:#555;font-size:15px;">
                    Job별 마진 계산, 거래처 관리 및 영세율 인보이스
                    (A4 PDF 저장) 지원
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.markdown(
        """
        <div style="
            background-color:#f0f2f6;
            padding:20px;
            border-radius:10px;
            margin-bottom:20px;
        ">
            <h1 style="color:#1f77b4;margin:0;font-size:28px;">
                🚢 ✈️ (주)범운해운항공 종합 관리 프로그램
            </h1>
            <p style="margin:5px 0 0 0;color:#555;font-size:15px;">
                Job별 마진 계산, 거래처 관리 및 영세율 인보이스
                (A4 PDF 저장) 지원
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()


# ------------------------------------------------------------
# 세션 상태
# ------------------------------------------------------------
if (
    "client_list" not in st.session_state
    or not st.session_state.client_list
):
    c_list, c_rates, c_infos = load_client_data()

    st.session_state.client_list = c_list
    st.session_state.client_rates = c_rates
    st.session_state.client_infos = c_infos
else:
    if "client_rates" not in st.session_state:
        _, c_rates, _ = load_client_data()
        st.session_state.client_rates = c_rates

    if "client_infos" not in st.session_state:
        _, _, c_infos = load_client_data()
        st.session_state.client_infos = c_infos


if "bl_data_list" not in st.session_state:
    st.session_state.bl_data_list = load_bl_data()

if "account_data_list" not in st.session_state:
    st.session_state.account_data_list = load_account_data()

if "expense_data_list" not in st.session_state:
    st.session_state.expense_data_list = load_expense_data()

if "is_editing" not in st.session_state:
    st.session_state.is_editing = False

if "edit_client" not in st.session_state:
    st.session_state.edit_client = ""

if "edit_country" not in st.session_state:
    st.session_state.edit_country = ""

if "edit_item" not in st.session_state:
    st.session_state.edit_item = ""

if "shared_cbm" not in st.session_state:
    st.session_state.shared_cbm = 0.0

if "shared_gw" not in st.session_state:
    st.session_state.shared_gw = 0.0

if "sales_vol_wt" not in st.session_state:
    st.session_state.sales_vol_wt = 0.0

if "purchase_vol_wt" not in st.session_state:
    st.session_state.purchase_vol_wt = 0.0


# ------------------------------------------------------------
# 메뉴
# ------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 수출입 B/L 및 마진 등록",
    "📅 선적 일정표 (Schedule)",
    "🏢 거래처별·국가별·품목별 요금 상세 관리",
    "📈 일계표 및 미수금 관리",
    "💳 회사 경비 및 지출 관리"
])


# ============================================================
# TAB 1
# ============================================================
with tab1:
    st.header("📋 수출입 B/L 및 마진 등록")

    with st.container():
        st.markdown(
            "### 📦 1단계: 화물 규격(cm) 및 실중량(kg) 통합 입력"
        )

        col_in1, col_in2, col_in3, col_in4 = st.columns(4)

        with col_in1:
            common_w_str = st.text_input(
                "가로 (cm)",
                value="",
                placeholder="숫자만 바로 입력",
                key="common_w"
            )

        with col_in2:
            common_l_str = st.text_input(
                "세로 (cm)",
                value="",
                placeholder="숫자만 바로 입력",
                key="common_l"
            )

        with col_in3:
            common_h_str = st.text_input(
                "높이 (cm)",
                value="",
                placeholder="숫자만 바로 입력",
                key="common_h"
            )

        with col_in4:
            common_gw_str = st.text_input(
                "실 중량 (Gross Weight, kg)",
                value="",
                placeholder="숫자만 바로 입력",
                key="common_gw"
            )

        col_div1, col_div2, col_btn = st.columns([1, 1, 2])

        with col_div1:
            s_div = st.selectbox(
                "매출 부피중량 기준",
                [5000, 6000],
                key="s_div"
            )

        with col_div2:
            p_div = st.selectbox(
                "매입 부피중량 기준",
                [6000, 5000],
                key="p_div"
            )

        with col_btn:
            st.markdown(
                "<div style='margin-top:24px;'></div>",
                unsafe_allow_html=True
            )

            if st.button(
                "🚀 한 번에 계산 및 아래 폼에 자동 반영",
                type="primary",
                use_container_width=True
            ):
                try:
                    w = safe_float(common_w_str, 0.0)
                    l = safe_float(common_l_str, 0.0)
                    h = safe_float(common_h_str, 0.0)
                    gw = safe_float(common_gw_str, 0.0)
                except ValueError:
                    w, l, h, gw = 0.0, 0.0, 0.0, 0.0

                if w > 0 and l > 0 and h > 0:
                    st.session_state.shared_cbm = (
                        w * l * h
                    ) / 1000000.0

                    st.session_state.shared_gw = gw

                    st.session_state.sales_vol_wt = (
                        w * l * h
                    ) / s_div

                    st.session_state.purchase_vol_wt = (
                        w * l * h
                    ) / p_div

                    st.success(
                        f"통합 계산 완료! "
                        f"CBM: {st.session_state.shared_cbm:.3f} | "
                        f"실중량: {gw}kg | "
                        f"매출부피중량({s_div}): "
                        f"{st.session_state.sales_vol_wt:.2f}kg | "
                        f"매입부피중량({p_div}): "
                        f"{st.session_state.purchase_vol_wt:.2f}kg"
                    )
                else:
                    st.warning(
                        "가로, 세로, 높이 값을 올바른 숫자로 "
                        "모두 입력해주세요."
                    )

        st.info(
            f"👉 현재 반영된 값 ➔ "
            f"CBM: **{st.session_state.shared_cbm:.3f}** | "
            f"실중량: **{st.session_state.shared_gw} kg** | "
            f"매출 부피중량: "
            f"**{st.session_state.sales_vol_wt:.2f} kg** | "
            f"매입 부피중량: "
            f"**{st.session_state.purchase_vol_wt:.2f} kg**"
        )

    st.divider()

    with st.form("margin_form"):
        st.markdown(
            "### 📋 2단계: 상세 B/L 정보 입력"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            io_type = st.selectbox(
                "수출입 구분",
                ["수출 (Export)", "수입 (Import)"]
            )

            job_no = st.text_input(
                "Job 번호 (예: BW-2026-001)"
            )

            bl_no = st.text_input("B/L 번호")

            dest_country = st.selectbox(
                "출발/도착 국가 (지역)",
                COUNTRY_LIST,
                key="form_dest_country"
            )

            item_desc = st.text_input(
                "품목명 (Description)",
                placeholder="예: 일반공산품, 화장품 등",
                key="form_item_desc"
            )

        with col2:
            reg_date = st.date_input(
                "등록/선적 날짜",
                value=date.today()
            )

            shipper_name = st.selectbox(
                "화주명 (매출처)",
                options=[""] + st.session_state.client_list
            )

            purchase_vendor = st.selectbox(
                "매입처 (항공사/선사/파트너)",
                options=[""] + st.session_state.client_list
            )

            transport_type = st.selectbox(
                "운송 형태",
                ["항공(Air)", "해상(FCL)", "해상(LCL)"]
            )

            gross_weight_sales = st.number_input(
                "매출용 실 중량 (Gross Weight, kg)",
                min_value=0.0,
                step=1.0,
                value=float(st.session_state.shared_gw),
                format="%.2f"
            )

            gross_weight_purchase = st.number_input(
                "매입용 실 중량 (Gross Weight, kg)",
                min_value=0.0,
                step=1.0,
                value=float(st.session_state.shared_gw),
                format="%.2f"
            )

        with col3:
            final_sales_cbm = st.number_input(
                "매출 확정 부피 (CBM)",
                value=float(st.session_state.shared_cbm),
                min_value=0.0,
                step=0.001,
                format="%.3f"
            )

            final_sales_vol_wt = st.number_input(
                "매출 확정 부피중량 (kg)",
                value=float(st.session_state.sales_vol_wt),
                min_value=0.0,
                step=0.01,
                format="%.2f"
            )

            raw_sales_chargeable = max(
                gross_weight_sales,
                final_sales_vol_wt
            )

            default_sales_chargeable = (
                math.ceil(raw_sales_chargeable)
                if raw_sales_chargeable > 0
                else 0
            )

            sales_chargeable_weight = st.number_input(
                "매출 청구 중량 (Chargeable Weight, kg - 올림)",
                value=float(default_sales_chargeable),
                min_value=0.0,
                step=1.0,
                format="%.0f"
            )

            s_base_w, s_base_p, s_add_p = 1.0, 35000, 25000

            if shipper_name in st.session_state.client_rates:
                c_dict = st.session_state.client_rates[shipper_name]

                country_items = c_dict.get(
                    dest_country,
                    c_dict.get("기타 국가", {})
                )

                if item_desc in country_items:
                    r = country_items[item_desc]
                else:
                    r = (
                        list(country_items.values())[0]
                        if country_items
                        else {
                            "기본중량": 1.0,
                            "기본요금": 35000,
                            "추가단가": 25000
                        }
                    )

                s_base_w = safe_float(r.get("기본중량", 1.0), 1.0)
                s_base_p = safe_int(r.get("기본요금", 35000), 35000)
                s_add_p = safe_int(r.get("추가단가", 25000), 25000)

            auto_sales = calculate_tier_price(
                sales_chargeable_weight,
                s_base_w,
                s_base_p,
                s_add_p
            )

            total_sales = st.number_input(
                "총 매출액 (원) [품목별 요율 자동계산]",
                value=auto_sales,
                min_value=0,
                step=10000,
                format="%d"
            )

            st.divider()

            final_purchase_cbm = st.number_input(
                "매입 확정 부피 (CBM)",
                value=float(st.session_state.shared_cbm),
                min_value=0.0,
                step=0.001,
                format="%.3f"
            )

            final_purchase_vol_wt = st.number_input(
                "매입 확정 부피중량 (kg)",
                value=float(st.session_state.purchase_vol_wt),
                min_value=0.0,
                step=0.01,
                format="%.2f"
            )

            raw_purchase_chargeable = max(
                gross_weight_purchase,
                final_purchase_vol_wt
            )

            default_purchase_chargeable = (
                math.ceil(raw_purchase_chargeable)
                if raw_purchase_chargeable > 0
                else 0
            )

            purchase_chargeable_weight = st.number_input(
                "매입 청구 중량 (Chargeable Weight, kg - 올림)",
                value=float(default_purchase_chargeable),
                min_value=0.0,
                step=1.0,
                format="%.0f"
            )

            p_base_w, p_base_p, p_add_p = 1.0, 35000, 25000

            if purchase_vendor in st.session_state.client_rates:
                c_dict = st.session_state.client_rates[purchase_vendor]

                country_items = c_dict.get(
                    dest_country,
                    c_dict.get("기타 국가", {})
                )

                if item_desc in country_items:
                    r = country_items[item_desc]
                else:
                    r = (
                        list(country_items.values())[0]
                        if country_items
                        else {
                            "기본중량": 1.0,
                            "기본요금": 35000,
                            "추가단가": 25000
                        }
                    )

                p_base_w = safe_float(r.get("기본중량", 1.0), 1.0)
                p_base_p = safe_int(r.get("기본요금", 35000), 35000)
                p_add_p = safe_int(r.get("추가단가", 25000), 25000)

            auto_purchase = calculate_tier_price(
                purchase_chargeable_weight,
                p_base_w,
                p_base_p,
                p_add_p
            )

            total_purchase = st.number_input(
                "총 매입액 (원) [품목별 요율 자동계산]",
                value=auto_purchase,
                min_value=0,
                step=10000,
                format="%d"
            )

        remarks = st.text_area(
            "비고 (선사, 품목 등 특이사항)"
        )

        submitted = st.form_submit_button(
            "💾 마진 데이터 및 B/L 최종 등록"
        )

        if submitted:
            if job_no and shipper_name:
                margin = total_sales - total_purchase

                new_entry = {
                    "구분": io_type,
                    "날짜": str(reg_date),
                    "Job 번호": job_no,
                    "B/L 번호": bl_no,
                    "국가": dest_country,
                    "화주명(매출)": shipper_name,
                    "매입처": purchase_vendor,
                    "운송형태": transport_type,
                    "품목": item_desc,
                    "매출실중량(kg)": gross_weight_sales,
                    "매출청구중량(kg)": sales_chargeable_weight,
                    "매출액(원)": total_sales,
                    "매입실중량(kg)": gross_weight_purchase,
                    "매입청구중량(kg)": purchase_chargeable_weight,
                    "매입액(원)": total_purchase,
                    "예상마진(원)": margin,
                    "비고": remarks
                }

                st.session_state.bl_data_list.append(
                    new_entry
                )

                save_bl_data(
                    st.session_state.bl_data_list
                )

                st.success(
                    f"Job [{job_no}] 등록 완료!"
                )
            else:
                st.warning(
                    "Job 번호와 화주명(매출처)은 "
                    "필수 입력 항목입니다."
                )

    st.divider()

    col_h1, col_h2 = st.columns([4, 1])

    with col_h1:
        st.subheader(
            "📊 등록된 수출입 B/L 및 마진 내역"
        )

    with col_h2:
        if st.button("🗑️ 등록 내역 전체 초기화"):
            st.session_state.bl_data_list = []
            save_bl_data([])
            st.rerun()

    if st.session_state.bl_data_list:

        for idx, item in enumerate(
            st.session_state.bl_data_list
        ):
            job_display = item.get(
                "Job 번호",
                ""
            )

            sales_display = safe_int(item.get("매출액(원)", 0), 0)

            margin_display = safe_int(item.get("예상마진(원)", 0), 0)

            with st.expander(
                f"📌 [Job: {job_display}] "
                f"화주: {item.get('화주명(매출)', '')} | "
                f"국가: {item.get('국가', '')} | "
                f"매출: {sales_display:,}원 | "
                f"마진: {margin_display:,}원"
            ):

                # ------------------------------------------------
                # PDF 옵션
                # ------------------------------------------------
                st.markdown(
                    "### 📄 PDF 문서 발행"
                )

                client_name = item.get(
                    "화주명(매출)",
                    ""
                )

                client_info = st.session_state.client_infos.get(
                    client_name,
                    {
                        "사업자등록번호": "-",
                        "이메일": "-",
                        "담당자": "-"
                    }
                )

                opt_col1, opt_col2 = st.columns(2)

                with opt_col1:
                    st.markdown(
                        "#### 🖨️ JOB 마진 정산서"
                    )

                    try:
                        margin_pdf = make_margin_pdf(item)

                        st.download_button(
                            label="📥 마진 정산서 PDF 저장",
                            data=margin_pdf,
                            file_name=(
                                f"JOB_마진정산서_"
                                f"{safe_filename(job_display)}.pdf"
                            ),
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"download_margin_pdf_{idx}"
                        )

                        st.caption(
                            "A4 1장 기준 / 매출·매입·마진 내역 포함"
                        )

                    except Exception as e:
                        st.error(
                            "마진 정산서 PDF 생성 오류: "
                            f"{e}"
                        )

                with opt_col2:
                    st.markdown(
                        "#### 📄 매출 Invoice"
                    )

                    apply_vat = st.checkbox(
                        "부가세(VAT 10%) 추가",
                        key=f"vat_check_{idx}"
                    )

                    invoice_status = st.radio(
                        "계산서 발행 상태",
                        [
                            "계산서 발행 완료 건 (우리은행 계좌 안내)",
                            "계산서 미발행 건 (카카오뱅크 계좌 안내)"
                        ],
                        key=f"invoice_status_radio_{idx}"
                    )

                    try:
                        invoice_pdf = make_invoice_pdf(
                            item,
                            client_info,
                            apply_vat,
                            invoice_status
                        )

                        st.download_button(
                            label="📥 매출 Invoice PDF 저장",
                            data=invoice_pdf,
                            file_name=(
                                f"Invoice_"
                                f"{safe_filename(job_display)}.pdf"
                            ),
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"download_invoice_pdf_{idx}"
                        )

                        if apply_vat:
                            st.caption(
                                "공급가액 + 부가세 10%가 적용됩니다."
                            )
                        else:
                            st.caption(
                                "VAT 0원 / 영세율 적용 표시"
                            )

                    except Exception as e:
                        st.error(
                            "Invoice PDF 생성 오류: "
                            f"{e}"
                        )

                st.divider()

                # ------------------------------------------------
                # 화면 미리보기
                # ------------------------------------------------
                preview_col1, preview_col2 = st.columns(2)

                with preview_col1:
                    if st.button(
                        "👁️ 마진 정산서 화면 미리보기",
                        key=f"preview_margin_{idx}",
                        use_container_width=True
                    ):
                        st.session_state[
                            f"show_margin_preview_{idx}"
                        ] = not st.session_state.get(
                            f"show_margin_preview_{idx}",
                            False
                        )

                with preview_col2:
                    if st.button(
                        "👁️ Invoice 화면 미리보기",
                        key=f"preview_invoice_{idx}",
                        use_container_width=True
                    ):
                        st.session_state[
                            f"show_invoice_preview_{idx}"
                        ] = not st.session_state.get(
                            f"show_invoice_preview_{idx}",
                            False
                        )

                if st.session_state.get(
                    f"show_margin_preview_{idx}",
                    False
                ):
                    s_amt = safe_int(item.get("매출액(원)", 0), 0)
                    p_amt = safe_int(item.get("매입액(원)", 0), 0)
                    m_amt = safe_int(item.get("예상마진(원)", 0), 0)

                    st.markdown(
                        f"""
                        <div style="
                            border:2px solid #333;
                            padding:30px;
                            background:#fff;
                            color:#000;
                        ">
                        <h2 style="text-align:center;">
                            (주)범운해운항공
                        </h2>
                        <h4 style="text-align:center;">
                            BUMWOON OCEAN & AIR., LTD.
                        </h4>
                        <h3 style="text-align:center;">
                            [ JOB 마진 정산서 ]
                        </h3>
                        <hr>
                        <p>
                            <b>Job 번호:</b> {item.get('Job 번호', '')}
                            &nbsp;&nbsp;&nbsp;
                            <b>등록일:</b> {item.get('날짜', '')}
                        </p>
                        <p>
                            <b>B/L 번호:</b> {item.get('B/L 번호', '')}
                            &nbsp;&nbsp;&nbsp;
                            <b>운송형태:</b> {item.get('운송형태', '')}
                        </p>
                        <p>
                            <b>화주:</b> {item.get('화주명(매출)', '')}
                            &nbsp;&nbsp;&nbsp;
                            <b>매입처:</b> {item.get('매입처', '')}
                        </p>
                        <p>
                            <b>국가:</b> {item.get('국가', '')}
                            &nbsp;&nbsp;&nbsp;
                            <b>품목:</b> {item.get('품목', '')}
                        </p>
                        <table style="
                            width:100%;
                            border-collapse:collapse;
                            text-align:center;
                        ">
                            <tr style="background:#f2f2f2;">
                                <th style="border:1px solid #777;padding:8px;">
                                    구분
                                </th>
                                <th style="border:1px solid #777;padding:8px;">
                                    실중량
                                </th>
                                <th style="border:1px solid #777;padding:8px;">
                                    청구중량
                                </th>
                                <th style="border:1px solid #777;padding:8px;">
                                    금액
                                </th>
                            </tr>
                            <tr>
                                <td style="border:1px solid #777;padding:8px;">
                                    매출
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {item.get('매출실중량(kg)', 0)}
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {item.get('매출청구중량(kg)', 0)}
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {s_amt:,}원
                                </td>
                            </tr>
                            <tr>
                                <td style="border:1px solid #777;padding:8px;">
                                    매입
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {item.get('매입실중량(kg)', 0)}
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {item.get('매입청구중량(kg)', 0)}
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {p_amt:,}원
                                </td>
                            </tr>
                        </table>
                        <h3 style="text-align:right;">
                            예상 수익 마진: {m_amt:,}원
                        </h3>
                        <p>
                            <b>비고:</b>
                            {item.get('비고', '') or '특이사항 없음'}
                        </p>
                        <br>
                        <p style="text-align:center;font-weight:bold;">
                            주식회사 범운해운항공 (직인생략)
                        </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                if st.session_state.get(
                    f"show_invoice_preview_{idx}",
                    False
                ):
                    supply_amount = safe_int(item.get("매출액(원)", 0), 0)

                    vat_amount = (
                        int(supply_amount * 0.1)
                        if apply_vat
                        else 0
                    )

                    grand_total = (
                        supply_amount + vat_amount
                    )

                    if "미발행" in invoice_status:
                        account_preview = (
                            "<b>카카오뱅크:</b> "
                            "3333-12-9553477 "
                            "(예금주: 이상복 / 범운해운항공)<br>"
                            "<b>우리은행:</b> "
                            "1005-704-932716 "
                            "(예금주: 주식회사 범운해운항공)"
                        )
                    else:
                        account_preview = (
                            "<b>우리은행:</b> "
                            "1005-704-932716 "
                            "(예금주: 주식회사 범운해운항공)"
                        )

                    st.markdown(
                        f"""
                        <div style="
                            max-width:900px;
                            margin:auto;
                            border:2px solid #1f77b4;
                            padding:30px;
                            background:#fff;
                            color:#000;
                        ">
                        <h1 style="text-align:center;color:#1f77b4;">
                            INVOICE (청구서)
                        </h1>
                        <h4 style="text-align:center;">
                            (주)범운해운항공 |
                            BUMWOON OCEAN & AIR., LTD.
                        </h4>
                        <hr>

                        <div style="
                            display:flex;
                            gap:20px;
                        ">
                            <div style="width:50%;">
                                <b>[ 공급자 (Supplier) ]</b><br>
                                상호: (주)범운해운항공<br>
                                대표이사: 이상복<br>
                                본사: 경기도 김포시 풍무동 326-5번지 2동<br>
                                1창고: 경기도 김포시 승가로 110-30 가동<br>
                                2창고: 경기도 김포시 승가로 87-47<br>
                                Tel: 031-989-7071<br>
                                Fax: 031-989-7072<br>
                                E-mail: bumwoon11@naver.com
                            </div>

                            <div style="
                                width:50%;
                                background:#f9f9f9;
                                padding:12px;
                            ">
                                <b>[ 공급받는 자 (Client / Bill To) ]</b><br>
                                상호: {client_name}<br>
                                사업자등록번호:
                                {client_info.get('사업자등록번호', '-') or '-'}<br>
                                담당자:
                                {client_info.get('담당자', '-') or '-'}<br>
                                이메일:
                                {client_info.get('이메일', '-') or '-'}
                            </div>
                        </div>

                        <p>
                            <b>Job No. :</b>
                            {item.get('Job 번호', '')}
                        </p>

                        <table style="
                            width:100%;
                            border-collapse:collapse;
                            text-align:center;
                            font-size:13px;
                        ">
                            <tr style="
                                background:#1f77b4;
                                color:white;
                            ">
                                <th style="padding:8px;border:1px solid #999;">
                                    순서
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    날짜
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    B/L No.
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    목적지
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    청구중량
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    품명
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    공급가액
                                </th>
                            </tr>
                            <tr>
                                <td style="padding:8px;border:1px solid #999;">1</td>
                                <td style="padding:8px;border:1px solid #999;">
                                    {item.get('날짜', '')}
                                </td>
                                <td style="padding:8px;border:1px solid #999;">
                                    {item.get('B/L 번호', '')}
                                </td>
                                <td style="padding:8px;border:1px solid #999;">
                                    {item.get('국가', '')}
                                </td>
                                <td style="padding:8px;border:1px solid #999;">
                                    {item.get('매출청구중량(kg)', 0)} kg
                                </td>
                                <td style="padding:8px;border:1px solid #999;">
                                    {item.get('품목', '')}
                                </td>
                                <td style="padding:8px;border:1px solid #999;">
                                    <b>{supply_amount:,} 원</b>
                                </td>
                            </tr>
                        </table>

                        <div style="
                            text-align:right;
                            margin-top:15px;
                            line-height:1.8;
                        ">
                            공급가액:
                            <b>{supply_amount:,} 원</b><br>
                            부가세(VAT):
                            <b>{vat_amount:,} 원</b>
                            {'(부가세 10% 적용)' if apply_vat else '(영세율 적용)'}<br>
                            <h2 style="color:#d9534f;">
                                총 청구금액:
                                {grand_total:,} 원
                            </h2>
                        </div>

                        <div style="
                            background:#fffbe6;
                            padding:12px;
                            margin-top:20px;
                            border:1px solid #ffe58f;
                            line-height:1.7;
                        ">
                            <b>[ 입금 계좌 안내 ]</b><br>
                            {account_preview}
                        </div>

                        <p style="
                            text-align:center;
                            font-weight:bold;
                            margin-top:35px;
                        ">
                            주식회사 범운해운항공 대표이사 이상복
                        </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        st.dataframe(
            pd.DataFrame(st.session_state.bl_data_list),
            use_container_width=True
        )

    else:
        st.info(
            "아직 등록된 B/L 내역이 없습니다."
        )


# ============================================================
# TAB 2
# ============================================================
with tab2:
    st.markdown(
        "### 📅 선적 일정 관리 (Schedule)"
    )

    st.markdown(
        "선적 스케줄 및 선박/항공편 입출항 일정을 관리합니다."
    )

    st.markdown("---")

    initial_schedule_data = [
        {
            "국가": "미국",
            "운행 수단": "에어",
            "운행 요일": "화요일, 토요일",
            "비고": "정기 항공편"
        },
        {
            "국가": "호주",
            "운행 수단": "해운/에어",
            "운행 요일": "토요일, 일요일",
            "비고": "주말 운행"
        },
        {
            "국가": "인도",
            "운행 수단": "에어",
            "운행 요일": "수요일, 토요일",
            "비고": "정기 항공편"
        },
        {
            "국가": "중국",
            "운행 수단": "해운/에어",
            "운행 요일": "매주 화요일, 금요일",
            "비고": "주 2회"
        },
        {
            "국가": "태국",
            "운행 수단": "에어",
            "운행 요일": "월요일 ~ 토요일",
            "비고": "주 6일 운행"
        }
    ]

    if "schedule_df" not in st.session_state:
        st.session_state.schedule_df = pd.DataFrame(
            initial_schedule_data
        )

    st.markdown(
        "#### 🔍 정기 운행 스케줄표 (직접 수정 가능)"
    )

    edited_schedule_df = st.data_editor(
        st.session_state.schedule_df,
        num_rows="dynamic",
        use_container_width=True,
        key="schedule_editor_box"
    )

    if st.button(
        "스케줄 변경사항 저장",
        type="primary"
    ):
        st.session_state.schedule_df = edited_schedule_df
        st.success(
            "선적 일정 스케줄이 성공적으로 저장되었습니다!"
        )


# ============================================================
# TAB 3
# ============================================================
with tab3:
    st.header(
        "🏢 거래처별·국가별·품목별 요금 상세 관리"
    )

    tab3_sub1, tab3_sub2 = st.tabs([
        "➕ 신규 품목별 요율 등록",
        "✏️ 기존 품목 요금 수정 및 삭제"
    ])

    with tab3_sub1:
        st.subheader(
            "신규 거래처 품명별 요율 설정 및 상세 정보 입력"
        )

        c_info1, c_info2, c_info3 = st.columns(3)

        with c_info1:
            new_client_name = st.text_input(
                "거래처명",
                key="reg_client_name"
            )

        with c_info2:
            reg_biz_no = st.text_input(
                "사업자등록번호",
                key="reg_biz_no"
            )

        with c_info3:
            reg_email = st.text_input(
                "이메일 주소",
                key="reg_email"
            )

        c_info4, c_info5, c_info6 = st.columns(3)

        with c_info4:
            reg_manager = st.text_input(
                "담당자 성명",
                key="reg_manager"
            )

        with c_info5:
            target_country = st.selectbox(
                "적용 국가 선택",
                COUNTRY_LIST,
                key="reg_target_country"
            )

        with c_info6:
            target_item = st.text_input(
                "품명",
                value="일반공산품",
                key="reg_target_item"
            )

        c_rate1, c_rate2, c_rate3 = st.columns(3)

        with c_rate1:
            base_weight = st.number_input(
                "기준 중량 (kg)",
                min_value=0.1,
                value=1.0,
                step=0.5,
                key="reg_base_weight"
            )

        with c_rate2:
            base_price = st.number_input(
                "기본 요금 (원)",
                min_value=0,
                value=35000,
                step=1000,
                key="reg_base_price"
            )

        with c_rate3:
            add_price = st.number_input(
                "추가 1kg당 요금 (원)",
                min_value=0,
                value=25000,
                step=1000,
                key="reg_add_price"
            )

        if st.button(
            "해당 품목 요율 및 거래처 정보 등록하기",
            type="primary"
        ):
            if new_client_name and target_item:
                if new_client_name not in st.session_state.client_list:
                    st.session_state.client_list.append(
                        new_client_name
                    )
                    st.session_state.client_rates[
                        new_client_name
                    ] = {}

                st.session_state.client_infos[
                    new_client_name
                ] = {
                    "사업자등록번호": reg_biz_no,
                    "이메일": reg_email,
                    "담당자": reg_manager
                }

                if target_country not in st.session_state.client_rates[
                    new_client_name
                ]:
                    st.session_state.client_rates[
                        new_client_name
                    ][target_country] = {}

                st.session_state.client_rates[
                    new_client_name
                ][target_country][target_item] = {
                    "기본중량": base_weight,
                    "기본요금": base_price,
                    "추가단가": add_price
                }

                save_client_data(
                    st.session_state.client_list,
                    st.session_state.client_rates,
                    st.session_state.client_infos
                )

                st.success(
                    f"[{new_client_name}] 거래처 정보 및 "
                    f"[{target_country} / {target_item}] "
                    "요율이 등록되었습니다!"
                )

                st.rerun()

            else:
                st.warning(
                    "거래처명과 품명은 필수 입력 사항입니다."
                )

    with tab3_sub2:
        st.subheader(
            "기존 품목별 요금 수정 및 삭제"
        )

        if st.session_state.client_list:
            flat_data = []

            for client, c_dict in (
                st.session_state.client_rates.items()
            ):
                for country, item_dict in c_dict.items():
                    if not isinstance(item_dict, dict):
                        continue

                    for item_name, r_val in item_dict.items():
                        flat_data.append({
                            "거래처명": client,
                            "적용 국가": country,
                            "품명": item_name,
                            "기준 중량(kg)": r_val.get(
                                "기본중량", 1.0
                            ),
                            "기본 요금(원)": r_val.get(
                                "기본요금", 35000
                            ),
                            "추가 단가(원/kg)": r_val.get(
                                "추가단가", 25000
                            )
                        })

            st.markdown(
                "#### 📋 전체 품목 요율 목록 및 빠른 관리"
            )

            for i, row_data in enumerate(flat_data):
                col_info1, col_info2, col_info3, col_btn_edit, col_btn_del = st.columns(
                    [2, 1, 2, 1, 1]
                )

                with col_info1:
                    st.markdown(
                        f"**거래처:** {row_data['거래처명']}"
                    )

                with col_info2:
                    st.markdown(
                        f"**국가:** {row_data['적용 국가']}"
                    )

                with col_info3:
                    st.markdown(
                        f"**품명:** {row_data['품명']}"
                    )

                with col_btn_edit:
                    if st.button(
                        "수정 선택",
                        key=f"select_row_{i}"
                    ):
                        st.session_state.is_editing = True
                        st.session_state.edit_client = (
                            row_data["거래처명"]
                        )
                        st.session_state.edit_country = (
                            row_data["적용 국가"]
                        )
                        st.session_state.edit_item = (
                            row_data["품명"]
                        )
                        st.rerun()

                with col_btn_del:
                    if st.button(
                        "🗑️ 삭제",
                        key=f"delete_row_{i}"
                    ):
                        c_name = row_data["거래처명"]
                        co_name = row_data["적용 국가"]
                        i_name = row_data["품명"]

                        if (
                            c_name in st.session_state.client_rates
                            and co_name in st.session_state.client_rates[c_name]
                        ):
                            if (
                                i_name
                                in st.session_state.client_rates[
                                    c_name
                                ][co_name]
                            ):
                                del st.session_state.client_rates[
                                    c_name
                                ][co_name][i_name]

                        save_client_data(
                            st.session_state.client_list,
                            st.session_state.client_rates,
                            st.session_state.client_infos
                        )

                        st.success(
                            f"[{c_name} / {co_name} / {i_name}] "
                            "품목이 삭제되었습니다."
                        )

                        st.rerun()

            st.divider()

            if st.session_state.is_editing:
                c_name = st.session_state.edit_client
                co_name = st.session_state.edit_country
                i_name = st.session_state.edit_item

                current_r = (
                    st.session_state.client_rates
                    .get(c_name, {})
                    .get(co_name, {})
                    .get(
                        i_name,
                        {
                            "기본중량": 1.0,
                            "기본요금": 35000,
                            "추가단가": 25000
                        }
                    )
                )

                c1, c2 = st.columns(2)

                with c1:
                    e_base_w = st.number_input(
                        "기준 중량 (kg)",
                        min_value=0.1,
                        value=safe_float(
                            current_r.get(
                                "기본중량", 1.0
                            ),
                            1.0
                        ),
                        step=0.5,
                        key="edit_base_w"
                    )

                with c2:
                    e_base_p = st.number_input(
                        "기본 요금 (원)",
                        min_value=0,
                        value=safe_int(
                            current_r.get(
                                "기본요금", 35000
                            ),
                            35000
                        ),
                        step=1000,
                        key="edit_base_p"
                    )

                e_add_p = st.number_input(
                    "추가 1kg당 요금 (원)",
                    min_value=0,
                    value=safe_int(
                        current_r.get(
                            "추가단가", 25000
                        ),
                        25000
                    ),
                    step=1000,
                    key="edit_add_p"
                )

                col_btn1, col_btn2 = st.columns(2)

                with col_btn1:
                    if st.button(
                        "💾 수정 내용 저장 반영",
                        type="primary",
                        use_container_width=True
                    ):
                        if c_name not in st.session_state.client_rates:
                            st.session_state.client_rates[c_name] = {}

                        if co_name not in st.session_state.client_rates[c_name]:
                            st.session_state.client_rates[c_name][co_name] = {}

                        st.session_state.client_rates[
                            c_name
                        ][co_name][i_name] = {
                            "기본중량": e_base_w,
                            "기본요금": e_base_p,
                            "추가단가": e_add_p
                        }

                        save_client_data(
                            st.session_state.client_list,
                            st.session_state.client_rates,
                            st.session_state.client_infos
                        )

                        st.success("수정 완료!")
                        st.session_state.is_editing = False
                        st.rerun()

                with col_btn2:
                    if st.button(
                        "❌ 수정 취소",
                        use_container_width=True
                    ):
                        st.session_state.is_editing = False
                        st.rerun()


# ============================================================
# TAB 4
# ============================================================
with tab4:
    st.header("📈 일계표 및 미수금 관리")

    st.markdown(
        "등록된 B/L 매출/매입 내역을 바탕으로 "
        "일일 매출·매입 현황과 거래처별 미수금을 관리합니다."
    )

    st.divider()

    st.subheader(
        "📅 날짜별 일계표 (매출 / 매입 / 순이익 현황)"
    )

    if st.session_state.bl_data_list:
        df_acc = pd.DataFrame(
            st.session_state.bl_data_list
        )

        for _col in ["매출액(원)", "매입액(원)", "예상마진(원)"]:
            if _col not in df_acc.columns:
                df_acc[_col] = 0
            df_acc[_col] = pd.to_numeric(df_acc[_col], errors="coerce").fillna(0)
        if "날짜" not in df_acc.columns:
            df_acc["날짜"] = ""
        if "Job 번호" not in df_acc.columns:
            df_acc["Job 번호"] = ""

        daily_summary = (
            df_acc.groupby("날짜")
            .agg(
                총매출액=("매출액(원)", "sum"),
                총매입액=("매입액(원)", "sum"),
                총마진=("예상마진(원)", "sum"),
                건수=("Job 번호", "count")
            )
            .reset_index()
            .sort_values(
                by="날짜",
                ascending=False
            )
        )

        st.dataframe(
            daily_summary,
            use_container_width=True
        )

    else:
        st.info(
            "등록된 B/L 내역이 없어 일계표를 표시할 수 없습니다."
        )

    st.divider()

    st.subheader(
        "🏢 거래처별 미수금(청구 대비 입금) 관리"
    )

    if st.session_state.bl_data_list:
        df_bl_ledger = pd.DataFrame(
            st.session_state.bl_data_list
        )

        client_sales = (
            df_bl_ledger
            .groupby("화주명(매출)")["매출액(원)"]
            .sum()
            .reset_index()
        )

        client_sales.columns = [
            "거래처명",
            "총청구금액"
        ]

        account_df = pd.DataFrame(
            st.session_state.account_data_list
        )

        if "입금액(원)" in account_df.columns:
            account_df["입금액(원)"] = pd.to_numeric(account_df["입금액(원)"], errors="coerce").fillna(0)

        if (
            not account_df.empty
            and "거래처명" in account_df.columns
            and "입금액(원)" in account_df.columns
        ):
            client_received = (
                account_df
                .groupby("거래처명")["입금액(원)"]
                .sum()
                .reset_index()
            )
        else:
            client_received = pd.DataFrame(
                columns=[
                    "거래처명",
                    "입금액(원)"
                ]
            )

        ledger_merged = pd.merge(
            client_sales,
            client_received,
            on="거래처명",
            how="left"
        ).fillna(0)

        ledger_merged["미수금잔액(원)"] = (
            ledger_merged["총청구금액"]
            - ledger_merged["입금액(원)"]
        )

        st.markdown(
            "#### 📋 거래처별 미수금 현황 요약"
        )

        st.dataframe(
            ledger_merged,
            use_container_width=True
        )

        st.markdown(
            "#### 💰 입금(수금) 내역 직접 등록"
        )

        active_clients = st.session_state.get(
            "client_list",
            []
        )

        if not active_clients:
            active_clients = [
                "(주)홍길동상사",
                "ABC로지스틱스",
                "글로벌쉬핑",
                "글루오필메디앤코",
                "카스항운"
            ]

        with st.form("deposit_form"):
            col_d1, col_d2, col_d3 = st.columns(3)

            with col_d1:
                dep_client = st.selectbox(
                    "거래처 선택",
                    options=active_clients
                )

            with col_d2:
                dep_amount = st.number_input(
                    "입금된 금액 (원)",
                    min_value=0,
                    step=10000,
                    format="%d"
                )

            with col_d3:
                dep_date = st.date_input(
                    "입금일자",
                    value=date.today()
                )

            dep_memo = st.text_input(
                "입금 관련 메모"
            )

            submitted_dep = st.form_submit_button(
                "💳 수금/입금 내역 반영하기"
            )

            if submitted_dep:
                if dep_client and dep_amount > 0:
                    new_dep = {
                        "날짜": str(dep_date),
                        "거래처명": dep_client,
                        "입금액(원)": dep_amount,
                        "메모": dep_memo
                    }

                    st.session_state.account_data_list.append(
                        new_dep
                    )

                    save_account_data(
                        st.session_state.account_data_list
                    )

                    st.success(
                        f"[{dep_client}] 거래처의 입금액 "
                        f"{dep_amount:,}원이 정상 반영되었습니다!"
                    )

                    st.rerun()

                else:
                    st.warning(
                        "거래처를 선택하고 0원 초과의 "
                        "입금액을 입력해주세요."
                    )

        if st.session_state.account_data_list:
            st.markdown(
                "#### 📜 상세 입금 내역 리스트"
            )

            st.dataframe(
                pd.DataFrame(
                    st.session_state.account_data_list
                ),
                use_container_width=True
            )

            if st.button(
                "🗑️ 입금 내역 전체 초기화"
            ):
                st.session_state.account_data_list = []
                save_account_data([])
                st.rerun()

    else:
        st.info(
            "거래처별 미수금을 계산할 B/L 매출 데이터가 없습니다."
        )


# ============================================================
# TAB 5
# ============================================================
with tab5:
    st.header(
        "💳 회사 경비 및 지출 관리"
    )

    st.markdown(
        "주유비, 식대, 접대비 및 각종 기타 잡비 "
        "지출 내역을 등록하고 관리합니다."
    )

    st.divider()

    with st.form("expense_form"):
        st.markdown(
            "### ✍️ 지출 경비 직접 등록"
        )

        ex_col1, ex_col2, ex_col3 = st.columns(3)

        with ex_col1:
            ex_date = st.date_input(
                "지출 일자",
                value=date.today(),
                key="ex_date"
            )

        with ex_col2:
            ex_category = st.selectbox(
                "비용 항목 (계정과목)",
                EXPENSE_CATEGORIES,
                key="ex_category"
            )

        with ex_col3:
            ex_amount = st.number_input(
                "지출 금액 (원)",
                min_value=0,
                step=1000,
                format="%d",
                key="ex_amount"
            )

        ex_col4, ex_col5 = st.columns(2)

        with ex_col4:
            ex_pay_method = st.selectbox(
                "결제 수단",
                [
                    "법인카드",
                    "현금",
                    "계좌이체",
                    "개인카드 (사후정산)"
                ],
                key="ex_pay_method"
            )

        with ex_col5:
            ex_vendor = st.text_input(
                "거래처 / 사용처",
                placeholder="어디서 사용하셨나요?",
                key="ex_vendor"
            )

        ex_memo = st.text_area(
            "지출 상세 메모",
            key="ex_memo"
        )

        submitted_ex = st.form_submit_button(
            "💾 지출 경비 등록하기",
            type="primary"
        )

        if submitted_ex:
            if ex_amount > 0:
                new_expense = {
                    "날짜": str(ex_date),
                    "항목": ex_category,
                    "금액(원)": ex_amount,
                    "결제수단": ex_pay_method,
                    "사용처": ex_vendor,
                    "메모": ex_memo
                }

                st.session_state.expense_data_list.append(
                    new_expense
                )

                save_expense_data(
                    st.session_state.expense_data_list
                )

                st.success(
                    f"[{ex_category}] 지출 금액 "
                    f"{ex_amount:,}원이 정상 등록되었습니다!"
                )

                st.rerun()

            else:
                st.warning(
                    "0원 초과의 지출 금액을 입력해주세요."
                )

    st.divider()

    st.subheader(
        "📊 항목별 경비 지출 요약"
    )

    if st.session_state.expense_data_list:
        df_exp = pd.DataFrame(
            st.session_state.expense_data_list
        )

        if "금액(원)" not in df_exp.columns:
            df_exp["금액(원)"] = 0
        df_exp["금액(원)"] = pd.to_numeric(df_exp["금액(원)"], errors="coerce").fillna(0)
        if "항목" not in df_exp.columns:
            df_exp["항목"] = "기타 잡비"

        exp_summary = (
            df_exp.groupby("항목")["금액(원)"]
            .agg(["count", "sum"])
            .reset_index()
        )

        exp_summary.columns = [
            "비용 항목",
            "지출 건수",
            "총 지출액(원)"
        ]

        st.dataframe(
            exp_summary,
            use_container_width=True
        )

        st.markdown(
            "#### 📜 상세 지출 경비 내역 리스트"
        )

        st.dataframe(
            df_exp,
            use_container_width=True
        )

        if st.button(
            "🗑️ 경비 내역 전체 초기화"
        ):
            st.session_state.expense_data_list = []
            save_expense_data([])
            st.rerun()

    else:
        st.info(
            "아직 등록된 경비 지출 내역이 없습니다."
        )
import streamlit as st
import pandas as pd
from datetime import date
import math
import os
import base64
from io import BytesIO

# ============================================================
# (주)범운해운항공 종합 관리 프로그램
# 최종본 - A4 PDF 직접 저장 / 마진 정산서 + 매출 Invoice 분리
# ============================================================

st.set_page_config(
    page_title="(주)범운해운항공 종합 관리 프로그램",
    page_icon="🚢",
    layout="wide"
)

# ------------------------------------------------------------
# 기본 경로 / 파일
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "bl_history_data.csv")
CLIENT_FILE = os.path.join(BASE_DIR, "client_data.csv")
ACCOUNT_FILE = os.path.join(BASE_DIR, "account_ledger_data.csv")
EXPENSE_FILE = os.path.join(BASE_DIR, "expense_data.csv")

COUNTRY_LIST = [
    "미국", "중국", "호주", "태국", "인도",
    "멕시코", "홍콩", "베트남", "기타 국가"
]

EXPENSE_CATEGORIES = [
    "주유비 (차량유지비)",
    "식대 (복리후생비)",
    "접대비",
    "소모품비",
    "통신비",
    "공과금",
    "기타 잡비"
]


# ------------------------------------------------------------
# 회사 로고 자동 감지
# ------------------------------------------------------------
LOGO_FILE = None

for filename in os.listdir(BASE_DIR):
    lower_name = filename.lower()
    if lower_name.startswith("lo") and lower_name.endswith(
        (".png", ".jpg", ".jpeg", ".webp")
    ):
        LOGO_FILE = os.path.join(BASE_DIR, filename)
        break


# ------------------------------------------------------------
# 안전한 데이터 변환
# ------------------------------------------------------------
def safe_text(value, default=""):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    return str(value)


def safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        text = str(value).strip().replace(",", "")
        if text == "" or text.lower() in {"nan", "none", "null"}:
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(round(safe_float(value, default)))
    except Exception:
        return default


def normalize_bl_record(record):
    record = dict(record)

    # 이전 버전 컬럼명 호환
    if not safe_text(record.get("화주명(매출)")).strip() and "화주명(매출처)" in record:
        record["화주명(매출)"] = record.get("화주명(매출처)")
    if not safe_text(record.get("예상마진(원)")).strip() and "예상Profit(원)" in record:
        record["예상마진(원)"] = record.get("예상Profit(원)")
    if not safe_text(record.get("예상Profit(원)")).strip() and "예상마진(원)" in record:
        record["예상Profit(원)"] = record.get("예상마진(원)")

    # 오래된 CSV에 일부 컬럼이 없더라도 화면이 중단되지 않게 기본값 보완
    defaults = {
        "구분": "",
        "날짜": "",
        "Job 번호": "",
        "B/L 번호": "",
        "국가": "",
        "화주명(매출)": "",
        "매입처": "",
        "운송형태": "",
        "품목": "",
        "매출실중량(kg)": 0,
        "매출청구중량(kg)": 0,
        "매출액(원)": 0,
        "매입실중량(kg)": 0,
        "매입청구중량(kg)": 0,
        "매입액(원)": 0,
        "예상마진(원)": 0,
        "비고": "",
    }
    for key, default in defaults.items():
        if key not in record:
            record[key] = default

    return record


# ------------------------------------------------------------
# 데이터 불러오기
# ------------------------------------------------------------
def load_bl_data():
    if not os.path.exists(DATA_FILE):
        return []

    for encoding in ("utf-8-sig", "cp949", "utf-8"):
        try:
            df = pd.read_csv(DATA_FILE, encoding=encoding)
            if "예상Profit(원)" in df.columns and "예상마진(원)" not in df.columns:
                df["예상마진(원)"] = df["예상Profit(원)"]
            return [normalize_bl_record(x) for x in df.to_dict("records")]
        except Exception:
            continue
    return []


def load_client_data():
    if os.path.exists(CLIENT_FILE):
        for encoding in ("utf-8-sig", "cp949", "utf-8"):
            try:
                df = pd.read_csv(CLIENT_FILE, encoding=encoding)
                if "거래처명" not in df.columns:
                    continue

                clients = [safe_text(x).strip() for x in df["거래처명"].dropna().unique().tolist() if safe_text(x).strip()]
                rates = {}
                client_infos = {}

                for client in clients:
                    rates[client] = {}
                    sub_df = df[df["거래처명"].astype(str) == client]
                    if sub_df.empty:
                        continue

                    first_row = sub_df.iloc[0]
                    client_infos[client] = {
                        "사업자등록번호": safe_text(first_row.get("사업자등록번호", "")),
                        "이메일": safe_text(first_row.get("이메일", "")),
                        "담당자": safe_text(first_row.get("담당자", ""))
                    }

                    for _, row in sub_df.iterrows():
                        country = safe_text(row.get("국가", "기타 국가")).strip() or "기타 국가"
                        item = safe_text(row.get("품명", "일반공산품")).strip() or "일반공산품"
                        rates[client].setdefault(country, {})
                        rates[client][country][item] = {
                            "기본중량": safe_float(row.get("기본중량", 1.0), 1.0),
                            "기본요금": safe_int(row.get("기본요금", 35000), 35000),
                            "추가단가": safe_int(row.get("추가단가", 25000), 25000),
                            "1CBM당단가": safe_int(row.get("1CBM당단가", 0), 0),
                        }

                if clients:
                    return clients, rates, client_infos
            except Exception:
                continue

    default_clients = [
        "(주)홍길동상사",
        "ABC로지스틱스",
        "글로벌쉬핑",
        "글루오필메디앤코",
        "대한항공(KE)",
        "아시아나(OZ)",
        "캐세이퍼시픽(CX)",
        "카스항운",
        "글로우필"
    ]

    default_rates = {}
    default_infos = {
        c: {
            "사업자등록번호": "000-00-00000",
            "이메일": "example@bumwoon.com",
            "담당자": "담당자"
        }
        for c in default_clients
    }

    for client in default_clients:
        default_rates[client] = {}
        for country in COUNTRY_LIST:
            default_rates[client][country] = {
                "일반공산품": {
                    "기본중량": 1.0,
                    "기본요금": 35000 if client == "카스항운" else 30000,
                    "추가단가": 25000,
                    "1CBM당단가": 0
                },
                "화장품": {
                    "기본중량": 1.0,
                    "기본요금": 38000,
                    "추가단가": 28000,
                    "1CBM당단가": 0
                }
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
            return pd.read_csv(EXPENSE_FILE).to_dict("records")
        except Exception:
            return []
    return []


# ------------------------------------------------------------
# 데이터 저장
# ------------------------------------------------------------
def save_bl_data(data_list):
    if data_list:
        pd.DataFrame(data_list).to_csv(
            DATA_FILE,
            index=False,
            encoding="utf-8-sig"
        )
    elif os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)


def save_client_data(client_list, client_rates, client_infos):
    rows = []

    for client in client_list:
        info = client_infos.get(
            client,
            {
                "사업자등록번호": "",
                "이메일": "",
                "담당자": ""
            }
        )

        country_dict = client_rates.get(client, {})

        for country, item_dict in country_dict.items():
            if not isinstance(item_dict, dict):
                continue

            for item_name, r_val in item_dict.items():
                rows.append({
                    "거래처명": client,
                    "사업자등록번호": info.get(
                        "사업자등록번호", ""
                    ),
                    "이메일": info.get("이메일", ""),
                    "담당자": info.get("담당자", ""),
                    "국가": country,
                    "품명": item_name,
                    "기본중량": r_val.get("기본중량", 1.0),
                    "기본요금": r_val.get("기본요금", 35000),
                    "추가단가": r_val.get("추가단가", 25000)
                })

    pd.DataFrame(rows).to_csv(
        CLIENT_FILE,
        index=False,
        encoding="utf-8-sig"
    )


def save_account_data(data_list):
    if data_list:
        pd.DataFrame(data_list).to_csv(
            ACCOUNT_FILE,
            index=False,
            encoding="utf-8-sig"
        )
    elif os.path.exists(ACCOUNT_FILE):
        os.remove(ACCOUNT_FILE)


def save_expense_data(data_list):
    if data_list:
        pd.DataFrame(data_list).to_csv(
            EXPENSE_FILE,
            index=False,
            encoding="utf-8-sig"
        )
    elif os.path.exists(EXPENSE_FILE):
        os.remove(EXPENSE_FILE)


# ------------------------------------------------------------
# 계산
# ------------------------------------------------------------
def calculate_tier_price(
    chargeable_weight,
    base_weight,
    base_price,
    add_price
):
    weight = max(0.0, safe_float(chargeable_weight, 0.0))
    base_w = max(0.0, safe_float(base_weight, 1.0))
    base_p = safe_int(base_price, 35000)
    add_p = safe_int(add_price, 25000)

    if weight <= 0:
        return 0
    if weight <= base_w:
        return base_p

    excess_weight = math.ceil(weight - base_w)
    return int(base_p + excess_weight * add_p)


# ------------------------------------------------------------
# PDF 생성
# ReportLab이 설치되어 있어야 합니다.
# Streamlit Cloud / 일반 Python 환경에서:
# pip install reportlab
# ------------------------------------------------------------
def get_pdf_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    font_name = "HYSMyeongJo-Medium"

    try:
        pdfmetrics.getFont(font_name)
    except Exception:
        pdfmetrics.registerFont(
            UnicodeCIDFont(font_name)
        )

    return font_name


def make_margin_pdf(item):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image
    )

    font = get_pdf_fonts()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"JOB 마진 정산서 - {item.get('Job 번호', '')}"
    )

    normal = ParagraphStyle(
        "NormalKR",
        fontName=font,
        fontSize=9.5,
        leading=14
    )

    small = ParagraphStyle(
        "SmallKR",
        fontName=font,
        fontSize=8.5,
        leading=12
    )

    title_style = ParagraphStyle(
        "TitleKR",
        fontName=font,
        fontSize=17,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "SubtitleKR",
        fontName=font,
        fontSize=11,
        leading=15,
        alignment=TA_CENTER
    )

    right_style = ParagraphStyle(
        "RightKR",
        fontName=font,
        fontSize=12,
        leading=17,
        alignment=TA_RIGHT
    )

    story = []

    # 로고
    if LOGO_FILE and os.path.exists(LOGO_FILE):
        try:
            logo = Image(LOGO_FILE)
            logo.drawHeight = 14 * mm
            logo.drawWidth = 42 * mm
            story.append(
                Table(
                    [[logo]],
                    colWidths=[180 * mm]
                )
            )
            story.append(Spacer(1, 3 * mm))
        except Exception:
            pass

    story.append(
        Paragraph(
            "(주)범운해운항공 / BUMWOON OCEAN & AIR., LTD.",
            title_style
        )
    )

    story.append(
        Paragraph(
            "[ JOB 마진 정산서 ]",
            subtitle_style
        )
    )

    story.append(Spacer(1, 5 * mm))

    info_data = [
        [
            Paragraph(
                f"<b>Job 번호:</b> {item.get('Job 번호', '')}",
                normal
            ),
            Paragraph(
                f"<b>등록 일자:</b> {item.get('날짜', '')}",
                normal
            )
        ],
        [
            Paragraph(
                f"<b>B/L 번호:</b> {item.get('B/L 번호', '')}",
                normal
            ),
            Paragraph(
                f"<b>운송 형태:</b> {item.get('운송형태', '')} "
                f"({item.get('구분', '')})",
                normal
            )
        ],
        [
            Paragraph(
                f"<b>화주명 (매출처):</b> "
                f"{item.get('화주명(매출)', '')}",
                normal
            ),
            Paragraph(
                f"<b>매입처:</b> {item.get('매입처', '')}",
                normal
            )
        ],
        [
            Paragraph(
                f"<b>목적 국가:</b> {item.get('국가', '')}",
                normal
            ),
            Paragraph(
                f"<b>품목명:</b> {item.get('품목', '')}",
                normal
            )
        ]
    ]

    info_table = Table(
        info_data,
        colWidths=[90 * mm, 90 * mm]
    )

    info_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ])
    )

    story.append(info_table)
    story.append(Spacer(1, 5 * mm))

    sales_amount = safe_int(item.get("매출액(원)", 0), 0)
    purchase_amount = safe_int(item.get("매입액(원)", 0), 0)
    margin_amount = safe_int(item.get("예상마진(원)", 0), 0)

    amount_data = [
        [
            Paragraph("<b>구분</b>", normal),
            Paragraph("<b>실중량 (kg)</b>", normal),
            Paragraph("<b>청구중량 (kg)</b>", normal),
            Paragraph("<b>금액 (KRW)</b>", normal)
        ],
        [
            Paragraph("<b>매출 (Sales)</b>", normal),
            Paragraph(
                str(item.get("매출실중량(kg)", 0)),
                normal
            ),
            Paragraph(
                str(item.get("매출청구중량(kg)", 0)),
                normal
            ),
            Paragraph(
                f"{sales_amount:,} 원",
                normal
            )
        ],
        [
            Paragraph("<b>매입 (Purchase)</b>", normal),
            Paragraph(
                str(item.get("매입실중량(kg)", 0)),
                normal
            ),
            Paragraph(
                str(item.get("매입청구중량(kg)", 0)),
                normal
            ),
            Paragraph(
                f"{purchase_amount:,} 원",
                normal
            )
        ]
    ]

    amount_table = Table(
        amount_data,
        colWidths=[45 * mm, 40 * mm, 45 * mm, 50 * mm],
        repeatRows=1
    )

    amount_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.7, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(amount_table)
    story.append(Spacer(1, 7 * mm))

    story.append(
        Paragraph(
            f"<b>예상 수익 마진: {margin_amount:,} 원</b>",
            right_style
        )
    )

    story.append(Spacer(1, 8 * mm))

    remarks = str(
        item.get("비고", "") or "특이사항 없음"
    ).replace("\n", "<br/>")

    story.append(
        Paragraph(
            f"<b>비고:</b> {remarks}",
            normal
        )
    )

    story.append(Spacer(1, 25 * mm))

    story.append(
        Paragraph(
            "주식회사 범운해운항공 (직인생략)",
            ParagraphStyle(
                "SignKR",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_CENTER
            )
        )
    )

    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()


def make_invoice_pdf(item, client_info, apply_vat, invoice_status):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image
    )

    font = get_pdf_fonts()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Invoice - {item.get('Job 번호', '')}"
    )

    normal = ParagraphStyle(
        "InvoiceNormalKR",
        fontName=font,
        fontSize=8.5,
        leading=12
    )

    small = ParagraphStyle(
        "InvoiceSmallKR",
        fontName=font,
        fontSize=7.5,
        leading=10
    )

    title_style = ParagraphStyle(
        "InvoiceTitleKR",
        fontName=font,
        fontSize=19,
        leading=24,
        alignment=TA_CENTER
    )

    center = ParagraphStyle(
        "InvoiceCenterKR",
        fontName=font,
        fontSize=8.5,
        leading=12,
        alignment=TA_CENTER
    )

    right = ParagraphStyle(
        "InvoiceRightKR",
        fontName=font,
        fontSize=9.5,
        leading=14,
        alignment=TA_RIGHT
    )

    total_style = ParagraphStyle(
        "InvoiceTotalKR",
        fontName=font,
        fontSize=12,
        leading=17,
        alignment=TA_RIGHT
    )

    story = []

    # 상단 로고 + 제목
    header_cells = []

    if LOGO_FILE and os.path.exists(LOGO_FILE):
        try:
            logo = Image(LOGO_FILE)
            logo.drawHeight = 14 * mm
            logo.drawWidth = 40 * mm
            header_cells.append(logo)
        except Exception:
            header_cells.append("")
    else:
        header_cells.append("")

    header_cells.append(
        Paragraph(
            "<b>INVOICE (청구서)</b><br/>"
            "<font size='9'>"
            "(주)범운해운항공 | BUMWOON OCEAN & AIR., LTD."
            "</font>",
            title_style
        )
    )

    header_table = Table(
        [header_cells],
        colWidths=[45 * mm, 135 * mm]
    )

    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    story.append(header_table)
    story.append(Spacer(1, 3 * mm))

    # 공급자 / 공급받는 자
    client_name = str(
        item.get("화주명(매출)", "")
    )

    supplier_text = (
        "<b>[ 공급자 (Supplier) ]</b><br/>"
        "<b>상호:</b> (주)범운해운항공 "
        "(BUMWOON OCEAN & AIR., LTD.)<br/>"
        "<b>대표이사:</b> 이상복<br/>"
        "<b>본사:</b> 경기도 김포시 풍무동 326-5번지 2동<br/>"
        "<b>1창고:</b> 경기도 김포시 승가로 110-30 가동<br/>"
        "<b>2창고:</b> 경기도 김포시 승가로 87-47<br/>"
        "<b>Tel:</b> 031-989-7071 "
        "&nbsp;&nbsp; <b>Fax:</b> 031-989-7072<br/>"
        "<b>E-mail:</b> bumwoon11@naver.com"
    )

    client_text = (
        "<b>[ 공급받는 자 (Client / Bill To) ]</b><br/>"
        f"<b>상호:</b> {client_name}<br/>"
        f"<b>사업자등록번호:</b> "
        f"{client_info.get('사업자등록번호', '-') or '-'}<br/>"
        f"<b>담당자:</b> "
        f"{client_info.get('담당자', '-') or '-'}<br/>"
        f"<b>이메일:</b> "
        f"{client_info.get('이메일', '-') or '-'}"
    )

    party_table = Table(
        [[
            Paragraph(supplier_text, normal),
            Paragraph(client_text, normal)
        ]],
        colWidths=[90 * mm, 90 * mm]
    )

    party_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cccccc")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f7f7f7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(party_table)
    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            f"<b>Job No. : {item.get('Job 번호', '')}</b>",
            normal
        )
    )

    story.append(Spacer(1, 3 * mm))

    supply_amount = safe_int(item.get("매출액(원)", 0), 0)

    vat_amount = (
        int(supply_amount * 0.1)
        if apply_vat else 0
    )

    grand_total = supply_amount + vat_amount

    invoice_data = [
        [
            Paragraph("<b>순서</b>", center),
            Paragraph("<b>날짜</b>", center),
            Paragraph("<b>B/L No.</b>", center),
            Paragraph("<b>목적지</b>", center),
            Paragraph("<b>청구중량</b>", center),
            Paragraph("<b>품명</b>", center),
            Paragraph("<b>공급가액</b>", center)
        ],
        [
            Paragraph("1", center),
            Paragraph(
                str(item.get("날짜", "")),
                center
            ),
            Paragraph(
                str(item.get("B/L 번호", "")),
                center
            ),
            Paragraph(
                str(item.get("국가", "")),
                center
            ),
            Paragraph(
                f"{item.get('매출청구중량(kg)', 0)} kg",
                center
            ),
            Paragraph(
                str(item.get("품목", "")),
                center
            ),
            Paragraph(
                f"<b>{supply_amount:,}</b>",
                center
            )
        ]
    ]

    invoice_table = Table(
        invoice_data,
        colWidths=[
            12 * mm,
            23 * mm,
            32 * mm,
            23 * mm,
            24 * mm,
            38 * mm,
            28 * mm
        ],
        repeatRows=1
    )

    invoice_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#888888")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeaf7")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ])
    )

    story.append(invoice_table)
    story.append(Spacer(1, 5 * mm))

    vat_text = (
        "(영세율 적용)"
        if not apply_vat
        else "(부가세 10% 적용)"
    )

    summary_data = [
        [
            "",
            Paragraph(
                f"공급가액: <b>{supply_amount:,} 원</b>",
                right
            )
        ],
        [
            "",
            Paragraph(
                f"부가세(VAT): <b>{vat_amount:,} 원</b> "
                f"{vat_text}",
                right
            )
        ],
        [
            "",
            Paragraph(
                f"<b>총 청구금액: {grand_total:,} 원</b>",
                total_style
            )
        ]
    ]

    summary_table = Table(
        summary_data,
        colWidths=[80 * mm, 100 * mm]
    )

    summary_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )

    story.append(summary_table)
    story.append(Spacer(1, 5 * mm))

    if "미발행" in invoice_status:
        account_text = (
            "<b>[ 입금 계좌 안내 - 계산서 미발행 건 ]</b><br/>"
            "카카오뱅크: 3333-12-9553477 "
            "(예금주: 이상복 / 범운해운항공)<br/>"
            "우리은행: 1005-704-932716 "
            "(예금주: 주식회사 범운해운항공)"
        )
    else:
        account_text = (
            "<b>[ 입금 계좌 안내 - 계산서 발행 완료 건 ]</b><br/>"
            "우리은행: 1005-704-932716 "
            "(예금주: 주식회사 범운해운항공)"
        )

    account_table = Table(
        [[Paragraph(account_text, normal)]],
        colWidths=[180 * mm]
    )

    account_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#e0c45c")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbe6")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )

    story.append(account_table)
    story.append(Spacer(1, 13 * mm))

    story.append(
        Paragraph(
            "주식회사 범운해운항공 대표이사 이상복",
            ParagraphStyle(
                "InvoiceSignKR",
                fontName=font,
                fontSize=10,
                leading=14,
                alignment=TA_CENTER
            )
        )
    )

    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()


# ------------------------------------------------------------
# PDF 파일명
# ------------------------------------------------------------
def safe_filename(value):
    value = str(value or "").strip()

    if not value:
        value = "NO_JOB"

    for char in '\\/:*?"<>|':
        value = value.replace(char, "_")

    return value


# ------------------------------------------------------------
# 상단 제목 / 로고
# ------------------------------------------------------------
if LOGO_FILE and os.path.exists(LOGO_FILE):
    col_logo, col_title = st.columns([1, 4])

    with col_logo:
        st.image(LOGO_FILE, width=150)

    with col_title:
        st.markdown(
            """
            <div style="padding-top:5px;">
                <h1 style="color:#1f77b4;margin:0;font-size:28px;">
                    🚢 ✈️ (주)범운해운항공 종합 관리 프로그램
                </h1>
                <p style="margin:5px 0 0 0;color:#555;font-size:15px;">
                    Job별 마진 계산, 거래처 관리 및 영세율 인보이스
                    (A4 PDF 저장) 지원
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.markdown(
        """
        <div style="
            background-color:#f0f2f6;
            padding:20px;
            border-radius:10px;
            margin-bottom:20px;
        ">
            <h1 style="color:#1f77b4;margin:0;font-size:28px;">
                🚢 ✈️ (주)범운해운항공 종합 관리 프로그램
            </h1>
            <p style="margin:5px 0 0 0;color:#555;font-size:15px;">
                Job별 마진 계산, 거래처 관리 및 영세율 인보이스
                (A4 PDF 저장) 지원
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()


# ------------------------------------------------------------
# 세션 상태
# ------------------------------------------------------------
if (
    "client_list" not in st.session_state
    or not st.session_state.client_list
):
    c_list, c_rates, c_infos = load_client_data()

    st.session_state.client_list = c_list
    st.session_state.client_rates = c_rates
    st.session_state.client_infos = c_infos
else:
    if "client_rates" not in st.session_state:
        _, c_rates, _ = load_client_data()
        st.session_state.client_rates = c_rates

    if "client_infos" not in st.session_state:
        _, _, c_infos = load_client_data()
        st.session_state.client_infos = c_infos


if "bl_data_list" not in st.session_state:
    st.session_state.bl_data_list = load_bl_data()

if "account_data_list" not in st.session_state:
    st.session_state.account_data_list = load_account_data()

if "expense_data_list" not in st.session_state:
    st.session_state.expense_data_list = load_expense_data()

if "is_editing" not in st.session_state:
    st.session_state.is_editing = False

if "edit_client" not in st.session_state:
    st.session_state.edit_client = ""

if "edit_country" not in st.session_state:
    st.session_state.edit_country = ""

if "edit_item" not in st.session_state:
    st.session_state.edit_item = ""

if "shared_cbm" not in st.session_state:
    st.session_state.shared_cbm = 0.0

if "shared_gw" not in st.session_state:
    st.session_state.shared_gw = 0.0

if "sales_vol_wt" not in st.session_state:
    st.session_state.sales_vol_wt = 0.0

if "purchase_vol_wt" not in st.session_state:
    st.session_state.purchase_vol_wt = 0.0


# ------------------------------------------------------------
# 메뉴
# ------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 수출입 B/L 및 마진 등록",
    "📅 선적 일정표 (Schedule)",
    "🏢 거래처별·국가별·품목별 요금 상세 관리",
    "📈 일계표 및 미수금 관리",
    "💳 회사 경비 및 지출 관리"
])


# ============================================================
# TAB 1
# ============================================================
with tab1:
    st.header("📋 수출입 B/L 및 마진 등록")

    with st.container():
        st.markdown(
            "### 📦 1단계: 화물 규격(cm) 및 실중량(kg) 통합 입력"
        )

        col_in1, col_in2, col_in3, col_in4 = st.columns(4)

        with col_in1:
            common_w_str = st.text_input(
                "가로 (cm)",
                value="",
                placeholder="숫자만 바로 입력",
                key="common_w"
            )

        with col_in2:
            common_l_str = st.text_input(
                "세로 (cm)",
                value="",
                placeholder="숫자만 바로 입력",
                key="common_l"
            )

        with col_in3:
            common_h_str = st.text_input(
                "높이 (cm)",
                value="",
                placeholder="숫자만 바로 입력",
                key="common_h"
            )

        with col_in4:
            common_gw_str = st.text_input(
                "실 중량 (Gross Weight, kg)",
                value="",
                placeholder="숫자만 바로 입력",
                key="common_gw"
            )

        col_div1, col_div2, col_btn = st.columns([1, 1, 2])

        with col_div1:
            s_div = st.selectbox(
                "매출 부피중량 기준",
                [5000, 6000],
                key="s_div"
            )

        with col_div2:
            p_div = st.selectbox(
                "매입 부피중량 기준",
                [6000, 5000],
                key="p_div"
            )

        with col_btn:
            st.markdown(
                "<div style='margin-top:24px;'></div>",
                unsafe_allow_html=True
            )

            if st.button(
                "🚀 한 번에 계산 및 아래 폼에 자동 반영",
                type="primary",
                use_container_width=True
            ):
                try:
                    w = safe_float(common_w_str, 0.0)
                    l = safe_float(common_l_str, 0.0)
                    h = safe_float(common_h_str, 0.0)
                    gw = safe_float(common_gw_str, 0.0)
                except ValueError:
                    w, l, h, gw = 0.0, 0.0, 0.0, 0.0

                if w > 0 and l > 0 and h > 0:
                    st.session_state.shared_cbm = (
                        w * l * h
                    ) / 1000000.0

                    st.session_state.shared_gw = gw

                    st.session_state.sales_vol_wt = (
                        w * l * h
                    ) / s_div

                    st.session_state.purchase_vol_wt = (
                        w * l * h
                    ) / p_div

                    st.success(
                        f"통합 계산 완료! "
                        f"CBM: {st.session_state.shared_cbm:.3f} | "
                        f"실중량: {gw}kg | "
                        f"매출부피중량({s_div}): "
                        f"{st.session_state.sales_vol_wt:.2f}kg | "
                        f"매입부피중량({p_div}): "
                        f"{st.session_state.purchase_vol_wt:.2f}kg"
                    )
                else:
                    st.warning(
                        "가로, 세로, 높이 값을 올바른 숫자로 "
                        "모두 입력해주세요."
                    )

        st.info(
            f"👉 현재 반영된 값 ➔ "
            f"CBM: **{st.session_state.shared_cbm:.3f}** | "
            f"실중량: **{st.session_state.shared_gw} kg** | "
            f"매출 부피중량: "
            f"**{st.session_state.sales_vol_wt:.2f} kg** | "
            f"매입 부피중량: "
            f"**{st.session_state.purchase_vol_wt:.2f} kg**"
        )

    st.divider()

    with st.form("margin_form"):
        st.markdown(
            "### 📋 2단계: 상세 B/L 정보 입력"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            io_type = st.selectbox(
                "수출입 구분",
                ["수출 (Export)", "수입 (Import)"]
            )

            job_no = st.text_input(
                "Job 번호 (예: BW-2026-001)"
            )

            bl_no = st.text_input("B/L 번호")

            dest_country = st.selectbox(
                "출발/도착 국가 (지역)",
                COUNTRY_LIST,
                key="form_dest_country"
            )

            item_desc = st.text_input(
                "품목명 (Description)",
                placeholder="예: 일반공산품, 화장품 등",
                key="form_item_desc"
            )

        with col2:
            reg_date = st.date_input(
                "등록/선적 날짜",
                value=date.today()
            )

            shipper_name = st.selectbox(
                "화주명 (매출처)",
                options=[""] + st.session_state.client_list
            )

            purchase_vendor = st.selectbox(
                "매입처 (항공사/선사/파트너)",
                options=[""] + st.session_state.client_list
            )

            transport_type = st.selectbox(
                "운송 형태",
                ["항공(Air)", "해상(FCL)", "해상(LCL)"]
            )

            gross_weight_sales = st.number_input(
                "매출용 실 중량 (Gross Weight, kg)",
                min_value=0.0,
                step=1.0,
                value=float(st.session_state.shared_gw),
                format="%.2f"
            )

            gross_weight_purchase = st.number_input(
                "매입용 실 중량 (Gross Weight, kg)",
                min_value=0.0,
                step=1.0,
                value=float(st.session_state.shared_gw),
                format="%.2f"
            )

        with col3:
            final_sales_cbm = st.number_input(
                "매출 확정 부피 (CBM)",
                value=float(st.session_state.shared_cbm),
                min_value=0.0,
                step=0.001,
                format="%.3f"
            )

            final_sales_vol_wt = st.number_input(
                "매출 확정 부피중량 (kg)",
                value=float(st.session_state.sales_vol_wt),
                min_value=0.0,
                step=0.01,
                format="%.2f"
            )

            raw_sales_chargeable = max(
                gross_weight_sales,
                final_sales_vol_wt
            )

            default_sales_chargeable = (
                math.ceil(raw_sales_chargeable)
                if raw_sales_chargeable > 0
                else 0
            )

            sales_chargeable_weight = st.number_input(
                "매출 청구 중량 (Chargeable Weight, kg - 올림)",
                value=float(default_sales_chargeable),
                min_value=0.0,
                step=1.0,
                format="%.0f"
            )

            s_base_w, s_base_p, s_add_p = 1.0, 35000, 25000

            if shipper_name in st.session_state.client_rates:
                c_dict = st.session_state.client_rates[shipper_name]

                country_items = c_dict.get(
                    dest_country,
                    c_dict.get("기타 국가", {})
                )

                if item_desc in country_items:
                    r = country_items[item_desc]
                else:
                    r = (
                        list(country_items.values())[0]
                        if country_items
                        else {
                            "기본중량": 1.0,
                            "기본요금": 35000,
                            "추가단가": 25000
                        }
                    )

                s_base_w = safe_float(r.get("기본중량", 1.0), 1.0)
                s_base_p = safe_int(r.get("기본요금", 35000), 35000)
                s_add_p = safe_int(r.get("추가단가", 25000), 25000)

            auto_sales = calculate_tier_price(
                sales_chargeable_weight,
                s_base_w,
                s_base_p,
                s_add_p
            )

            total_sales = st.number_input(
                "총 매출액 (원) [품목별 요율 자동계산]",
                value=auto_sales,
                min_value=0,
                step=10000,
                format="%d"
            )

            st.divider()

            final_purchase_cbm = st.number_input(
                "매입 확정 부피 (CBM)",
                value=float(st.session_state.shared_cbm),
                min_value=0.0,
                step=0.001,
                format="%.3f"
            )

            final_purchase_vol_wt = st.number_input(
                "매입 확정 부피중량 (kg)",
                value=float(st.session_state.purchase_vol_wt),
                min_value=0.0,
                step=0.01,
                format="%.2f"
            )

            raw_purchase_chargeable = max(
                gross_weight_purchase,
                final_purchase_vol_wt
            )

            default_purchase_chargeable = (
                math.ceil(raw_purchase_chargeable)
                if raw_purchase_chargeable > 0
                else 0
            )

            purchase_chargeable_weight = st.number_input(
                "매입 청구 중량 (Chargeable Weight, kg - 올림)",
                value=float(default_purchase_chargeable),
                min_value=0.0,
                step=1.0,
                format="%.0f"
            )

            p_base_w, p_base_p, p_add_p = 1.0, 35000, 25000

            if purchase_vendor in st.session_state.client_rates:
                c_dict = st.session_state.client_rates[purchase_vendor]

                country_items = c_dict.get(
                    dest_country,
                    c_dict.get("기타 국가", {})
                )

                if item_desc in country_items:
                    r = country_items[item_desc]
                else:
                    r = (
                        list(country_items.values())[0]
                        if country_items
                        else {
                            "기본중량": 1.0,
                            "기본요금": 35000,
                            "추가단가": 25000
                        }
                    )

                p_base_w = safe_float(r.get("기본중량", 1.0), 1.0)
                p_base_p = safe_int(r.get("기본요금", 35000), 35000)
                p_add_p = safe_int(r.get("추가단가", 25000), 25000)

            auto_purchase = calculate_tier_price(
                purchase_chargeable_weight,
                p_base_w,
                p_base_p,
                p_add_p
            )

            total_purchase = st.number_input(
                "총 매입액 (원) [품목별 요율 자동계산]",
                value=auto_purchase,
                min_value=0,
                step=10000,
                format="%d"
            )

        remarks = st.text_area(
            "비고 (선사, 품목 등 특이사항)"
        )

        submitted = st.form_submit_button(
            "💾 마진 데이터 및 B/L 최종 등록"
        )

        if submitted:
            if job_no and shipper_name:
                margin = total_sales - total_purchase

                new_entry = {
                    "구분": io_type,
                    "날짜": str(reg_date),
                    "Job 번호": job_no,
                    "B/L 번호": bl_no,
                    "국가": dest_country,
                    "화주명(매출)": shipper_name,
                    "매입처": purchase_vendor,
                    "운송형태": transport_type,
                    "품목": item_desc,
                    "매출실중량(kg)": gross_weight_sales,
                    "매출청구중량(kg)": sales_chargeable_weight,
                    "매출액(원)": total_sales,
                    "매입실중량(kg)": gross_weight_purchase,
                    "매입청구중량(kg)": purchase_chargeable_weight,
                    "매입액(원)": total_purchase,
                    "예상마진(원)": margin,
                    "비고": remarks
                }

                st.session_state.bl_data_list.append(
                    new_entry
                )

                save_bl_data(
                    st.session_state.bl_data_list
                )

                st.success(
                    f"Job [{job_no}] 등록 완료!"
                )
            else:
                st.warning(
                    "Job 번호와 화주명(매출처)은 "
                    "필수 입력 항목입니다."
                )

    st.divider()

    col_h1, col_h2 = st.columns([4, 1])

    with col_h1:
        st.subheader(
            "📊 등록된 수출입 B/L 및 마진 내역"
        )

    with col_h2:
        if st.button("🗑️ 등록 내역 전체 초기화"):
            st.session_state.bl_data_list = []
            save_bl_data([])
            st.rerun()

    if st.session_state.bl_data_list:

        for idx, item in enumerate(
            st.session_state.bl_data_list
        ):
            job_display = item.get(
                "Job 번호",
                ""
            )

            sales_display = safe_int(item.get("매출액(원)", 0), 0)

            margin_display = safe_int(item.get("예상마진(원)", 0), 0)

            with st.expander(
                f"📌 [Job: {job_display}] "
                f"화주: {item.get('화주명(매출)', '')} | "
                f"국가: {item.get('국가', '')} | "
                f"매출: {sales_display:,}원 | "
                f"마진: {margin_display:,}원"
            ):

                # ------------------------------------------------
                # PDF 옵션
                # ------------------------------------------------
                st.markdown(
                    "### 📄 PDF 문서 발행"
                )

                client_name = item.get(
                    "화주명(매출)",
                    ""
                )

                client_info = st.session_state.client_infos.get(
                    client_name,
                    {
                        "사업자등록번호": "-",
                        "이메일": "-",
                        "담당자": "-"
                    }
                )

                opt_col1, opt_col2 = st.columns(2)

                with opt_col1:
                    st.markdown(
                        "#### 🖨️ JOB 마진 정산서"
                    )

                    try:
                        margin_pdf = make_margin_pdf(item)

                        st.download_button(
                            label="📥 마진 정산서 PDF 저장",
                            data=margin_pdf,
                            file_name=(
                                f"JOB_마진정산서_"
                                f"{safe_filename(job_display)}.pdf"
                            ),
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"download_margin_pdf_{idx}"
                        )

                        st.caption(
                            "A4 1장 기준 / 매출·매입·마진 내역 포함"
                        )

                    except Exception as e:
                        st.error(
                            "마진 정산서 PDF 생성 오류: "
                            f"{e}"
                        )

                with opt_col2:
                    st.markdown(
                        "#### 📄 매출 Invoice"
                    )

                    apply_vat = st.checkbox(
                        "부가세(VAT 10%) 추가",
                        key=f"vat_check_{idx}"
                    )

                    invoice_status = st.radio(
                        "계산서 발행 상태",
                        [
                            "계산서 발행 완료 건 (우리은행 계좌 안내)",
                            "계산서 미발행 건 (카카오뱅크 계좌 안내)"
                        ],
                        key=f"invoice_status_radio_{idx}"
                    )

                    try:
                        invoice_pdf = make_invoice_pdf(
                            item,
                            client_info,
                            apply_vat,
                            invoice_status
                        )

                        st.download_button(
                            label="📥 매출 Invoice PDF 저장",
                            data=invoice_pdf,
                            file_name=(
                                f"Invoice_"
                                f"{safe_filename(job_display)}.pdf"
                            ),
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"download_invoice_pdf_{idx}"
                        )

                        if apply_vat:
                            st.caption(
                                "공급가액 + 부가세 10%가 적용됩니다."
                            )
                        else:
                            st.caption(
                                "VAT 0원 / 영세율 적용 표시"
                            )

                    except Exception as e:
                        st.error(
                            "Invoice PDF 생성 오류: "
                            f"{e}"
                        )

                st.divider()

                # ------------------------------------------------
                # 화면 미리보기
                # ------------------------------------------------
                preview_col1, preview_col2 = st.columns(2)

                with preview_col1:
                    if st.button(
                        "👁️ 마진 정산서 화면 미리보기",
                        key=f"preview_margin_{idx}",
                        use_container_width=True
                    ):
                        st.session_state[
                            f"show_margin_preview_{idx}"
                        ] = not st.session_state.get(
                            f"show_margin_preview_{idx}",
                            False
                        )

                with preview_col2:
                    if st.button(
                        "👁️ Invoice 화면 미리보기",
                        key=f"preview_invoice_{idx}",
                        use_container_width=True
                    ):
                        st.session_state[
                            f"show_invoice_preview_{idx}"
                        ] = not st.session_state.get(
                            f"show_invoice_preview_{idx}",
                            False
                        )

                if st.session_state.get(
                    f"show_margin_preview_{idx}",
                    False
                ):
                    s_amt = safe_int(item.get("매출액(원)", 0), 0)
                    p_amt = safe_int(item.get("매입액(원)", 0), 0)
                    m_amt = safe_int(item.get("예상마진(원)", 0), 0)

                    st.markdown(
                        f"""
                        <div style="
                            border:2px solid #333;
                            padding:30px;
                            background:#fff;
                            color:#000;
                        ">
                        <h2 style="text-align:center;">
                            (주)범운해운항공
                        </h2>
                        <h4 style="text-align:center;">
                            BUMWOON OCEAN & AIR., LTD.
                        </h4>
                        <h3 style="text-align:center;">
                            [ JOB 마진 정산서 ]
                        </h3>
                        <hr>
                        <p>
                            <b>Job 번호:</b> {item.get('Job 번호', '')}
                            &nbsp;&nbsp;&nbsp;
                            <b>등록일:</b> {item.get('날짜', '')}
                        </p>
                        <p>
                            <b>B/L 번호:</b> {item.get('B/L 번호', '')}
                            &nbsp;&nbsp;&nbsp;
                            <b>운송형태:</b> {item.get('운송형태', '')}
                        </p>
                        <p>
                            <b>화주:</b> {item.get('화주명(매출)', '')}
                            &nbsp;&nbsp;&nbsp;
                            <b>매입처:</b> {item.get('매입처', '')}
                        </p>
                        <p>
                            <b>국가:</b> {item.get('국가', '')}
                            &nbsp;&nbsp;&nbsp;
                            <b>품목:</b> {item.get('품목', '')}
                        </p>
                        <table style="
                            width:100%;
                            border-collapse:collapse;
                            text-align:center;
                        ">
                            <tr style="background:#f2f2f2;">
                                <th style="border:1px solid #777;padding:8px;">
                                    구분
                                </th>
                                <th style="border:1px solid #777;padding:8px;">
                                    실중량
                                </th>
                                <th style="border:1px solid #777;padding:8px;">
                                    청구중량
                                </th>
                                <th style="border:1px solid #777;padding:8px;">
                                    금액
                                </th>
                            </tr>
                            <tr>
                                <td style="border:1px solid #777;padding:8px;">
                                    매출
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {item.get('매출실중량(kg)', 0)}
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {item.get('매출청구중량(kg)', 0)}
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {s_amt:,}원
                                </td>
                            </tr>
                            <tr>
                                <td style="border:1px solid #777;padding:8px;">
                                    매입
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {item.get('매입실중량(kg)', 0)}
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {item.get('매입청구중량(kg)', 0)}
                                </td>
                                <td style="border:1px solid #777;padding:8px;">
                                    {p_amt:,}원
                                </td>
                            </tr>
                        </table>
                        <h3 style="text-align:right;">
                            예상 수익 마진: {m_amt:,}원
                        </h3>
                        <p>
                            <b>비고:</b>
                            {item.get('비고', '') or '특이사항 없음'}
                        </p>
                        <br>
                        <p style="text-align:center;font-weight:bold;">
                            주식회사 범운해운항공 (직인생략)
                        </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                if st.session_state.get(
                    f"show_invoice_preview_{idx}",
                    False
                ):
                    supply_amount = safe_int(item.get("매출액(원)", 0), 0)

                    vat_amount = (
                        int(supply_amount * 0.1)
                        if apply_vat
                        else 0
                    )

                    grand_total = (
                        supply_amount + vat_amount
                    )

                    if "미발행" in invoice_status:
                        account_preview = (
                            "<b>카카오뱅크:</b> "
                            "3333-12-9553477 "
                            "(예금주: 이상복 / 범운해운항공)<br>"
                            "<b>우리은행:</b> "
                            "1005-704-932716 "
                            "(예금주: 주식회사 범운해운항공)"
                        )
                    else:
                        account_preview = (
                            "<b>우리은행:</b> "
                            "1005-704-932716 "
                            "(예금주: 주식회사 범운해운항공)"
                        )

                    st.markdown(
                        f"""
                        <div style="
                            max-width:900px;
                            margin:auto;
                            border:2px solid #1f77b4;
                            padding:30px;
                            background:#fff;
                            color:#000;
                        ">
                        <h1 style="text-align:center;color:#1f77b4;">
                            INVOICE (청구서)
                        </h1>
                        <h4 style="text-align:center;">
                            (주)범운해운항공 |
                            BUMWOON OCEAN & AIR., LTD.
                        </h4>
                        <hr>

                        <div style="
                            display:flex;
                            gap:20px;
                        ">
                            <div style="width:50%;">
                                <b>[ 공급자 (Supplier) ]</b><br>
                                상호: (주)범운해운항공<br>
                                대표이사: 이상복<br>
                                본사: 경기도 김포시 풍무동 326-5번지 2동<br>
                                1창고: 경기도 김포시 승가로 110-30 가동<br>
                                2창고: 경기도 김포시 승가로 87-47<br>
                                Tel: 031-989-7071<br>
                                Fax: 031-989-7072<br>
                                E-mail: bumwoon11@naver.com
                            </div>

                            <div style="
                                width:50%;
                                background:#f9f9f9;
                                padding:12px;
                            ">
                                <b>[ 공급받는 자 (Client / Bill To) ]</b><br>
                                상호: {client_name}<br>
                                사업자등록번호:
                                {client_info.get('사업자등록번호', '-') or '-'}<br>
                                담당자:
                                {client_info.get('담당자', '-') or '-'}<br>
                                이메일:
                                {client_info.get('이메일', '-') or '-'}
                            </div>
                        </div>

                        <p>
                            <b>Job No. :</b>
                            {item.get('Job 번호', '')}
                        </p>

                        <table style="
                            width:100%;
                            border-collapse:collapse;
                            text-align:center;
                            font-size:13px;
                        ">
                            <tr style="
                                background:#1f77b4;
                                color:white;
                            ">
                                <th style="padding:8px;border:1px solid #999;">
                                    순서
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    날짜
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    B/L No.
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    목적지
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    청구중량
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    품명
                                </th>
                                <th style="padding:8px;border:1px solid #999;">
                                    공급가액
                                </th>
                            </tr>
                            <tr>
                                <td style="padding:8px;border:1px solid #999;">1</td>
                                <td style="padding:8px;border:1px solid #999;">
                                    {item.get('날짜', '')}
                                </td>
                                <td style="padding:8px;border:1px solid #999;">
                                    {item.get('B/L 번호', '')}
                                </td>
                                <td style="padding:8px;border:1px solid #999;">
                                    {item.get('국가', '')}
                                </td>
                                <td style="padding:8px;border:1px solid #999;">
                                    {item.get('매출청구중량(kg)', 0)} kg
                                </td>
                                <td style="padding:8px;border:1px solid #999;">
                                    {item.get('품목', '')}
                                </td>
                                <td style="padding:8px;border:1px solid #999;">
                                    <b>{supply_amount:,} 원</b>
                                </td>
                            </tr>
                        </table>

                        <div style="
                            text-align:right;
                            margin-top:15px;
                            line-height:1.8;
                        ">
                            공급가액:
                            <b>{supply_amount:,} 원</b><br>
                            부가세(VAT):
                            <b>{vat_amount:,} 원</b>
                            {'(부가세 10% 적용)' if apply_vat else '(영세율 적용)'}<br>
                            <h2 style="color:#d9534f;">
                                총 청구금액:
                                {grand_total:,} 원
                            </h2>
                        </div>

                        <div style="
                            background:#fffbe6;
                            padding:12px;
                            margin-top:20px;
                            border:1px solid #ffe58f;
                            line-height:1.7;
                        ">
                            <b>[ 입금 계좌 안내 ]</b><br>
                            {account_preview}
                        </div>

                        <p style="
                            text-align:center;
                            font-weight:bold;
                            margin-top:35px;
                        ">
                            주식회사 범운해운항공 대표이사 이상복
                        </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        st.dataframe(
            pd.DataFrame(st.session_state.bl_data_list),
            use_container_width=True
        )

    else:
        st.info(
            "아직 등록된 B/L 내역이 없습니다."
        )


# ============================================================
# TAB 2
# ============================================================
with tab2:
    st.markdown(
        "### 📅 선적 일정 관리 (Schedule)"
    )

    st.markdown(
        "선적 스케줄 및 선박/항공편 입출항 일정을 관리합니다."
    )

    st.markdown("---")

    initial_schedule_data = [
        {
            "국가": "미국",
            "운행 수단": "에어",
            "운행 요일": "화요일, 토요일",
            "비고": "정기 항공편"
        },
        {
            "국가": "호주",
            "운행 수단": "해운/에어",
            "운행 요일": "토요일, 일요일",
            "비고": "주말 운행"
        },
        {
            "국가": "인도",
            "운행 수단": "에어",
            "운행 요일": "수요일, 토요일",
            "비고": "정기 항공편"
        },
        {
            "국가": "중국",
            "운행 수단": "해운/에어",
            "운행 요일": "매주 화요일, 금요일",
            "비고": "주 2회"
        },
        {
            "국가": "태국",
            "운행 수단": "에어",
            "운행 요일": "월요일 ~ 토요일",
            "비고": "주 6일 운행"
        }
    ]

    if "schedule_df" not in st.session_state:
        st.session_state.schedule_df = pd.DataFrame(
            initial_schedule_data
        )

    st.markdown(
        "#### 🔍 정기 운행 스케줄표 (직접 수정 가능)"
    )

    edited_schedule_df = st.data_editor(
        st.session_state.schedule_df,
        num_rows="dynamic",
        use_container_width=True,
        key="schedule_editor_box"
    )

    if st.button(
        "스케줄 변경사항 저장",
        type="primary"
    ):
        st.session_state.schedule_df = edited_schedule_df
        st.success(
            "선적 일정 스케줄이 성공적으로 저장되었습니다!"
        )


# ============================================================
# TAB 3
# ============================================================
with tab3:
    st.header(
        "🏢 거래처별·국가별·품목별 요금 상세 관리"
    )

    tab3_sub1, tab3_sub2 = st.tabs([
        "➕ 신규 품목별 요율 등록",
        "✏️ 기존 품목 요금 수정 및 삭제"
    ])

    with tab3_sub1:
        st.subheader(
            "신규 거래처 품명별 요율 설정 및 상세 정보 입력"
        )

        c_info1, c_info2, c_info3 = st.columns(3)

        with c_info1:
            new_client_name = st.text_input(
                "거래처명",
                key="reg_client_name"
            )

        with c_info2:
            reg_biz_no = st.text_input(
                "사업자등록번호",
                key="reg_biz_no"
            )

        with c_info3:
            reg_email = st.text_input(
                "이메일 주소",
                key="reg_email"
            )

        c_info4, c_info5, c_info6 = st.columns(3)

        with c_info4:
            reg_manager = st.text_input(
                "담당자 성명",
                key="reg_manager"
            )

        with c_info5:
            target_country = st.selectbox(
                "적용 국가 선택",
                COUNTRY_LIST,
                key="reg_target_country"
            )

        with c_info6:
            target_item = st.text_input(
                "품명",
                value="일반공산품",
                key="reg_target_item"
            )

        c_rate1, c_rate2, c_rate3 = st.columns(3)

        with c_rate1:
            base_weight = st.number_input(
                "기준 중량 (kg)",
                min_value=0.1,
                value=1.0,
                step=0.5,
                key="reg_base_weight"
            )

        with c_rate2:
            base_price = st.number_input(
                "기본 요금 (원)",
                min_value=0,
                value=35000,
                step=1000,
                key="reg_base_price"
            )

        with c_rate3:
            add_price = st.number_input(
                "추가 1kg당 요금 (원)",
                min_value=0,
                value=25000,
                step=1000,
                key="reg_add_price"
            )

        if st.button(
            "해당 품목 요율 및 거래처 정보 등록하기",
            type="primary"
        ):
            if new_client_name and target_item:
                if new_client_name not in st.session_state.client_list:
                    st.session_state.client_list.append(
                        new_client_name
                    )
                    st.session_state.client_rates[
                        new_client_name
                    ] = {}

                st.session_state.client_infos[
                    new_client_name
                ] = {
                    "사업자등록번호": reg_biz_no,
                    "이메일": reg_email,
                    "담당자": reg_manager
                }

                if target_country not in st.session_state.client_rates[
                    new_client_name
                ]:
                    st.session_state.client_rates[
                        new_client_name
                    ][target_country] = {}

                st.session_state.client_rates[
                    new_client_name
                ][target_country][target_item] = {
                    "기본중량": base_weight,
                    "기본요금": base_price,
                    "추가단가": add_price
                }

                save_client_data(
                    st.session_state.client_list,
                    st.session_state.client_rates,
                    st.session_state.client_infos
                )

                st.success(
                    f"[{new_client_name}] 거래처 정보 및 "
                    f"[{target_country} / {target_item}] "
                    "요율이 등록되었습니다!"
                )

                st.rerun()

            else:
                st.warning(
                    "거래처명과 품명은 필수 입력 사항입니다."
                )

    with tab3_sub2:
        st.subheader(
            "기존 품목별 요금 수정 및 삭제"
        )

        if st.session_state.client_list:
            flat_data = []

            for client, c_dict in (
                st.session_state.client_rates.items()
            ):
                for country, item_dict in c_dict.items():
                    if not isinstance(item_dict, dict):
                        continue

                    for item_name, r_val in item_dict.items():
                        flat_data.append({
                            "거래처명": client,
                            "적용 국가": country,
                            "품명": item_name,
                            "기준 중량(kg)": r_val.get(
                                "기본중량", 1.0
                            ),
                            "기본 요금(원)": r_val.get(
                                "기본요금", 35000
                            ),
                            "추가 단가(원/kg)": r_val.get(
                                "추가단가", 25000
                            )
                        })

            st.markdown(
                "#### 📋 전체 품목 요율 목록 및 빠른 관리"
            )

            for i, row_data in enumerate(flat_data):
                col_info1, col_info2, col_info3, col_btn_edit, col_btn_del = st.columns(
                    [2, 1, 2, 1, 1]
                )

                with col_info1:
                    st.markdown(
                        f"**거래처:** {row_data['거래처명']}"
                    )

                with col_info2:
                    st.markdown(
                        f"**국가:** {row_data['적용 국가']}"
                    )

                with col_info3:
                    st.markdown(
                        f"**품명:** {row_data['품명']}"
                    )

                with col_btn_edit:
                    if st.button(
                        "수정 선택",
                        key=f"select_row_{i}"
                    ):
                        st.session_state.is_editing = True
                        st.session_state.edit_client = (
                            row_data["거래처명"]
                        )
                        st.session_state.edit_country = (
                            row_data["적용 국가"]
                        )
                        st.session_state.edit_item = (
                            row_data["품명"]
                        )
                        st.rerun()

                with col_btn_del:
                    if st.button(
                        "🗑️ 삭제",
                        key=f"delete_row_{i}"
                    ):
                        c_name = row_data["거래처명"]
                        co_name = row_data["적용 국가"]
                        i_name = row_data["품명"]

                        if (
                            c_name in st.session_state.client_rates
                            and co_name in st.session_state.client_rates[c_name]
                        ):
                            if (
                                i_name
                                in st.session_state.client_rates[
                                    c_name
                                ][co_name]
                            ):
                                del st.session_state.client_rates[
                                    c_name
                                ][co_name][i_name]

                        save_client_data(
                            st.session_state.client_list,
                            st.session_state.client_rates,
                            st.session_state.client_infos
                        )

                        st.success(
                            f"[{c_name} / {co_name} / {i_name}] "
                            "품목이 삭제되었습니다."
                        )

                        st.rerun()

            st.divider()

            if st.session_state.is_editing:
                c_name = st.session_state.edit_client
                co_name = st.session_state.edit_country
                i_name = st.session_state.edit_item

                current_r = (
                    st.session_state.client_rates
                    .get(c_name, {})
                    .get(co_name, {})
                    .get(
                        i_name,
                        {
                            "기본중량": 1.0,
                            "기본요금": 35000,
                            "추가단가": 25000
                        }
                    )
                )

                c1, c2 = st.columns(2)

                with c1:
                    e_base_w = st.number_input(
                        "기준 중량 (kg)",
                        min_value=0.1,
                        value=safe_float(
                            current_r.get(
                                "기본중량", 1.0
                            ),
                            1.0
                        ),
                        step=0.5,
                        key="edit_base_w"
                    )

                with c2:
                    e_base_p = st.number_input(
                        "기본 요금 (원)",
                        min_value=0,
                        value=safe_int(
                            current_r.get(
                                "기본요금", 35000
                            ),
                            35000
                        ),
                        step=1000,
                        key="edit_base_p"
                    )

                e_add_p = st.number_input(
                    "추가 1kg당 요금 (원)",
                    min_value=0,
                    value=safe_int(
                        current_r.get(
                            "추가단가", 25000
                        ),
                        25000
                    ),
                    step=1000,
                    key="edit_add_p"
                )

                col_btn1, col_btn2 = st.columns(2)

                with col_btn1:
                    if st.button(
                        "💾 수정 내용 저장 반영",
                        type="primary",
                        use_container_width=True
                    ):
                        if c_name not in st.session_state.client_rates:
                            st.session_state.client_rates[c_name] = {}

                        if co_name not in st.session_state.client_rates[c_name]:
                            st.session_state.client_rates[c_name][co_name] = {}

                        st.session_state.client_rates[
                            c_name
                        ][co_name][i_name] = {
                            "기본중량": e_base_w,
                            "기본요금": e_base_p,
                            "추가단가": e_add_p
                        }

                        save_client_data(
                            st.session_state.client_list,
                            st.session_state.client_rates,
                            st.session_state.client_infos
                        )

                        st.success("수정 완료!")
                        st.session_state.is_editing = False
                        st.rerun()

                with col_btn2:
                    if st.button(
                        "❌ 수정 취소",
                        use_container_width=True
                    ):
                        st.session_state.is_editing = False
                        st.rerun()


# ============================================================
# TAB 4
# ============================================================
with tab4:
    st.header("📈 일계표 및 미수금 관리")

    st.markdown(
        "등록된 B/L 매출/매입 내역을 바탕으로 "
        "일일 매출·매입 현황과 거래처별 미수금을 관리합니다."
    )

    st.divider()

    st.subheader(
        "📅 날짜별 일계표 (매출 / 매입 / 순이익 현황)"
    )

    if st.session_state.bl_data_list:
        df_acc = pd.DataFrame(
            st.session_state.bl_data_list
        )

        for _col in ["매출액(원)", "매입액(원)", "예상마진(원)"]:
            if _col not in df_acc.columns:
                df_acc[_col] = 0
            df_acc[_col] = pd.to_numeric(df_acc[_col], errors="coerce").fillna(0)
        if "날짜" not in df_acc.columns:
            df_acc["날짜"] = ""
        if "Job 번호" not in df_acc.columns:
            df_acc["Job 번호"] = ""

        daily_summary = (
            df_acc.groupby("날짜")
            .agg(
                총매출액=("매출액(원)", "sum"),
                총매입액=("매입액(원)", "sum"),
                총마진=("예상마진(원)", "sum"),
                건수=("Job 번호", "count")
            )
            .reset_index()
            .sort_values(
                by="날짜",
                ascending=False
            )
        )

        st.dataframe(
            daily_summary,
            use_container_width=True
        )

    else:
        st.info(
            "등록된 B/L 내역이 없어 일계표를 표시할 수 없습니다."
        )

    st.divider()

    st.subheader(
        "🏢 거래처별 미수금(청구 대비 입금) 관리"
    )

    if st.session_state.bl_data_list:
        df_bl_ledger = pd.DataFrame(
            st.session_state.bl_data_list
        )

        client_sales = (
            df_bl_ledger
            .groupby("화주명(매출)")["매출액(원)"]
            .sum()
            .reset_index()
        )

        client_sales.columns = [
            "거래처명",
            "총청구금액"
        ]

        account_df = pd.DataFrame(
            st.session_state.account_data_list
        )

        if "입금액(원)" in account_df.columns:
            account_df["입금액(원)"] = pd.to_numeric(account_df["입금액(원)"], errors="coerce").fillna(0)

        if (
            not account_df.empty
            and "거래처명" in account_df.columns
            and "입금액(원)" in account_df.columns
        ):
            client_received = (
                account_df
                .groupby("거래처명")["입금액(원)"]
                .sum()
                .reset_index()
            )
        else:
            client_received = pd.DataFrame(
                columns=[
                    "거래처명",
                    "입금액(원)"
                ]
            )

        ledger_merged = pd.merge(
            client_sales,
            client_received,
            on="거래처명",
            how="left"
        ).fillna(0)

        ledger_merged["미수금잔액(원)"] = (
            ledger_merged["총청구금액"]
            - ledger_merged["입금액(원)"]
        )

        st.markdown(
            "#### 📋 거래처별 미수금 현황 요약"
        )

        st.dataframe(
            ledger_merged,
            use_container_width=True
        )

        st.markdown(
            "#### 💰 입금(수금) 내역 직접 등록"
        )

        active_clients = st.session_state.get(
            "client_list",
            []
        )

        if not active_clients:
            active_clients = [
                "(주)홍길동상사",
                "ABC로지스틱스",
                "글로벌쉬핑",
                "글루오필메디앤코",
                "카스항운"
            ]

        with st.form("deposit_form"):
            col_d1, col_d2, col_d3 = st.columns(3)

            with col_d1:
                dep_client = st.selectbox(
                    "거래처 선택",
                    options=active_clients
                )

            with col_d2:
                dep_amount = st.number_input(
                    "입금된 금액 (원)",
                    min_value=0,
                    step=10000,
                    format="%d"
                )

            with col_d3:
                dep_date = st.date_input(
                    "입금일자",
                    value=date.today()
                )

            dep_memo = st.text_input(
                "입금 관련 메모"
            )

            submitted_dep = st.form_submit_button(
                "💳 수금/입금 내역 반영하기"
            )

            if submitted_dep:
                if dep_client and dep_amount > 0:
                    new_dep = {
                        "날짜": str(dep_date),
                        "거래처명": dep_client,
                        "입금액(원)": dep_amount,
                        "메모": dep_memo
                    }

                    st.session_state.account_data_list.append(
                        new_dep
                    )

                    save_account_data(
                        st.session_state.account_data_list
                    )

                    st.success(
                        f"[{dep_client}] 거래처의 입금액 "
                        f"{dep_amount:,}원이 정상 반영되었습니다!"
                    )

                    st.rerun()

                else:
                    st.warning(
                        "거래처를 선택하고 0원 초과의 "
                        "입금액을 입력해주세요."
                    )

        if st.session_state.account_data_list:
            st.markdown(
                "#### 📜 상세 입금 내역 리스트"
            )

            st.dataframe(
                pd.DataFrame(
                    st.session_state.account_data_list
                ),
                use_container_width=True
            )

            if st.button(
                "🗑️ 입금 내역 전체 초기화"
            ):
                st.session_state.account_data_list = []
                save_account_data([])
                st.rerun()

    else:
        st.info(
            "거래처별 미수금을 계산할 B/L 매출 데이터가 없습니다."
        )


# ============================================================
# TAB 5
# ============================================================
with tab5:
    st.header(
        "💳 회사 경비 및 지출 관리"
    )

    st.markdown(
        "주유비, 식대, 접대비 및 각종 기타 잡비 "
        "지출 내역을 등록하고 관리합니다."
    )

    st.divider()

    with st.form("expense_form"):
        st.markdown(
            "### ✍️ 지출 경비 직접 등록"
        )

        ex_col1, ex_col2, ex_col3 = st.columns(3)

        with ex_col1:
            ex_date = st.date_input(
                "지출 일자",
                value=date.today(),
                key="ex_date"
            )

        with ex_col2:
            ex_category = st.selectbox(
                "비용 항목 (계정과목)",
                EXPENSE_CATEGORIES,
                key="ex_category"
            )

        with ex_col3:
            ex_amount = st.number_input(
                "지출 금액 (원)",
                min_value=0,
                step=1000,
                format="%d",
                key="ex_amount"
            )

        ex_col4, ex_col5 = st.columns(2)

        with ex_col4:
            ex_pay_method = st.selectbox(
                "결제 수단",
                [
                    "법인카드",
                    "현금",
                    "계좌이체",
                    "개인카드 (사후정산)"
                ],
                key="ex_pay_method"
            )

        with ex_col5:
            ex_vendor = st.text_input(
                "거래처 / 사용처",
                placeholder="어디서 사용하셨나요?",
                key="ex_vendor"
            )

        ex_memo = st.text_area(
            "지출 상세 메모",
            key="ex_memo"
        )

        submitted_ex = st.form_submit_button(
            "💾 지출 경비 등록하기",
            type="primary"
        )

        if submitted_ex:
            if ex_amount > 0:
                new_expense = {
                    "날짜": str(ex_date),
                    "항목": ex_category,
                    "금액(원)": ex_amount,
                    "결제수단": ex_pay_method,
                    "사용처": ex_vendor,
                    "메모": ex_memo
                }

                st.session_state.expense_data_list.append(
                    new_expense
                )

                save_expense_data(
                    st.session_state.expense_data_list
                )

                st.success(
                    f"[{ex_category}] 지출 금액 "
                    f"{ex_amount:,}원이 정상 등록되었습니다!"
                )

                st.rerun()

            else:
                st.warning(
                    "0원 초과의 지출 금액을 입력해주세요."
                )

    st.divider()

    st.subheader(
        "📊 항목별 경비 지출 요약"
    )

    if st.session_state.expense_data_list:
        df_exp = pd.DataFrame(
            st.session_state.expense_data_list
        )

        if "금액(원)" not in df_exp.columns:
            df_exp["금액(원)"] = 0
        df_exp["금액(원)"] = pd.to_numeric(df_exp["금액(원)"], errors="coerce").fillna(0)
        if "항목" not in df_exp.columns:
            df_exp["항목"] = "기타 잡비"

        exp_summary = (
            df_exp.groupby("항목")["금액(원)"]
            .agg(["count", "sum"])
            .reset_index()
        )

        exp_summary.columns = [
            "비용 항목",
            "지출 건수",
            "총 지출액(원)"
        ]

        st.dataframe(
            exp_summary,
            use_container_width=True
        )

        st.markdown(
            "#### 📜 상세 지출 경비 내역 리스트"
        )

        st.dataframe(
            df_exp,
            use_container_width=True
        )

        if st.button(
            "🗑️ 경비 내역 전체 초기화"
        ):
            st.session_state.expense_data_list = []
            save_expense_data([])
            st.rerun()

    else:
        st.info(
            "아직 등록된 경비 지출 내역이 없습니다."
        )
