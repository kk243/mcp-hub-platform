# Agent Hub — backend

팀별 AI agent의 workflow / tool / skill 메타를 공유하는 API 서버 (FastAPI + sqlite3).

## 실행

```bash
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # 값 확인
python app.py
```

- API 문서: http://localhost:8000/docs
- DB(`data/hub.db`)와 테이블은 처음 실행할 때 자동으로 만들어진다.
- 업로드한 코드는 `storage/<tool|skill>/<key>/`에 저장된다.

## 구조

```
app.py               FastAPI 생성, router 등록, uvicorn.run
src/hub/router.py    모든 API (prefix /api/hub, GET/POST만)
src/hub/db.py        sqlite 연결, 테이블 생성, JSON 컬럼 변환
src/hub/importer.py  등록 zip 검증 → 저장
```

## 사용자와 권한

- 사용자: 요청 헤더 `SM_USER`(env `SM_USER_HEADER`로 변경). 헤더가 없으면 `DEV_USER`.
- 관리자: `ADMIN_USERS`(콤마 구분). `/api/hub/admin/*`은 관리자만 쓸 수 있다.
- 코드 열람: 관리자, owner, `public`, 또는 `allowlist`에 포함된 사용자.

로컬에서 권한을 확인하려면 `.env`의 `DEV_USER`를 바꾸거나 헤더를 직접 넣는다.

```bash
curl -H "SM_USER: 99999999" http://localhost:8000/api/hub/items/tool_bad_lot_query/code
```

## 샘플 등록

```bash
python ../samples/make_sample.py
curl -F file=@../samples/wf_bad_lot_cause.zip "http://localhost:8000/api/hub/admin/import?dry_run=0"
curl -F file=@../samples/wf_bad_lot_cause_teamA.zip "http://localhost:8000/api/hub/admin/import?dry_run=0"
```

화면의 관리 > 업로드에서 올려도 된다.

## env

| 이름 | 설명 |
|---|---|
| `HOST`, `PORT` | 바인드 주소 |
| `RELOAD` | `1`이면 코드 변경 시 재시작 (개발용) |
| `SM_USER_HEADER` | 사용자 헤더명 |
| `DEV_USER` | 헤더가 없을 때 쓸 사용자. 운영에서는 비운다 |
| `ADMIN_USERS` | 관리자 사번 (콤마 구분) |
| `DB_PATH`, `STORAGE_DIR` | DB 파일, 코드 저장 위치 |
| `CORS_ORIGINS` | 프론트를 다른 도메인에서 띄울 때만 설정 (콤마 구분) |
