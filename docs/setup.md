# 배포 구성

소스 저장소는 [leeds86/m1-2](https://github.com/leeds86/m1-2)이며 백엔드는 Render, 프론트는 Vercel에서 서비스합니다.

## Render

| 설정 | 값 |
| --- | --- |
| Root Directory | `backend` |
| Runtime | Python 3.13.9 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check | `/health` |
| API 주소 | `https://m1-2-j9ok.onrender.com` |

| 환경변수 | 값 / 용도 |
| --- | --- |
| `STORAGE_BACKEND` | `firestore` |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Firestore 접근 권한을 가진 서비스 계정 JSON. 비밀 값 |
| `OPENAI_API_KEY` | Codyssey 가상 API 키. 비밀 값 |
| `OPENAI_MODEL` | `gpt-5.4-mini` |
| `OPENAI_BASE_URL` | `https://copa.codyssey.kr/v1` |
| `ALLOWED_ORIGINS` | `https://m1-2-frontend-topaz.vercel.app` |

Firestore는 Admin SDK와 서비스 계정 IAM으로 접근합니다. 브라우저의 직접 데이터베이스 접근은 `firestore.rules`로 거부합니다. 비밀 값은 Render 환경변수에만 등록하며 소스 코드나 프론트에 포함하지 않습니다.

환경변수 변경은 재배포 후 반영됩니다. `/health`는 설정 존재 여부를 표시하므로 실제 저장소 연결은 [요약 API](https://m1-2-j9ok.onrender.com/api/data/summary?market=KRW-BTC)로 확인합니다.

## Vercel

| 설정 | 값 |
| --- | --- |
| Project | `m1-2-frontend` |
| Root Directory | `frontend` |
| Framework Preset | `Other` |
| Build Command | `node build.mjs` |
| Output Directory | `dist` |
| `API_BASE_URL` | `https://m1-2-j9ok.onrender.com` |
| 운영 주소 | `https://m1-2-frontend-topaz.vercel.app` |

`API_BASE_URL`은 경로 없는 HTTPS origin입니다. `/docs`, `/api`, `/v1`을 붙이지 않습니다. `build.mjs`는 이 공개 주소만 `dist/config.js`에 기록합니다. Vercel에는 AI 키와 서비스 계정을 등록하지 않습니다.

빌드 환경변수를 바꾸면 새로 배포해야 반영됩니다. 방문자는 위 운영 주소를 사용하며, 로그인 보호가 적용된 개별 배포 주소와 구분합니다.

## 운영 확인

1. [서버 상태](https://m1-2-j9ok.onrender.com/health)와 [Swagger](https://m1-2-j9ok.onrender.com/docs)를 확인합니다.
2. [웹 서비스](https://m1-2-frontend-topaz.vercel.app/)에서 데이터 조회·수집과 AI 질문을 실행합니다.
3. 대화 기록을 불러와 저장된 메시지가 복원되는지 확인합니다.
4. 운영 도메인이 바뀌면 Render의 `ALLOWED_ORIGINS`와 안내 문서의 주소를 함께 갱신합니다.
