# 제출 기록

계정 설정과 공개 배포를 완료한 뒤 아래 내용을 실제 값으로 채웁니다. 아직 공개 배포 완료를 의미하지 않습니다.

| 제출 항목 | 현재 상태 |
| --- | --- |
| GitHub 저장소 URL | https://github.com/leeds86/m1-2 |
| 프론트 URL (Vercel) | 배포 필요 |
| 백엔드 URL (Render) | 배포 필요 |
| Swagger URL | 배포된 Render origin + `/docs` |
| Firestore 데이터 수 | 실제 BTC 일봉 200개 저장·조회 확인. 공개 배포 후 재확인 필요 |
| AI 실응답 / 대화 저장 | 실제 Codyssey 응답·Firestore 자동 저장·4개 메시지 불러오기 확인. 공개 배포 후 재확인 필요 |

## 화면 증빙

로컬 검증 화면은 `screenshots/` 아래 보관합니다. 제출용 실제 AI 답변·Firestore 저장·공개 Swagger 화면은 연결 후 추가하고 이 문서에 링크를 기록합니다.

- [로컬 분석 화면](screenshots/local-desktop.jpg) — 실제 업비트 일봉 200개, SQLite 모드. AI 연결 전 화면.
- [모바일 레이아웃 확인](screenshots/local-mobile.jpg) — 모바일 배치 확인용. 실제 클라우드 시연 증빙은 아님.
- [모바일 입력창 확인](screenshots/local-mobile-form.jpg) — 새 코드의 입력창·취소 동작 재검증.
- [실제 Firestore·AI 연결 화면](screenshots/firestore-ai-connected.jpg) — 실제 일봉 200개와 Codyssey AI 응답, 대화 저장·불러오기 검증. 로컬 앱과 실제 외부 서비스 조합이며 공개 배포 화면은 아님.

## 실행과 평가

설치는 루트 README, 계정 설정은 `docs/setup.md`, 시연 순서는 `docs/evaluation-checklist.md`, 자동/브라우저 검증 범위는 `docs/verification.md`를 사용합니다.
