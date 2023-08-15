
#! 1. 모듈 선언
#! 2. 글로벌 변수 선언
#! 3. Main Program
#! 4. Streamlit UI

###############################################################!
######################! 1. 모듈 선언 ###############################
import streamlit as st
import requests
import json
import datetime
import time
import yaml
import threading
import queue
import pandas as pd
from customPackge.send_message import send_message#!디스코드 메시지 전송 함수
from customPackge.get_access_token import get_access_token #!주식 api 토큰 생성
from customPackge.stock_sell import stock_sell #!주식 매도
from customPackge.stock_buy import stock_buy #!주식 매수
from customPackge.hashkey import hashkey #! 해쉬키 변환(암호화)
from customPackge.get_stock_current_price import get_stock_current_price #!선택한 주식 현재가
from customPackge.get_balance import get_balance #! 현금 잔고조회
from customPackge.get_stock_balance import get_stock_balance #! 주식 잔고조회


#################################################################!
########################! 2. 글로벌 변수 선언 ###########################
global APP_KEY,APP_SECRET,ACCESS_TOKEN,CANO,ACNT_PRDT_CD,DISCORD_WEBHOOK_URL,URL_BASE,bot_thread,symbol_list
with open('config.yaml', encoding='UTF-8') as f:
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
APP_KEY = _cfg['APP_KEY']
APP_SECRET = _cfg['APP_SECRET']
ACCESS_TOKEN = ""
CANO = _cfg['CANO']
ACNT_PRDT_CD = _cfg['ACNT_PRDT_CD']
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']
URL_BASE = _cfg['URL_BASE']

    

def get_target_price(code="005930"):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"FHKST01010400"}
    params = {
    "fid_cond_mrkt_div_code":"J",
    "fid_input_iscd":code,
    "fid_org_adj_prc":"1",
    "fid_period_div_code":"D"
    }
    res = requests.get(URL, headers=headers, params=params)
    stck_oprc = int(res.json()['output'][0]['stck_oprc']) #오늘 시가
    stck_hgpr = int(res.json()['output'][1]['stck_hgpr']) #전일 고가
    stck_lwpr = int(res.json()['output'][1]['stck_lwpr']) #전일 저가
    target_price = stck_oprc + (stck_hgpr - stck_lwpr) * 0.5
    return target_price


##############################################################!
####################! 3. Main Program ###########################
# 기존 코드를 함수로 만듭니다.
def stock_trading_bot(stop_event,q):
    # 자동매매 시작
    try:    
        # send_message("===국내 주식 자동매매 프로그램을 시작합니다===")
        while True:
            #! 타겟팅하는 list
            try:
                symbol_list = q.get(block=False) # Queue에서 값을 가져옴
            except queue.Empty:
                pass # Queue가 비어있는 경우, 다음 작업으로 넘어감
            print(symbol_list)
            
            time.sleep(1)
            if stop_event.is_set():
                break

    except Exception as e:
        # send_message(f"[오류 발생2]{e}")
        time.sleep(1)


############################################################################!
#######################! 4. Streamlit UI ######################################
#! 값 초기화
if "stop_auto_trading" not in st.session_state:
    st.session_state["stop_auto_trading"] = threading.Event()
    st.session_state["symbol_list"] = ["005930","035720","000660","069500"] #!종목코드리스트
    st.session_state["symbol_list_queue"] = queue.Queue() #!쓰레드 전달 큐 생성
    st.session_state["symbol_list_queue"].put(st.session_state["symbol_list"]) #! 쓰레드 전달 큐 종목코드리스트 업데이트


#! 타이틀, 아이콘
st.set_page_config(
    page_title="Auto trading bot",
    page_icon = "📈"
)
#! 사이드바 생성
st.sidebar.success("Select a demo above.")
#! 메인헤더 생성
st.title("볼알클럽")    


#! 서브헤더 프로그램 상태 (st 전역)
execution_state = st.empty()
execution_state.subheader("프로그램 상태 : 중지")

#! 프로그램 시작, 정지 버튼 그룹
container = st.container()
col1, col2 = st.columns([1, 1])
with container:
    with col1:
        if st.button("시작"):
            execution_state.subheader("프로그램 상태 : 실행 중")
            # ACCESS_TOKEN = get_access_token() #!토큰 발급
            st.session_state["stop_auto_trading"].clear() #!쓰레드에 false값 전달
            st.session_state["thread"] = threading.Thread(target=stock_trading_bot, args=(st.session_state.stop_auto_trading,st.session_state["symbol_list_queue"])) #!
            st.session_state["thread"].start() #! 메인 프로그램 시작
    with col2:
        if st.button("중지"):
            execution_state.subheader("프로그램 상태 : 중지") 
            st.session_state["stop_auto_trading"].set() #!쓰레드에 True값 전달


st.write('-' * 50)
st.markdown("""
    <style>
        .symbol_title{
            width:100%;
            margin-top:20px;
        }
        .stButton > button{
            width:100%;
            height:100%;
        }
    </style>            
    <h4 class="symbol_title">현재 타겟팅 주식 종목코드</h4>
""", unsafe_allow_html=True)

#! 타겟팅 주식 리스트
tasks_df = pd.DataFrame(columns=['종목코드']) #!테이블 생성
tasks_df = pd.concat([tasks_df, pd.DataFrame(st.session_state["symbol_list"], columns=['종목코드'])], ignore_index=True)

#! 새로운 task 추가 (input + button)
table_container = st.container()
table_col1, table_col2 = st.columns([3, 1])
with table_container:
    with table_col1:
        task = st.text_input('')
    with table_col2:
        if st.button("추가",key='add_stock_button'):
            if task:#! 입력값 유무
                if task not in st.session_state["symbol_list"]: #! 중복 방지
                    new_task = {"종목코드": task}
                    tasks_df = tasks_df.append(new_task, ignore_index=True)  #! 종목코드리스트 데이터 업데이트
                    st.session_state["symbol_list"].append(task)  #! 종목코드리스트 데이터 상태 업데이트
                    st.session_state["symbol_list_queue"].put(st.session_state["symbol_list"])  #! 쓰레드 전달 큐 종목코드리스트 데이터 업데이트
        if st.button("삭제"):
            if task:#! 입력값 유무
                if task in st.session_state["symbol_list"]: #! 입력값이 있으면 삭제
                    # 종목코드가 입력된 경우 삭제 작업 실행
                    tasks_df = tasks_df[tasks_df["종목코드"] != task]  #! 종목코드리스트 데이터 프레임에서 입력한 종목코드를 제거
                    st.session_state["symbol_list"].remove(task)  #! 종목코드리스트 데이터 상태에서 입력한 종목코드를 제거
                    st.session_state["symbol_list_queue"].put(st.session_state["symbol_list"])  #! 쓰레드 전달 큐 종목코드리스트 데이터 업데이트

#! 테이블 생성
if not tasks_df.empty:
    st.write(tasks_df)
else:
    st.write("아직 등록된 task가 없습니다.")


    # symbol_list = ["005930","035720","000660","069500"]






