# Coin Context · 코인 분석 AI 비서

선택한 코인의 완료 일봉을 저장하고, 서버에서 계산한 기술지표와 통계에 근거해 AI와 대화하는 웹 서비스입니다. 업비트 원화 시장에서 종목을 선택하고 일봉 최대 200개를 수집합니다.

미션 필수 기능인 데이터 CRUD, 요약 API, 문맥을 주입하는 AI 채팅, 대화 저장·불러오기, Swagger, 반응형 화면을 구현합니다. 백테스트·주문·자동매매·다운로드·다크 모드·차트 등 보너스 기능은 구현 범위에서 제외했습니다.

## 실행 상태와 링크

| 구분 | 주소 / 상태 |
| --- | --- |
| GitHub 저장소 | https://github.com/leeds86/m1-2 |
| 로컬 프론트 | http://127.0.0.1:5500 |
| 로컬 백엔드 | http://127.0.0.1:8000 |
| 로컬 Swagger | http://127.0.0.1:8000/docs |
| 공개 프론트 | 계정 설정과 Vercel 배포 후 `docs/submission.md`에 기록 |
| 공개 백엔드 / Swagger | Firebase·OpenAI 설정과 Render 배포 후 `docs/submission.md`에 기록 |

2026-10-24 검증에서 실제 Firestore에 BTC 일봉 200개를 저장하고 Codyssey AI 응답·대화 저장·불러오기를 확인했습니다. **제출 환경은 Firestore가 필수**이며 SQLite는 개발용입니다. 이 결과는 로컬 앱과 실제 외부 서비스의 연결 검증으로, 공개 Render/Vercel 배포 검증과는 구분합니다. AI 응답을 만들어서 대신 표시하지 않습니다.

계정은 있지만 설정이 필요하다면 [계정 연결 안내](docs/setup.md)의 순서대로 진행하세요.

## 기술과 구조

- Python 3.10+ / FastAPI / Pydantic / Uvicorn
- Firebase Admin SDK / Cloud Firestore (`data`, `conversations`)
- OpenAI Python SDK / Codyssey OpenAI 호환 Chat Completions (`gpt-5.4-mini`)
- HTML / CSS / JavaScript. 프론트 프레임워크·런타임 패키지 없음
- Render 백엔드 / Vercel 정적 프론트

```text
backend/
  app/
    main.py              앱 구성, CORS, 오류 응답, health
    config.py            환경변수 읽기
    schemas.py           요청·응답 Pydantic 모델
    dependencies.py      저장소·브라우저 식별자 주입
    repositories.py      Firestore / 개발용 SQLite 저장 어댑터
    providers.py         업비트 HTTP / OpenAI SDK 호출
    limiter.py           요청 횟수 제한
    routers/             데이터·대화·채팅 HTTP API
    services/            기술지표·요약·대화·채팅 처리
  tests/                 지표 단위 / API 통합 테스트
  scripts/import_data.py 실데이터 수집·초기 적재
frontend/
  index.html             의미 있는 HTML 구조, 입력·삭제 확인창
  styles.css             데스크톱 / 모바일 레이아웃
  app.js                 화면 상태, API 호출, 안전한 DOM 출력
  config.js              로컬 공개 API 주소
  build.mjs              API_BASE_URL로 배포 설정 생성
scripts/                 Windows 실행 도우미
docs/                    계정 설정 / 평가 시연 / 검증 / 제출 안내
```

HTTP 라우터는 요청 검증과 상태코드, 서비스는 분석·대화 로직, 저장 어댑터는 문서 입출력을 담당합니다. 요약 endpoint와 AI 채팅은 같은 `summarize()` 함수를 호출합니다. 서버가 자기 HTTP API를 다시 호출하지 않아 네트워크 비용 없이 책임 분리와 재사용을 유지합니다.

## 로컬 실행

프로젝트 루트에서 PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
```

`.env`는 로컬용으로 준비돼 있습니다. 새 checkout에서는 `.env.example`을 `.env`로 복사하고 값을 채웁니다. Git은 `.env`, 개인키, 로컬 DB를 제외합니다.

첫 번째 터미널:

```powershell
.\scripts\start-backend.ps1 -LocalStorage
```

두 번째 터미널:

```powershell
.\scripts\start-frontend.ps1
```

브라우저에서 `http://127.0.0.1:5500`을 열고 **일봉 데이터 수집**을 누릅니다. 별도 업비트 API 키는 필요 없습니다. SQLite 데이터는 `.local/coins.sqlite3`에 남습니다. AI 채팅에는 유효한 `OPENAI_API_KEY`가 필요합니다.

PowerShell 스크립트 실행이 제한된 경우 실행 정책을 바꾸지 않고 다음 명령을 직접 사용합니다.

```powershell
$env:STORAGE_BACKEND='sqlite'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```powershell
.\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1 --directory frontend
```

Firestore로 전환할 때는 `STORAGE_BACKEND=firestore`와 서비스 계정을 설정하고, `-LocalStorage` 없이 새 터미널에서 백엔드를 시작합니다. `-LocalStorage`로 실행한 프로세스 환경은 `.env`보다 우선합니다. 데이터는 저장소 사이에 자동 복사되지 않으므로 Firestore 모드에서 다시 수집하세요.

## 환경변수

| 이름 | 위치 | 값 / 역할 |
| --- | --- | --- |
| `STORAGE_BACKEND` | 백엔드 | 기본 `firestore`; 로컬 검증만 `sqlite` |
| `OPENAI_API_KEY` | 백엔드 | 사용자 본인의 Codyssey 가상 API 키. 프론트에 노출 금지 |
| `OPENAI_MODEL` | 백엔드 | `gpt-5.4-mini`; 키 발급 플랫폼의 사용 가능 모델 ID |
| `OPENAI_BASE_URL` | 백엔드 | Codyssey 키는 `https://copa.codyssey.kr/v1`. 미설정 시 공식 OpenAI 주소이므로 발급 플랫폼과 일치시켜야 함 |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | 백엔드 | Render에서 서비스 계정 JSON 전체를 저장 |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | 백엔드 | 로컬에서 JSON 파일의 절대 경로. JSON 변수와 둘 다 있으면 JSON 우선 |
| `ALLOWED_ORIGINS` | 백엔드 | 쉼표로 구분한 프론트 origin. 경로 없이 scheme·host·port 포함 |
| `SQLITE_PATH` | 로컬 백엔드, 선택 | 개발용 DB 경로; 기본 `.local/coins.sqlite3` |
| `API_BASE_URL` | Vercel 빌드 | 공개 Render origin. 예: `https://서비스이름.onrender.com` |

Vercel은 루트 `.env`를 업로드해 읽는 방식이 아닙니다. 프로젝트 환경변수에 `API_BASE_URL`을 따로 설정해야 합니다. `build.mjs`는 이 공개 주소만 `dist/config.js`에 넣습니다. OpenAI·Firebase 키는 프론트 설정에 넣지 않습니다.

## 데이터와 계산 기준

`data/{market}_{date}`:

```json
{
  "id": "KRW-BTC_2025-01-01",
  "market": "KRW-BTC",
  "date": "2025-01-01",
  "value": 100000000,
  "open": 99000000,
  "high": 101000000,
  "low": 98000000,
  "volume": 10,
  "memo": "형식 설명용 예시",
  "source": "manual",
  "created_at": "2025-01-02T00:00:00+00:00",
  "updated_at": "2025-01-02T00:00:00+00:00"
}
```

`value`는 미션의 수치 필드에 대응하는 **종가**입니다. OHLCV와 종목을 확장했고, 메모는 분석에 대한 사용자 기록입니다. 위 수치는 데이터 형식 예시이며 실거래 시세가 아닙니다.

- 일봉 시작일은 UTC 날짜이며 한국 시간 오전 9시 시작입니다. 현재 진행 중인 UTC 일봉을 제외합니다.
- 볼린저 밴드: 종가 SMA20 ± 2 × **모집단** 표준편차. 20번째 일봉부터 계산합니다.
- RSI14: 최초 14개 가격 변화의 상승·하락 평균을 초기값으로 쓰는 Wilder 평활. 15번째 일봉부터 계산합니다. 등락이 모두 없으면 50, 하락만 없으면 100입니다.
- MACD: SMA로 초기화한 EMA12 − EMA26. 시그널은 MACD의 EMA9입니다. 각각 26번째·34번째 일봉부터 계산됩니다. 다른 서비스의 EMA 초기값·조회 시작 구간에 따라 수치 차이가 날 수 있습니다.
- 거래량 비율: 최신 거래량 ÷ **현재 일봉을 제외한** 이전 20개 평균. 21번째부터 계산하며 평균이 0이면 `null`입니다.
- 최근 흐름: 최근 7개 / 직전 7개 종가 평균 변화율. +1% 초과 상승, −1% 미만 하락, 나머지 유지입니다.
- 거래 없는 날짜를 보간하지 않습니다. 날짜 간격이 불연속이면 화면과 요약에 알립니다. 지표의 개수는 달력 날짜가 아닌 관측 일봉 수입니다.
- 재수집은 기존 문서를 건너뜁니다. 수동 수정·메모를 덮어쓰지 않습니다. 수동 삭제 후 수집하면 원본이 다시 추가됩니다.

요약은 기간·개수·평균/최대/최소/최근 종가·추세·최신 지표를 반환합니다. 표준 요약에는 전체 원시 메모를 넣지 않아 메모를 통해 AI 지시가 섞이지 않도록 합니다. 지표는 Python에서 계산하고 AI는 계산 결과를 설명합니다.

초기 적재를 CLI로 하려면:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m scripts.import_data --market KRW-BTC
..\.venv\Scripts\python.exe -m scripts.import_data --market KRW-BTC --apply
```

첫 명령은 공개 시세 조회와 미리보기만, `--apply`는 `.env`의 저장소에 기록합니다. 상장한 지 얼마 안 된 종목은 100개 미만일 수 있어 평가 시연에는 충분한 이력이 있는 종목을 사용합니다.

## API

전체 스키마와 직접 실행은 `/docs`에서 확인합니다. 데이터·요약 조회는 `?market=KRW-BTC`처럼 종목을 지정하며 기본은 BTC입니다.

| 메서드 | 경로 | 역할 |
| --- | --- | --- |
| GET | `/health` | 서버 상태·저장 모드·키 설정 여부만 표시 |
| GET | `/api/markets` | 업비트 원화 종목 목록 (서버 5분 캐시) |
| POST | `/api/data/import` | `{ "market": "KRW-BTC" }`의 완료 일봉 수집 |
| POST | `/api/data` | 새 OHLCV + 메모 추가 |
| GET | `/api/data` | 선택 종목 목록, 최신 날짜순 |
| PUT | `/api/data/{id}` | 수치·메모 수정. 종목·날짜 변경은 새 기록으로 추가 |
| DELETE | `/api/data/{id}` | 데이터 삭제 |
| GET | `/api/data/summary` | 선택 종목의 계산된 요약 |
| POST | `/api/conversations` | 완성된 사용자/AI 메시지 쌍을 명시적 저장 |
| GET | `/api/conversations` | 이 브라우저의 대화 메타데이터 목록 |
| GET | `/api/conversations/{id}` | 선택 대화의 전체 메시지 |
| DELETE | `/api/conversations/{id}` | 대화 삭제 |
| POST | `/api/chat` | 요약 주입 → OpenAI 호출 → 한 턴 자동 저장 |

대화/채팅 API에는 UUID 형식의 `X-Client-Id` 헤더가 필요합니다. 프론트가 브라우저 localStorage에 식별자를 만들고 전송합니다. Swagger에서는 해당 입력칸에 테스트 UUID(예: `5fd8cacc-2165-4f7e-97ba-678fbca1a823`)를 넣어 일관되게 사용하세요.

`conversations/{uuid}`는 `owner`, `market`, `title`, `messages`, `message_count`, `created_at`, `updated_at`을 저장합니다. 목록 응답에는 메시지를 제외하고 불러오기에서만 포함합니다. `owner`는 응답에서 제외합니다. 익명 브라우저 식별은 로그인 인증이 아니므로 로그인·개인 금융정보 저장 기능으로 해석하지 않습니다.

## 채팅과 화면 상태

1. 종목 선택 시 기록·요약을 함께 가져오고 새 대화 상태로 전환합니다.
2. 데이터 추가/수정/삭제 후 목록과 요약을 다시 조회합니다.
3. 질문 시 선택 종목 요약을 서버에서 새로 계산해 `messages`의 `role: system`에 JSON으로 삽입합니다.
4. 해당 대화의 최근 20개 메시지와 새 질문을 Codyssey의 `/v1/chat/completions`에 전달하고 `choices[0].message.content`를 읽습니다.
5. 정상 완성된 응답만 사용자·AI 메시지 쌍으로 저장하고 대화 ID를 돌려줍니다. 이어지는 대화는 같은 문서에 트랜잭션으로 추가합니다.
6. 대화 목록의 ‘불러오기’를 누르면 종목·메시지·활성 대화 ID를 복원합니다. 데이터는 현재 저장 상태를 기준으로 새로 읽습니다.

동시 요청이 같은 대화를 바꾸면 이전 메시지 길이를 검사해 갱신 충돌을 알립니다. 한 대화는 최대 60개 메시지이며 이후 새 대화를 안내합니다.

## 입력·오류·운영

- Pydantic: 원화 종목 코드, 완료된 날짜, 양수 가격, 유한수, 0 이상 거래량, OHLC 관계, 500자 메모·2,000자 질문을 검증합니다. 잘못된 입력은 저장 전에 422입니다.
- 중복/수정 충돌/빈 데이터 질문은 409, 없는 기록은 404, 업비트·OpenAI 장애는 502, 저장소·키 설정 문제는 503입니다. 외부 예외의 원문·키를 브라우저에 전달하지 않습니다.
- DOM 출력은 `textContent`를 사용합니다. `<script>` 같은 메모도 실행되지 않습니다. 기본 삭제 확인은 앱 내부 접근 가능한 dialog로 제공합니다.
- CORS는 브라우저의 교차 origin 요청을 제어합니다. localhost와 Vercel은 Render와 origin이 달라 허용 목록이 필요합니다. CORS 자체가 API 인증은 아닙니다.
- AI 호출은 Codyssey 안내의 `max_tokens=1000`·40초 timeout·SDK 자동 재시도 0회, 브라우저/API는 최대 90초 대기합니다. 빈 응답이나 길이 제한으로 잘린 응답은 저장하지 않습니다. 과금 요청이 자동으로 반복되지 않습니다. 사용자/IP별 분당 채팅 제한, IP별 수집 제한을 적용합니다.
- 요청 제한은 단일 프로세스 메모리 기준입니다. 여러 worker/서버로 확장할 때는 공유 제한 저장소로 바꿉니다.
- Render 무료 인스턴스는 유휴 후 재시작될 수 있습니다. 첫 연결 안내와 로딩을 제공하며 오류 시 수동 새로고침할 수 있습니다. 로컬 디스크에 의존하지 않도록 제출 서버는 Firestore를 씁니다.
- 현재 미션 규모에서는 종목별 원본을 읽어 요약합니다. 데이터가 커지면 날짜 조건·페이지네이션·충분한 지표 준비 구간·요약 캐시를 추가합니다. 최근 30일 표시로 바꾸더라도 RSI/MACD 계산에는 앞선 준비 구간을 확보해야 합니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest
node --check frontend/app.js
node --test frontend/tests/state.test.cjs
```

테스트는 실제 SQLite 저장소와 FastAPI를 사용합니다. 외부 시세·AI 호출 경계만 통제된 HTTP/SDK 응답으로 대체하므로 테스트 실행에 API 과금·Firebase 계정이 필요 없습니다. 이는 실제 클라우드 연결 검증을 대신하지 않습니다.

배포 빌드 확인:

```powershell
$env:API_BASE_URL='https://실제-백엔드-서비스.onrender.com'
node frontend/build.mjs
```

빌드 결과는 `frontend/dist`입니다. 환경변수가 없거나 URL 형식이 잘못되면 배포를 실패시켜 localhost 주소가 실수로 서비스에 포함되는 것을 막습니다.

[평가 시연 체크리스트](docs/evaluation-checklist.md), [검증 기록](docs/verification.md), [제출 URL·스크린샷 기록](docs/submission.md)을 참고하세요.

## 공식 문서

- [업비트 일봉 조회](https://docs.upbit.com/kr/reference/list-candles-days)
- [OpenAI API 시작하기](https://developers.openai.com/api/docs/quickstart)
- [Firebase Admin SDK 설정](https://firebase.google.com/docs/admin/setup)
- [Firestore 시작하기](https://firebase.google.com/docs/firestore/quickstart)
- [Render FastAPI 배포](https://render.com/docs/deploy-fastapi), [무료 서비스 동작](https://render.com/docs/free)
- [Vercel 프로젝트 설정](https://vercel.com/docs/project-configuration)
