# Coin Context · 코인 분석 AI 비서

업비트 원화 시장의 완료 일봉을 저장하고, 서버에서 계산한 통계·기술지표를 근거로 AI와 대화하는 웹 서비스입니다.

## 서비스 주소

| 구분 | 주소 |
| --- | --- |
| 웹 서비스 | [Coin Context](https://m1-2-frontend-topaz.vercel.app/) |
| API 상태 | [Render /health](https://m1-2-j9ok.onrender.com/health) |
| API 문서 | [Swagger](https://m1-2-j9ok.onrender.com/docs) |
| 데이터 요약 | [비트코인 요약 JSON](https://m1-2-j9ok.onrender.com/api/data/summary?market=KRW-BTC) |
| 소스 코드 | [leeds86/m1-2](https://github.com/leeds86/m1-2) |

웹 서비스는 위 운영 주소로 접속합니다. 백엔드는 API 전용이며 `/health`, `/docs`, `/api/...` 경로를 제공합니다. Render 인스턴스가 유휴 상태였다면 첫 요청에 시간이 걸릴 수 있습니다.

## 주요 기능

- 원화 시장 코인 검색·선택 및 완료 일봉 최대 200개 수집
- 일봉 데이터 추가·조회·수정·삭제와 메모 관리
- 기간·개수·평균·최고·최저·최근 종가와 최근 흐름 요약
- 볼린저 밴드, RSI, MACD, 거래량 비율 계산
- 계산된 요약을 문맥으로 사용하는 AI 대화
- 대화 자동 저장, 기록 조회·불러오기·삭제
- 데스크톱과 모바일에 대응하는 화면

## 사용 방법

1. [웹 서비스](https://m1-2-frontend-topaz.vercel.app/)에서 분석할 종목을 선택합니다.
2. **일봉 데이터 수집**으로 해당 종목의 완료 일봉을 가져옵니다. **새로고침**은 이미 저장된 데이터를 다시 읽습니다.
3. 분석 화면에서 통계와 기술지표를 확인하고 AI에게 질문합니다.
4. **데이터 관리**에서 일봉과 메모를 추가·수정·삭제합니다. 변경 결과는 요약에 반영됩니다.
5. **대화 기록**에서 저장된 대화를 불러옵니다. 기록은 동일한 브라우저 식별자를 기준으로 조회됩니다.

표시 가격은 마지막으로 수집한 완료 일봉의 종가입니다. 실시간 시세가 아니며, 최신 완료 일봉이 필요하면 다시 수집합니다. 재수집은 기존 기록과 메모를 덮어쓰지 않습니다.

## 구성

```text
Vercel · HTML / CSS / JavaScript
    ↓ HTTPS API
Render · FastAPI / Pydantic
    ├─ Upbit · 원화 시장 종목 및 완료 일봉
    ├─ Cloud Firestore · data / conversations
    └─ Codyssey · OpenAI 호환 Chat Completions
```

| 경로 | 역할 |
| --- | --- |
| `backend/app/routers/` | 데이터·대화·채팅 HTTP API |
| `backend/app/services/` | 기술지표·요약·AI 문맥·대화 처리 |
| `backend/app/repositories.py` | 저장소 입출력 |
| `backend/app/providers.py` | 업비트 및 AI 제공자 호출 |
| `backend/app/schemas.py` | 요청·응답 검증 |
| `backend/tests/` | 계산·API·저장소·외부 호출 계약 테스트 |
| `frontend/` | 반응형 화면 및 API 클라이언트 |
| `frontend/build.mjs` | 공개 API 주소를 포함한 배포 파일 생성 |

요약 API와 AI 채팅은 같은 `summarize()` 함수를 사용합니다. 서버가 지표를 계산하고 AI는 결과를 설명합니다.

## 데이터와 계산 기준

Firestore의 `data/{market}_{date}`에 종목, UTC 일봉 시작일, 종가(`value`), 시가·고가·저가·거래량, 메모, 출처와 생성·수정 시간을 저장합니다.

| 항목 | 계산 기준 |
| --- | --- |
| 일봉 | 진행 중인 UTC 일봉 제외. UTC 00:00은 한국 시간 09:00 |
| 볼린저 밴드 | 종가 SMA20 ± 모집단 표준편차 × 2 |
| RSI | 가격 변화 14개의 평균으로 초기화한 Wilder RSI14 |
| MACD | SMA로 초기화한 EMA12 − EMA26, 시그널 EMA9 |
| 거래량 비율 | 최신 거래량 ÷ 이전 20개 평균. 최신 일봉은 비교 평균에서 제외 |
| 최근 흐름 | 최근 7개와 직전 7개 종가 평균 비교. ±1% 안이면 유지 |

거래 없는 날짜는 보간하지 않습니다. 계산 준비 구간이 부족한 값은 `null`로 반환하며, 날짜 공백과 데이터 부족을 화면에 안내합니다.

`conversations/{uuid}`에는 종목, 제목, 메시지, 메시지 수, 브라우저 식별자와 생성·수정 시간을 저장합니다. 정상 완성된 AI 응답만 사용자·AI 메시지 쌍으로 저장하며, 이어지는 대화는 트랜잭션으로 갱신합니다.

## API

전체 스키마는 [Swagger](https://m1-2-j9ok.onrender.com/docs)에서 확인할 수 있습니다.

| 메서드 | 경로 | 기능 |
| --- | --- | --- |
| GET | `/health` | 서버 상태와 설정 여부 |
| GET | `/api/markets` | 원화 시장 종목 목록 |
| POST | `/api/data/import` | 완료 일봉 수집 |
| GET / POST | `/api/data` | 데이터 목록 / 추가 |
| PUT / DELETE | `/api/data/{id}` | 데이터 수정 / 삭제 |
| GET | `/api/data/summary` | 종목별 통계와 기술지표 |
| POST | `/api/chat` | 요약 주입 → AI 응답 → 대화 자동 저장 |
| GET / POST | `/api/conversations` | 대화 목록 / 명시적 저장 |
| GET / DELETE | `/api/conversations/{id}` | 대화 불러오기 / 삭제 |

데이터 조회는 `?market=KRW-BTC`처럼 종목을 지정합니다. 대화·채팅 요청은 UUID 형식의 `X-Client-Id`가 필요하며 웹 화면에서 자동으로 관리합니다.

## 입력 검증과 운영

- Pydantic으로 가격·거래량·OHLC 관계·완료 날짜·종목 코드·입력 길이를 검증합니다.
- 잘못된 입력은 422, 중복·갱신 충돌은 409, 없는 기록은 404입니다. 외부 오류는 키나 원문 예외를 노출하지 않고 안내합니다.
- 외부 문자열은 `textContent`로 출력합니다. API 키와 Firebase 서비스 계정은 백엔드 환경변수에서만 사용합니다.
- CORS는 운영 프론트 주소를 명시적으로 허용합니다. 브라우저 식별자와 CORS는 로그인 인증을 대신하지 않습니다.
- AI 요청은 40초 제한과 자동 재시도 0회를 사용합니다. 한 대화는 최대 60개 메시지이며 요청 횟수 제한을 적용합니다.
- 기술지표는 과거 데이터의 관찰값이며 AI 설명은 수익이나 매매 결과를 보장하지 않습니다.

[배포 구성](docs/setup.md) · [서비스 결과](docs/submission.md) · [검증 결과](docs/verification.md)
