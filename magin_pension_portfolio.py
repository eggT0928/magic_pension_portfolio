import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="김성일 마법의 연금굴리기 포트폴리오",
    page_icon="💰",
    layout="wide"
)

# 포트폴리오 구성 정보
PORTFOLIO_CONFIG = {
    "위험자산": {
        "선진국": {
            "KRX:379800": {"name": "KODEX 미국 S&P500TR", "weight": 0.24, "group": "선진국", "is_new": False},
            "KRX:360200": {"name": "ACE 미국 S&P500TR", "weight": 0.24, "group": "선진국", "is_new": True},  # 신규 매수용
        },
        "신흥국": {
            "KRX:294400": {"name": "KOSEF 200TR", "weight": 0.08, "group": "신흥국", "is_new": False},
            "KRX:283580": {"name": "KODEX 차이나CSI300", "weight": 0.08, "group": "신흥국", "is_new": False},
            "KRX:453810": {"name": "KODEX 인도 NIFTY50", "weight": 0.08, "group": "신흥국", "is_new": False},
        }
    },
    "대체 투자": {
        "KRX:0072R0": {"name": "TIGER KRX금현물", "weight": 0.19, "group": "금", "is_new": True},  # 신규 매수용
        "KRX:411060": {"name": "ACE KRX금현물", "weight": 0.19, "group": "금", "is_new": False},
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

# 티커를 yfinance 형식으로 변환 (KRX:379800 -> 379800.KS)
def convert_ticker_to_yfinance(ticker):
    """KRX 티커를 yfinance 형식으로 변환"""
    if ticker.startswith("KRX:"):
        ticker_num = ticker.replace("KRX:", "")
        # 특수 문자 제거 (예: 0072R0 -> 0072R0, 숫자만 있는 경우 그대로)
        # yfinance는 보통 6자리 숫자.KS 형식을 사용하지만, 일부는 다른 형식일 수 있음
        return f"{ticker_num}.KS"
    return ticker

# yfinance 티커를 원래 형식으로 변환
def convert_yfinance_to_ticker(yf_ticker):
    """yfinance 티커를 원래 형식으로 변환"""
    if yf_ticker.endswith(".KS"):
        ticker_num = yf_ticker.replace(".KS", "")
        return f"KRX:{ticker_num}"
    return yf_ticker

# 현재 가격 조회
def get_current_prices(tickers):
    """현재 가격 조회 (장중 가격 우선)"""
    prices = {}
    for ticker in tickers:
        price = None
        yf_ticker = convert_ticker_to_yfinance(ticker)
        
        try:
            t = yf.Ticker(yf_ticker)
            # 1) 장중 가격(fast_info) 우선 조회
            try:
                price = t.fast_info.get("last_price")
            except:
                pass
            
            # 2) fast_info 실패 시 history 사용 (최근 종가)
            if price is None or price == 0:
                hist = t.history(period="1d")
                if not hist.empty:
                    price = hist["Close"].iloc[-1]
        except Exception as e:
            st.warning(f"{ticker} 가격 조회 실패: {e}")
        
        prices[ticker] = price
    return prices

# 포트폴리오 데이터 구조화
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

# 세션 상태 초기화
if 'holdings' not in st.session_state:
    st.session_state.holdings = {ticker: 0 for ticker in ALL_TICKERS}

if 'total_balance' not in st.session_state:
    st.session_state.total_balance = 0

if 'principal' not in st.session_state:
    st.session_state.principal = 0

if 'adjustable_weights' not in st.session_state:
    # 기본 비중 설정
    st.session_state.adjustable_weights = {}
    for ticker, info in PORTFOLIO_FLAT.items():
        st.session_state.adjustable_weights[ticker] = info['weight']

# 메인 타이틀
st.title("💰 김성일 마법의 연금굴리기 포트폴리오 관리")
st.markdown("---")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 총 자산 입력
    total_balance_input = st.number_input(
        "총 자산 (평가금 + 예수금)",
        min_value=0,
        value=int(st.session_state.total_balance) if st.session_state.total_balance > 0 else 0,
        step=10000,
        format="%d"
    )
    
    # 원금 입력
    principal_input = st.number_input(
        "원금 (초기 투자금)",
        min_value=0,
        value=int(st.session_state.principal) if st.session_state.principal > 0 else int(total_balance_input),
        step=10000,
        format="%d"
    )
    
    if st.button("💰 가격 조회 및 계산", type="primary", use_container_width=True):
        st.session_state.total_balance = total_balance_input
        st.session_state.principal = principal_input
        st.rerun()
    
    st.markdown("---")
    st.subheader("📊 보유 수량 관리")
    
    # 보유 수량 입력
    for ticker in ALL_TICKERS:
        info = PORTFOLIO_FLAT[ticker]
        current_holding = st.session_state.holdings.get(ticker, 0)
        new_holding = st.number_input(
            f"{info['name']}",
            min_value=0,
            value=int(current_holding),
            step=1,
            key=f"holding_{ticker}"
        )
        st.session_state.holdings[ticker] = new_holding
    
    if st.button("💾 보유 수량 저장", use_container_width=True):
        st.success("보유 수량이 저장되었습니다!")
    
    st.markdown("---")
    st.subheader("🔄 비중 조절")
    
    # 비중 조절 가능한 비율 설정
    weight_groups = {}
    for ticker, info in PORTFOLIO_FLAT.items():
        group = info['group']
        if group not in weight_groups:
            weight_groups[group] = []
        weight_groups[group].append(ticker)
    
    # 그룹별 총 비중 표시 및 조절
    for group, tickers in weight_groups.items():
        if len(tickers) > 1:
            # 그룹 내 합산 비중
            group_total_weight = sum(st.session_state.adjustable_weights.get(t, PORTFOLIO_FLAT[t]['weight']) for t in tickers)
            st.text_input(
                f"{group} 총 비중",
                value=f"{group_total_weight*100:.0f}%",
                disabled=True,
                key=f"group_total_{group}"
            )
            
            # 그룹 내 각 티커의 비중 조절 (합이 그룹 총 비중이 되도록)
            for ticker in tickers:
                info = PORTFOLIO_FLAT[ticker]
                current_weight = st.session_state.adjustable_weights.get(ticker, info['weight'])
                new_weight = st.slider(
                    f"{info['name']}",
                    min_value=0.0,
                    max_value=group_total_weight,
                    value=float(current_weight),
                    step=0.01,
                    format="%.2f%%",
                    key=f"weight_{ticker}"
                )
                st.session_state.adjustable_weights[ticker] = new_weight
        else:
            # 단일 티커인 경우
            ticker = tickers[0]
            info = PORTFOLIO_FLAT[ticker]
            current_weight = st.session_state.adjustable_weights.get(ticker, info['weight'])
            new_weight = st.slider(
                f"{info['name']}",
                min_value=0.0,
                max_value=1.0,
                value=float(current_weight),
                step=0.01,
                format="%.2f%%",
                key=f"weight_{ticker}"
            )
            st.session_state.adjustable_weights[ticker] = new_weight

# 메인 영역
if st.session_state.total_balance > 0:
    total_balance = st.session_state.total_balance
    
    # 가격 조회
    with st.spinner("현재 가격을 조회하는 중..."):
        prices = get_current_prices(ALL_TICKERS)
    
    # 포트폴리오 계산
    portfolio_data = []
    
    for ticker in ALL_TICKERS:
        info = PORTFOLIO_FLAT[ticker]
        price = prices.get(ticker)
        current_holding = st.session_state.holdings.get(ticker, 0)
        target_weight = st.session_state.adjustable_weights.get(ticker, info['weight'])
        
        if price and price > 0:
            target_value = total_balance * target_weight
            calculated_quantity = target_value / price
            current_value = current_holding * price
        else:
            target_value = total_balance * target_weight
            calculated_quantity = 0
            current_value = 0
        
        portfolio_data.append({
            "구분": info['group'],
            "티커": ticker,
            "상품": info['name'],
            "비중 조절 가능": f"{target_weight*100:.0f}%",
            "총자산 분배": f"₩ {target_value:,.0f}",
            "현재가(실시간)": f"₩ {price:,.0f}" if price else "N/A",
            "계산된 수량": f"{calculated_quantity:.2f}" if calculated_quantity > 0 else "0.00",
            "보유 수량": current_holding,
            "현재 평가액": f"₩ {current_value:,.0f}",
        })
    
    df_portfolio = pd.DataFrame(portfolio_data)
    
    # 구매 수량 입력 섹션
    st.subheader("📝 구매 수량 입력")
    
    purchase_data = []
    total_purchase_amount = 0
    
    for ticker in ALL_TICKERS:
        info = PORTFOLIO_FLAT[ticker]
        price = prices.get(ticker)
        
        if price and price > 0:
            target_weight = st.session_state.adjustable_weights.get(ticker, info['weight'])
            target_value = total_balance * target_weight
            calculated_quantity = target_value / price
            
            # 구매 수량 입력
            col1, col2 = st.columns([3, 1])
            with col1:
                purchase_quantity = st.number_input(
                    f"{info['name']} - 계산된 수량: {calculated_quantity:.2f}",
                    min_value=0,
                    value=int(calculated_quantity),
                    step=1,
                    key=f"purchase_{ticker}"
                )
            
            with col2:
                actual_purchase_amount = purchase_quantity * price
                total_purchase_amount += actual_purchase_amount
                actual_purchase_ratio = (actual_purchase_amount / total_balance * 100) if total_balance > 0 else 0
                st.metric("구매금액", f"₩ {actual_purchase_amount:,.0f}")
            
            purchase_data.append({
                "티커": ticker,
                "상품": info['name'],
                "계산된 수량": f"{calculated_quantity:.2f}",
                "구매할 수량 입력": purchase_quantity,
                "실구매 금액": f"₩ {actual_purchase_amount:,.0f}",
                "실구매 비율": f"{actual_purchase_ratio:.2f}%",
            })
    
    st.markdown("---")
    
    # 요약 정보
    st.subheader("📊 요약 정보")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("총 자산", f"₩ {total_balance:,.0f}")
        st.metric("총 구매 금액", f"₩ {total_purchase_amount:,.0f}")
    
    with col2:
        total_current_value = sum([
            st.session_state.holdings.get(ticker, 0) * prices.get(ticker, 0)
            for ticker in ALL_TICKERS
        ])
        st.metric("현재 평가액 합계", f"₩ {total_current_value:,.0f}")
        st.metric("실구매 비율 합계", f"{total_purchase_amount / total_balance * 100:.2f}%")
    
    with col3:
        principal = st.session_state.principal if st.session_state.principal > 0 else total_balance
        profit = total_current_value - principal
        profit_rate = (profit / principal * 100) if principal > 0 else 0
        st.metric("원금", f"₩ {principal:,.0f}")
        st.metric("수익금", f"₩ {profit:,.0f}")
        st.metric("수익률", f"{profit_rate:.2f}%")
    
    st.markdown("---")
    
    # 리밸런싱 계산
    st.subheader("🔄 리밸런싱 계산")
    
    rebalancing_data = []
    total_rebalance_amount = 0
    
    for ticker in ALL_TICKERS:
        info = PORTFOLIO_FLAT[ticker]
        price = prices.get(ticker)
        current_holding = st.session_state.holdings.get(ticker, 0)
        
        # 구매 수량 가져오기 (위에서 입력한 값)
        purchase_quantity_key = f"purchase_{ticker}"
        purchase_quantity = 0
        if purchase_quantity_key in st.session_state:
            purchase_quantity = st.session_state[purchase_quantity_key]
        else:
            # 기본값으로 계산된 수량 사용
            if price and price > 0:
                target_weight = st.session_state.adjustable_weights.get(ticker, PORTFOLIO_FLAT[ticker]['weight'])
                target_value = total_balance * target_weight
                purchase_quantity = int(target_value / price)
        
        if price and price > 0:
            # 리밸런싱 필요 수량 = 구매할 수량 - 현재 보유 수량
            rebalance_quantity = purchase_quantity - current_holding
            rebalance_amount = abs(rebalance_quantity * price)
            
            if rebalance_quantity > 0:
                total_rebalance_amount += rebalance_amount
                action = f"+{rebalance_quantity:.0f} (매수)"
                amount_str = f"₩ {rebalance_amount:,.0f}"
            elif rebalance_quantity < 0:
                action = f"{rebalance_quantity:.0f} (매도)"
                amount_str = f"₩ {rebalance_amount:,.0f}"
            else:
                action = "0 (유지)"
                amount_str = "₩ 0"
            
            rebalancing_data.append({
                "티커": ticker,
                "상품": info['name'],
                "현재 보유": current_holding,
                "목표 보유": purchase_quantity,
                "리밸런싱": action,
                "구매금액": amount_str,
            })
    
    df_rebalancing = pd.DataFrame(rebalancing_data)
    st.dataframe(df_rebalancing, use_container_width=True, hide_index=True)
    
    st.metric("구매금액 합계", f"₩ {total_rebalance_amount:,.0f}")
    
    st.markdown("---")
    
    # 포트폴리오 테이블 표시
    st.subheader("📈 포트폴리오 현황")
    st.dataframe(df_portfolio, use_container_width=True, hide_index=True)
    
    # 구매 데이터 테이블
    if purchase_data:
        st.subheader("💵 구매 계획")
        df_purchase = pd.DataFrame(purchase_data)
        st.dataframe(df_purchase, use_container_width=True, hide_index=True)
    
else:
    st.info("👈 왼쪽 사이드바에서 총 자산을 입력하고 '가격 조회 및 계산' 버튼을 클릭하세요.")
    
    # 초기 안내
    st.markdown("""
    ### 사용 방법
    
    1. **총 자산 입력**: 왼쪽 사이드바에서 평가금 + 예수금을 입력하세요.
    2. **보유 수량 입력**: 현재 보유하고 있는 각 종목의 수량을 입력하세요.
    3. **가격 조회**: '가격 조회 및 계산' 버튼을 클릭하여 현재 가격을 조회합니다.
    4. **구매 수량 입력**: 계산된 수량을 참고하여 실제 구매할 수량을 입력하세요.
    5. **리밸런싱 확인**: 리밸런싱 섹션에서 매수/매도 필요 수량을 확인하세요.
    
    ### 포트폴리오 구성
    
    - **위험자산 (67%)**: 선진국 24% (KODEX + ACE S&P500), 신흥국 8%씩 3개
    - **대체 투자 (19%)**: 금 (TIGER + ACE 금)
    - **안전자산 (33%)**: 한국 국채 14%, 미국 국채 7%씩 2개
    - **현금성 자산 (5%)**: TIGER KOFR금리액티브
    
    ### 참고사항
    
    - S&P500 신규 매수는 ACE로 진행 (보수 낮음)
    - 금 신규 매수는 TIGER로 진행 (보수 낮음)
    - 보유 수량은 세션 상태에 저장되며, 페이지를 새로고침하면 초기화됩니다.
    """)

