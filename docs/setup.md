# 계정 연결 안내

계정은 준비되어 있고, 이 프로젝트의 인증정보·배포 연결이 아직 입력되지 않은 상태를 기준으로 합니다. 키 값은 채팅에 붙이지 말고 로컬 `.env`와 Render 설정 화면에 직접 입력하세요.

## 1. Firebase

1. [Firebase Console](https://console.firebase.google.com/)에서 이 미션용 프로젝트를 만들거나 사용하려는 프로젝트를 선택합니다.
2. Firestore Database에서 `(default)` 데이터베이스를 만듭니다. Standard / Native 방식의 Firestore를 사용합니다.
3. 브라우저에서 Firebase SDK로 직접 접근하지 않으므로 보안 규칙은 production(직접 접근 거부)으로 둡니다. 루트 `firestore.rules`는 이 프로젝트의 거부 규칙 예제입니다. 백엔드 Admin SDK는 서비스 계정 IAM으로 접근합니다.
4. 프로젝트 설정 → 서비스 계정 → Firebase Admin SDK → 개인 키 생성을 통해 JSON 파일을 내려받습니다. 기존 서비스 계정을 쓸 수 있으면 재사용하세요.
5. JSON 파일을 프로젝트의 `credentials/service-account.json` 또는 본인이 정한 안전한 경로에 둡니다. Git은 `credentials/`와 service-account 파일을 제외합니다.
6. 프로젝트 루트 `.env`를 편집합니다. 백슬래시 대신 `/`를 쓰면 경로 이스케이프를 피하기 쉽습니다.

```dotenv
STORAGE_BACKEND=firestore
FIREBASE_SERVICE_ACCOUNT_PATH=C:/Users/ds/Documents/Codyssey/m1-2/credentials/service-account.json
```

`FIREBASE_SERVICE_ACCOUNT_JSON`을 직접 사용하는 경우 경로 대신 JSON 전체를 한 줄로 입력합니다. Python dotenv 파일에서는 전체 JSON을 작은따옴표로 감싸고 원래 JSON의 `\n` 이스케이프를 유지합니다. Render 환경변수 입력창에는 바깥쪽 작은따옴표 없이 JSON 원문을 넣습니다.

## 2. Codyssey AI API (OpenAI 호환)

1. Codyssey에서 발급한 가상 API 키를 사용합니다. 이 키는 OpenAI 공식 API 주소가 아니라 Codyssey 게이트웨이에 전달해야 합니다.
2. `.env`의 `OPENAI_API_KEY=` 뒤에 키를 직접 입력합니다. 모델은 사용 가능 목록의 `gpt-5.4-mini`, 주소는 `https://copa.codyssey.kr/v1`로 설정합니다.
3. Codyssey 대시보드에서 사용 한도·크레딧 상태를 확인합니다. 코드가 키·모델을 만들거나 결제를 설정하지는 않습니다.

```dotenv
OPENAI_API_KEY=직접_입력한_실제_키
OPENAI_MODEL=gpt-5.4-mini
OPENAI_BASE_URL=https://copa.codyssey.kr/v1
```

위의 `직접_입력한_실제_키` 문구를 그대로 저장하지 마세요. 준비가 안 되면 값을 비워두면 됩니다.

사용자가 제공한 Codyssey 안내에 따라 Bearer 인증으로 `/v1/chat/completions`를 호출합니다. 요약은 `messages`의 `system` 메시지, 응답은 `choices[0].message.content`입니다. Responses API의 `/v1/responses`를 사용하지 않습니다. 401이면 키뿐 아니라 발급 플랫폼과 `OPENAI_BASE_URL`의 일치 여부를 확인하세요.

현재 안내의 도메인은 **`copa.codyssey.kr`**입니다. 이전 화면의 `qacopa.codyssey.kr`로는 같은 키가 401을 반환했고, `copa.codyssey.kr`로 바꾼 최소 요청은 HTTP 200으로 성공했습니다. 키를 무조건 재발급하기 전에 사용 계정에 표시된 정확한 도메인을 확인하세요.

## 3. 로컬에서 실제 연결 확인

1. 로컬 백엔드를 종료하고 **새 터미널**에서 `scripts/start-backend.ps1`을 `-LocalStorage` 없이 실행합니다.
2. `.env`가 `firestore`이고 이전 터미널의 `$env:STORAGE_BACKEND='sqlite'`가 남아 있지 않은지 확인합니다.
3. `http://127.0.0.1:8000/health`에서 `storage: firestore`, `ai_configured: true`, `firebase_configured: true`를 확인합니다. 이 값은 설정 존재 여부이며 실제 연결 성공을 보장하지는 않습니다.
4. 웹에서 **일봉 데이터 수집**을 누르고 Firebase 콘솔의 `data` 컬렉션에 100개 이상 문서가 생기는지 확인합니다. 로컬 SQLite 데이터는 자동 이전되지 않습니다.
5. ‘최근 흐름을 요약해줘’라고 질문합니다. 실제 답변과 `conversations` 문서의 메시지 쌍을 확인합니다.
6. 새 대화를 누른 뒤 대화 기록에서 이전 대화를 불러오고 메시지가 재표시되는지 확인합니다.

## 4. GitHub

이 프로젝트의 원격 저장소는 [leeds86/m1-2](https://github.com/leeds86/m1-2)입니다. `.env`, 키 JSON, `.local`, `.venv`, 원본 미션·평가지와 개인 개발 메모가 업로드 목록에 없는지 확인합니다. GitHub 비공개 저장소도 Render/Vercel이 권한을 가지고 있으면 사용할 수 있습니다.

루트에서 Git 저장소를 시작하는 명령 예제는 다음과 같습니다. 실제 원격 URL은 본인 저장소 주소를 사용하세요.

```powershell
git init -b main
git add .
git status --short
git commit -m "Build coin context mission app"
git remote add origin 본인의_GitHub_저장소_URL
git push -u origin main
```

이미 연결된 checkout에서는 다시 초기화하지 않고 `git status`로 상태를 확인합니다. Render와 Vercel에는 위 저장소를 연결하세요.

## 5. Render 백엔드

1. [Render Dashboard](https://dashboard.render.com/) → New → Web Service → 해당 GitHub 저장소를 연결합니다. 루트 `render.yaml`을 사용하는 Blueprint도 가능합니다.
2. Root Directory: `backend`
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Python 버전은 `render.yaml`에 `3.13.9`를 지정했습니다. 루트에 직접 설정할 때도 해당 값을 사용합니다.
6. 환경변수에 다음을 입력합니다.

| 이름 | 값 |
| --- | --- |
| `STORAGE_BACKEND` | `firestore` |
| `OPENAI_API_KEY` | 본인 Codyssey 가상 API 키 |
| `OPENAI_MODEL` | `gpt-5.4-mini` |
| `OPENAI_BASE_URL` | `https://copa.codyssey.kr/v1` |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | 서비스 계정 JSON 전체 원문 |
| `ALLOWED_ORIGINS` | 우선 로컬 origin; Vercel 배포 후 실제 origin 추가 |

7. 생성된 Render URL에서 `/health`, `/docs`를 확인합니다. 서버 주소를 다음 Vercel 단계에서 사용합니다.

## 6. Vercel 프론트

1. [Vercel Dashboard](https://vercel.com/dashboard) → Add New Project → 같은 GitHub 저장소를 연결합니다.
2. Root Directory를 `frontend`로 설정합니다. Framework는 `Other`입니다.
3. `frontend/vercel.json`이 Build Command `node build.mjs`, Output Directory `dist`를 지정합니다. 이 경로들은 `frontend`를 기준으로 합니다.
4. Vercel 환경변수 `API_BASE_URL`에 **Render origin**을 입력합니다. 예시 형식은 `https://서비스이름.onrender.com`이며 `/docs`나 `/api`를 붙이지 않습니다.
5. 배포한 뒤 실제 Vercel origin을 Render의 `ALLOWED_ORIGINS`에 추가합니다. 예: `http://localhost:5500,http://127.0.0.1:5500,https://서비스이름.vercel.app`.
6. CORS 환경변수 변경이 반영되도록 Render를 재배포/재시작합니다. Vercel preview URL을 시연할 때는 그 정확한 origin도 별도로 추가합니다.
7. Vercel 페이지에서 데이터 수집·추가·질문·대화 불러오기를 확인합니다. 평가자가 로그인 없이 접속할 수 있도록 프로젝트의 Deployment Protection 설정도 확인합니다.

## 7. 제출 준비

`docs/evaluation-checklist.md` 순서로 공개 URL에서 확인하고, `docs/submission.md`에 실제 URL과 스크린샷을 기록합니다. 로컬 SQLite 화면만으로 Firestore 항목을 통과했다고 표시하지 않습니다.

공식 절차: [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup), [OpenAI 시작하기](https://developers.openai.com/api/docs/quickstart), [Render FastAPI](https://render.com/docs/deploy-fastapi), [Vercel 설정](https://vercel.com/docs/project-configuration).
