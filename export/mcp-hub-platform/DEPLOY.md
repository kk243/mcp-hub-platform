# Agent Hub 회사 이관 가이드

집에서 만든 `mcp-hub-platform`을 zip으로 묶어 회사에서 실행하는 순서다.

`.venv`와 `node_modules`는 zip에 넣지 않고 회사에서 다시 설치한다.
두 폴더는 만든 PC의 경로와 OS에 묶여 있어서 그대로 옮기면 동작하지 않는다.

## 1. 집에서 zip 만들기

프로젝트 폴더에서 아래 명령을 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File export\make_zip.ps1
```

`export\mcp-hub-platform.zip`이 만들어진다. 같은 내용의 복사본이 `export\mcp-hub-platform\`에도 남는다.
코드를 고친 뒤에는 다시 실행하면 새로 만들어진다.

zip에서 빠지는 것:

| 경로 | 빼는 이유 |
|---|---|
| `backend/.venv` | 이 PC의 Python 경로가 박혀 있다. 회사에서 다시 만든다 |
| `frontend/node_modules` | 회사에서 lock 파일로 다시 설치한다 |
| `backend/.env` | 회사 값으로 새로 만든다 |
| `backend/data`, `backend/storage` | 집 테스트 데이터다. 회사에서는 비어 있는 상태로 시작한다 |

`frontend/pnpm-lock.yaml`과 `backend/requirements.txt`는 버전을 고정하는 파일이라 반드시 들어가야 한다.
`samples/`도 들어가므로 회사에서 동작 확인용으로 쓸 수 있다.

## 2. 회사 PC 준비

- **Python 3.11**: `python --version`으로 확인한다.
- **Node 20.8.1**: `node --version`으로 확인한다.
- **pnpm 9 이상**: lock 파일 형식이 9.0이라 pnpm 8 이하로는 읽지 못한다. 없으면 `npm install -g pnpm@9`로 설치한다.
- **사내 미러**: 사내 PyPI나 npm 미러를 써야 하면 `pip config`와 `.npmrc`를 먼저 설정한다.

## 3. backend 실행

zip을 푼 폴더에서 실행한다.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # Linux: cp .env.example .env
```

`.env`에서 회사 값으로 바꿀 항목:

- `ADMIN_USERS`: 운영팀 사번을 콤마로 구분해 넣는다.
- `DEV_USER`: SiteMinder를 거쳐 접속하면 비운다. 회사 PC에서 혼자 테스트할 때만 본인 사번을 넣는다.
- `RELOAD`: 운영이면 `0`으로 둔다.
- `CORS_ORIGINS`: 프론트를 다른 도메인에서 띄울 때만 그 주소를 넣는다.

서버 실행:

```bash
python app.py
```

http://localhost:8000/docs 가 뜨면 정상이다. DB 파일과 테이블은 처음 실행할 때 자동으로 만들어진다.

## 4. frontend 실행

새 터미널에서 실행한다.

```bash
cd frontend
pnpm install --frozen-lockfile
copy .env.example .env
pnpm run dev
```

`--frozen-lockfile`을 붙이면 집에서 쓴 버전 그대로 설치되고 임의로 올라가지 않는다.
backend가 다른 서버에 있으면 `.env`의 `VITE_PROXY_TARGET`을 그 주소로 바꾼다.

http://localhost:5173 에 접속하면 상단에 Workflows, Tools, Skills 메뉴가 보인다.

## 5. 동작 확인

1. 화면 오른쪽 위에 사번이 보이면 사용자 식별이 된 것이다. SiteMinder를 거쳐 접속했다면 실제 본인 사번이 나와야 한다.
2. 관리 > 업로드에서 `samples/wf_bad_lot_cause.zip`을 올리고 검증한 뒤 등록한다. 사내망에서 POST와 zip 업로드가 막히지 않는지 이걸로 확인한다.
3. Workflows 메뉴에서 등록한 항목을 열고 그래프와 단계 클릭이 되는지 본다.
4. 테스트가 끝나면 backend를 멈추고 `backend/data`, `backend/storage`를 지워 깨끗한 상태로 시작한다.

## 6. git 저장소로 나누기

`backend/`와 `frontend/`를 각각 별도 저장소로 올린다.
두 폴더 모두 자체 `.gitignore`가 있어서 `.venv`, `node_modules`, `.env`, `data`, `storage`는 자동으로 빠진다.
설계서(`.claude/agent-hub-design.md`), 이 문서, `samples/`는 backend 저장소의 `docs/` 아래로 옮기는 것을 권장한다.

## 인터넷이 막힌 경우

회사 PC가 인터넷과 사내 미러 모두에 접근할 수 없으면 3, 4단계의 설치가 실패한다.
이때는 집에서 회사 OS용 설치 파일을 미리 받아 zip에 같이 넣어야 한다.
