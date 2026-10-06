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
    page_title="(주)범운해운항공 종합 관리 프로그램",
    layout="wide"
)

# [보안 및 계정 파일 저장 시스템]
ACCOUNT_USER_FILE = "system_user_accounts.csv"

# 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 로그인 화면 함수
def render_login():
    st.markdown("## 🔐 (주)범운해운항공 로그인")
    with st.form("login_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submit = st.form_submit_button("로그인")
        
        if submit:
            # 관리자 또는 기본 계정 검증 (필요에 따라 수정 가능)
            if username == "admin" and password == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

# 메인 대시보드 화면 함수 (안전한 예외 처리 적용)
def render_main_dashboard():
    try:
        st.title("📦 (주)범운해운항공 종합 관리 시스템")
        st.success("로그인되었습니다. 정상적으로 시스템에 접속했습니다.")
        
        # 로그아웃 버튼
        if st.sidebar.button("로그아웃"):
            st.session_state.logged_in = False
            st.rerun()
            
        # 여기에 기존에 작성해 두신 메인 기능 코드가 안전하게 실행됩니다.
        st.markdown("---")
        st.info("좌측 메뉴 또는 기능을 선택하여 업무를 진행해 주세요.")
        
    except Exception as e:
        st.error(f"화면을 불러오는 중 오류가 발생했습니다: {e}")

# 라우팅 처리
if not st.session_state.logged_in:
    render_login()
else:
    render_main_dashboard()
