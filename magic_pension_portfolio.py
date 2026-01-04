import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="김성일 마법의 연금굴리기 포트폴리오",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 사이드바 완전히 숨기기 (CSS)
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        .stApp > header {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# 포트폴리오 구성 정보
PORTFOLIO_CONFIG = {
    "위험자산": {
        "선진국": {
            "KRX:379800": {"name": "KODEX 미국 S&P500TR(보수 0.0062%)", "weight": 0.24, "group": "선진국", "is_new": False},
        },
        "신흥국": {
            "KRX:294400": {"name": "KOSEF 200TR", "weight": 0.08, "group": "신흥국", "is_new": False},
            "KRX:283580": {"name": "KODEX 차이나CSI300", "weight": 0.08, "group": "신흥국", "is_new": False},
            "KRX:453810": {"name": "KODEX 인도 NIFTY50", "weight": 0.08, "group": "신흥국", "is_new": False},
        }
    },
    "대체 투자": {
        "KRX:411060": {"name": "ACE KRX금현물(보수 0.19%)", "weight": 0.19, "group": "금", "is_new": False},
    },
    "안전자산": {
        "한국 국채": {
            "KRX:385560": {"name": "RISE KIS 국고채30년 Enhanced", "weight": 0.14, "group": "한국 국채", "is_new": False},
        },
        "미국 국채": {
            "KRX:308620": {"name": "KODEX 미국채 10년선물", "weight": 0.07, "group": "미국 국채", "is_new": False},
            "KRX:453850": {"name": "ACE 미국30년 국채액티브(H)", "weight": 0.07, "group": "미국 국채", "is_new": False},
        }
    },
    "현금성 자산": {
        "KRX:449170": {"name": "TIGER KOFR금리액티브(합성)", "weight": 0.05, "group": "현금성 자산", "is_new": False},
    }
}

# 그룹 합산 비중 로직 제거 - 모든 종목을 개별 비중으로 처리
GROUP_SUM_GROUPS = []

# 모든 티커 리스트 추출
def get_all_tickers():
    """모든 티커 리스트 반환"""
    tickers = []
    for category in PORTFOLIO_CONFIG.values():
        if isinstance(category, dict):
            for key, value in category.items():
                if isinstance(value, dict) and "name" in value:
                    tickers.append(key)
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, dict) and "name" in sub_value:
                            tickers.append(sub_key)
    return tickers

ALL_TICKERS = get_all_tickers()

# 포트폴리오 데이터 구조화 (평면 구조)
def get_portfolio_flat():
    """포트폴리오를 평면 구조로 변환"""
    portfolio_flat = {}
    for category, items in PORTFOLIO_CONFIG.items():
        if isinstance(items, dict):
            for key, value in items.items():
                if isinstance(value, dict) and "name" in value:
                    portfolio_flat[key] = value
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, dict) and "name" in sub_value:
                            portfolio_flat[sub_key] = sub_value
    return portfolio_flat

PORTFOLIO_FLAT = get_portfolio_flat()

# 그룹별 티커 리스트 생성
def get_group_tickers():
    """그룹별 티커 리스트 반환"""
    groups = {}
    for ticker, info in PORTFOLIO_FLAT.items():
        group = info['group']
        if group not in groups:
            groups[group] = []
        groups[group].append(ticker)
    return groups

# 티커를 yfinance 형식으로 변환
def convert_ticker_to_yfinance(ticker):
    """KRX 티커를 yfinance 형식으로 변환"""
    if ticker.startswith("KRX:"):
        ticker_num = ticker.replace("KRX:", "")
        return f"{ticker_num}.KS"
    return ticker

# 현재 가격 조회
def get_current_prices(tickers):
    """현재 가격 조회"""
    prices = {}
    for ticker in tickers:
        price = None
        yf_ticker = convert_ticker_to_yfinance(ticker)
        
        try:
            t = yf.Ticker(yf_ticker)
            try:
                price = t.fast_info.get("last_price")
            except:
                pass
            
            if price is None or price == 0:
                hist = t.history(period="1d")
                if not hist.empty:
                    price = hist["Close"].iloc[-1]
        except Exception as e:
            st.warning(f"{ticker} 가격 조회 실패: {e}")
        
        prices[ticker] = price if price and price > 0 else 0
    return prices

# 세션 상태 초기화
if 'holdings' not in st.session_state:
    st.session_state.holdings = {ticker: 0 for ticker in ALL_TICKERS}

if 'total_balance' not in st.session_state:
    st.session_state.total_balance = 0

if 'principal' not in st.session_state:
    st.session_state.principal = 0

if 'adjustable_weights' not in st.session_state:
    st.session_state.adjustable_weights = {}

# 모든 티커의 비중이 설정되어 있는지 확인하고, 없으면 기본값으로 설정
for ticker, info in PORTFOLIO_FLAT.items():
    if ticker not in st.session_state.adjustable_weights:
        st.session_state.adjustable_weights[ticker] = info['weight']

if 'purchase_quantities' not in st.session_state:
    st.session_state.purchase_quantities = {ticker: 0 for ticker in ALL_TICKERS}

# 상단 경고 배너
st.markdown("""
    <div style="background-color: #FFE066; padding: 10px; border-radius: 5px; margin-bottom: 20px; text-align: center;">
        <strong>김성일 작가님 최신버전 참고 → [마법의 연금 굴리기 전면개정판 필독]</strong>
    </div>
""", unsafe_allow_html=True)

# 메인 타이틀
st.title("💰 김성일 마법의 연금굴리기 포트폴리오 관리")
st.markdown("---")

# 상단 설정
col1, col2, col3, col4 = st.columns(4)
with col1:
    total_balance_input = st.number_input(
        "총 자산 (평가금 + 예수금)",
        min_value=0,
        value=int(st.session_state.total_balance) if st.session_state.total_balance > 0 else 0,
        step=10000,
        format="%d",
        key="total_balance_input"
    )
    st.session_state.total_balance = total_balance_input

with col2:
    principal_input = st.number_input(
        "원금 (초기 투자금)",
        min_value=0,
        value=int(st.session_state.principal) if st.session_state.principal > 0 else int(total_balance_input),
        step=10000,
        format="%d",
        key="principal_input"
    )
    st.session_state.principal = principal_input

with col3:
    if st.button("💰 가격 조회", type="primary", width='stretch'):
        st.rerun()

with col4:
    if st.button("💾 저장", width='stretch'):
        st.success("데이터가 저장되었습니다!")

st.markdown("---")

# 메인 영역
if st.session_state.total_balance > 0:
    total_balance = st.session_state.total_balance
    
    # 가격 조회
    with st.spinner("현재 가격을 조회하는 중..."):
        prices = get_current_prices(ALL_TICKERS)
    
    # 그룹별 티커 리스트
    group_tickers = get_group_tickers()
    
    # 테이블 데이터 생성 (모든 종목을 개별 비중으로 처리)
    table_data = []
    
    for ticker in ALL_TICKERS:
        info = PORTFOLIO_FLAT[ticker]
        price = prices.get(ticker, 0)
        current_holding = st.session_state.holdings.get(ticker, 0)
        group = info['group']
        
        # 비중 계산 - 각 종목의 조정된 weight 사용
        weight_value = st.session_state.adjustable_weights.get(ticker, info['weight'])
        
        # 총자산 분배 계산 - 모든 종목을 개별 비중으로 처리
        # 총자산 분배 = 총자산 × 비중
        target_value = total_balance * weight_value if total_balance > 0 and weight_value > 0 else 0
        
        # 계산된 수량
        calculated_quantity = target_value / price if price > 0 else 0
        
        # 구매 수량 (기본값은 계산된 수량)
        purchase_quantity = st.session_state.purchase_quantities.get(ticker, int(calculated_quantity) if calculated_quantity > 0 else 0)
        
        # 실구매 금액 및 비율
        actual_purchase_amount = purchase_quantity * price if price > 0 else 0
        actual_purchase_ratio = (actual_purchase_amount / total_balance * 100) if total_balance > 0 else 0
        
        # 리밸런싱 계산
        rebalance_quantity = purchase_quantity - current_holding
        if rebalance_quantity == 0:
            rebalance_text = f"0 {ticker}" # 스프레드시트 형식에 맞춤 (0 KRX:379800)
        else:
            rebalance_text = f"{rebalance_quantity:.0f}" # 스프레드시트 형식에 맞춤 (+158, -4)
        
        # 비중 표시 (퍼센트로)
        weight_display = weight_value * 100
        
        table_data.append({
            "구분": info['group'],
            "티커": ticker,
            "상품": info['name'],
            "비중 조절 가능": weight_display,
            "총자산 분배": target_value,
            "현재가(실시간)": price,
            "계산된 수량": calculated_quantity,
            "구매할 수량 입력": int(calculated_quantity) if calculated_quantity > 0 else 0, # 구매 수량은 정수
            "실구매 금액": actual_purchase_amount,
            "실구매 비율": actual_purchase_ratio,
            "보유 수량": current_holding,
            "리밸런싱": rebalance_text,
            "구매금액": actual_purchase_amount, # 실구매 금액을 구매금액에 할당
            "구매금액 합계": 0, # 최종 합계는 요약에서 계산
        })
    
    df_table = pd.DataFrame(table_data)
    
    # 편집 가능한 테이블 생성
    st.subheader("📊 포트폴리오 관리 테이블")
    
    # 총자산 분배 합계 계산 및 표시
    total_allocation = sum([row['총자산 분배'] for row in table_data])
    st.markdown(f"""
        <div style="background-color: #FF69B4; color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px; text-align: center;">
            <strong>총자산 분배 합계: ₩ {total_allocation:,.0f}</strong>
        </div>
    """, unsafe_allow_html=True)
    
    st.info("""
    💡 **자산 배분 안내**:
    - 모든 종목은 개별 비중으로 계산됩니다.
    - 각 종목의 비중을 조절하여 전체 비중이 100%가 되도록 관리하세요.
    """)
    
    # 컬럼 설정
    column_config = {
        "구분": st.column_config.TextColumn("구분", disabled=True),
        "티커": st.column_config.TextColumn("티커", disabled=True),
        "상품": st.column_config.TextColumn("상품", disabled=True),
        "비중 조절 가능": st.column_config.NumberColumn(
            "비중 조절 가능 (%)",
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            format="%.1f",
            help="각 종목의 비중을 조절할 수 있습니다. 전체 비중이 100%가 되도록 관리하세요."
        ),
        "총자산 분배": st.column_config.NumberColumn("총자산 분배 (원)", format="%d", disabled=True),
        "현재가(실시간)": st.column_config.NumberColumn("현재가 (원)", format="%d", disabled=True),
        "계산된 수량": st.column_config.NumberColumn("계산된 수량", format="%.2f", disabled=True),
        "구매할 수량 입력": st.column_config.NumberColumn(
            "구매할 수량 입력",
            min_value=0,
            step=1,
            format="%d"
        ),
        "총자산 분배": st.column_config.NumberColumn("총자산 분배 (원)", format="%d", disabled=True),
        "현재가(실시간)": st.column_config.NumberColumn("현재가 (원)", format="%d", disabled=True),
        "계산된 수량": st.column_config.NumberColumn("계산된 수량", format="%.2f", disabled=True),
        "구매할 수량 입력": st.column_config.NumberColumn(
            "구매할 수량 입력",
            min_value=0,
            step=1,
            format="%d"
        ),
        "실구매 금액": st.column_config.NumberColumn("실구매 금액 (원)", format="%d", disabled=True),
        "실구매 비율": st.column_config.NumberColumn("실구매 비율 (%)", format="%.2f", disabled=True),
        "보유 수량": st.column_config.NumberColumn(
            "보유 수량",
            min_value=0,
            step=1,
            format="%d"
        ),
        "리밸런싱": st.column_config.TextColumn("리밸런싱 + 개수만큼 매수/-개수만큼 매도", disabled=True),
        "구매금액": st.column_config.NumberColumn("구매금액 (원)", format="%d", disabled=True),
        "구매금액 합계": st.column_config.NumberColumn("구매금액 합계 (원)", format="%d", disabled=True),
    }
    
    # 편집된 데이터 가져오기
    edited_df = st.data_editor(
        df_table,
        column_config=column_config,
        width='stretch',
        hide_index=True,
        num_rows="fixed",
        key="portfolio_editor"
    )
    
    # 편집된 데이터를 세션 상태에 저장
    for idx, row in edited_df.iterrows():
        ticker = row['티커']
        info = PORTFOLIO_FLAT[ticker]
        
        # 비중 업데이트 - 모든 종목을 개별 비중으로 처리
        new_weight = row['비중 조절 가능'] / 100.0
        st.session_state.adjustable_weights[ticker] = new_weight
        
        # 보유 수량 업데이트
        st.session_state.holdings[ticker] = int(row['보유 수량'])
        
        # 구매 수량 업데이트
        st.session_state.purchase_quantities[ticker] = int(row['구매할 수량 입력'])
    
    st.markdown("---")
    
    # 요약 정보
    st.subheader("📊 요약 정보")
    
    # 총자산 분배 합계 (목표 배분 금액 합계)
    total_allocation_sum = sum([row['총자산 분배'] for row in table_data])
    
    # 현재 평가액 합계 (실제 보유 평가액)
    total_current_value = sum([
        st.session_state.holdings.get(ticker, 0) * prices.get(ticker, 0)
        for ticker in ALL_TICKERS
        if prices.get(ticker, 0) and prices.get(ticker, 0) > 0
    ])
    
    # 수익 계산
    principal = st.session_state.principal if st.session_state.principal > 0 else total_balance
    profit = total_current_value - principal
    profit_rate = (profit / principal * 100) if principal > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("원금", f"₩ {principal:,.0f}")
    with col2:
        st.metric("현재", f"₩ {total_allocation_sum:,.0f}") # 스프레드시트처럼 총자산 분배 합계를 "현재"로 표시
    with col3:
        st.metric("수익금", f"₩ {profit:,.0f}")
    with col4:
        st.metric("수익률", f"{profit_rate:.2f}%")
    

else:
    st.info("👈 위에서 총 자산을 입력하고 '가격 조회' 버튼을 클릭하세요.")
    
    st.markdown("""
    ### 사용 방법
    
    1. **총 자산 입력**: 위에서 평가금 + 예수금을 입력하세요.
    2. **원금 입력**: 초기 투자금을 입력하세요.
    3. **가격 조회**: '가격 조회' 버튼을 클릭하여 현재 가격을 조회합니다.
    4. **테이블에서 직접 입력**: 
       - **비중 조절 가능**: 각 종목의 비중을 조절합니다 (전체 비중이 100%가 되도록 관리)
       - **구매할 수량 입력**: 실제 구매할 수량을 입력합니다
       - **보유 수량**: 현재 보유 수량을 입력합니다
    5. **자동 계산**: 입력하면 즉시 계산이 반영됩니다.
    
    ### 포트폴리오 구성
    
    - **위험자산 (48%)**: 선진국 24% (KODEX S&P500), 신흥국 8%씩 3개 (한국, 중국, 인도)
    - **대체 투자 (19%)**: 금 19% (ACE KRX금현물)
    - **안전자산 (28%)**: 한국 국채 14%, 미국 국채 7%씩 2개 (10년물, 30년 액티브)
    - **현금성 자산 (5%)**: TIGER KOFR금리액티브 5%
    
    **총 비중: 24 + 24 + 19 + 14 + 14 + 5 = 100%**
    """)
