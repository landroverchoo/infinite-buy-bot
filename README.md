# 라오어 무한매수법 V3.0 자동매매 봇

라오어의 무한매수법 V3.0 전략을 구현한 Python 프로그램입니다. 백테스트, 시뮬레이션, 웹 UI, 그리고 (향후) 한국투자증권/키움증권 API를 통한 자동매매를 지원합니다.

## 무한매수법 V3.0이란?

- **분할 매수**: 총 투자금을 20, 30, 40등분 (20은 고위험)
- **T 값**: 매수누적액 / 1회매수액 (소수점 둘째 자리 올림)
- **별%**: 매수/매도 기준 (TQQQ: 15-1.5T, SOXL: 20-2T)
- **매수**:
  - 전반전(T<10): 1회매수액 절반은 별% LOC, 절반은 0% LOC
  - 후반전(T≥10): 전액 별% LOC
- **매도**: 목표 수익률(기본 5%) 도달 시 전량 매도
- **수익 반영**: 수익 절반은 40분할해 1회매수금 증가 (반복리), 절반은 손절 대비 저장
- **사이클 반복**: 매도 후 새 투자금으로 1회차부터 재시작

## 설치

```bash
pip install -r requirements.txt
```

## 사용법

### 1. 백테스트

```bash
python main.py backtest --config config.yaml --plot
```

- yfinance로 과거 데이터를 가져와 전략 시뮬레이션
- 매매 기록, 성과 지표(수익률, 최대 낙폭 등), 차트 출력

### 2. 주문 표 생성

```bash
python main.py table --start-price 100.0 --price-step -1.0
```

- 가상 가격 시나리오로 회차별 매수/매도 표 생성

### 3. 실시간 자동매매 (TODO)

```bash
python main.py run --config config.yaml
```

- 한투/키움 API 연동 필요 (미구현)

## 설정 (config.yaml)

```yaml
strategy:
  divisions: 40          # 20 또는 40
  total_investment: 10000000  # 총 투자금 (원)
  target_profit_pct: 5.0     # 목표 수익률 %
  use_loc: true              # LOC 주문 사용 여부
  loc_discount_pct: 1.0      # LOC 할인율 %

ticker: "TQQQ"               # 종목 코드
broker: "kis"                # kis 또는 kiwoom

backtest:
  start_date: "2024-01-01"
  end_date: "2024-12-31"
```

## 프로젝트 구조

```
infinite-buy-bot/
├── README.md
├── requirements.txt
├── config.yaml           # 설정
├── src/
│   ├── strategy.py       # 무한매수법 로직
│   ├── simulator.py      # 백테스트 & 시뮬레이션
│   ├── order_table.py    # 주문 표 생성
│   └── broker/
│       ├── base.py       # 증권사 추상 클래스
│       ├── kis.py        # 한투 (TODO)
│       └── kiwoom.py     # 키움 (TODO)
├── tests/
│   └── test_strategy.py  # 테스트
└── main.py               # CLI
```

## TODO

- 한투 OpenAPI 연동
- 키움 Open API+ 연동 (Windows 전용)
- 실시간 매매 로직

## 주의

- 실제 매매 전 반드시 모의 투자로 테스트하세요.
- 투자 손실 책임은 사용자에게 있습니다.

## 라이선스

MIT
