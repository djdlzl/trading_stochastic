#  눌림목 트레이딩 시스템

## 프로젝트 개요
이 프로젝트는 한국 주식 시장의 상한가 종목을 자동으로 분석하고 거래하는 알고리즘 트레이딩 시스템입니다.

## 주요 기능
- 상한가 종목 실시간 스크리닝
- 자동 종목 선택 및 거래 로직
- 다중 세션 트레이딩 지원
- RDBMS 기반 데이터 관리

## 기술 스택
- Python
- APScheduler (스케줄링)
- MySQL Connector
- Logging

## 주요 모듈
- `database/`: 데이터베이스 연결 및 데이터 관리
- `trading/`: 트레이딩 로직 및 세션 관리
- `config/`: 설정 및 조건 관리
- `process/`: 스케줄러 관리

## 시스템 워크플로우
1. 상한가 종목 데이터 수집
2. 종목 선택 알고리즘 실행
3. 자동 거래 세션 시작
4. 거래 결과 데이터베이스 저장

## 라이센스
Private Project

## 주의사항
- 실제 투자에 사용하기 전 충분한 테스트 필요
- 금융 리스크에 대한 책임은 사용자에게 있음