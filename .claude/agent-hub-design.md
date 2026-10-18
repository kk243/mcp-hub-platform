# Diff AI Agent Hub — 설계서 (mini-project 버전)

> 팀별 AI agent의 **workflow / skill / tool**을 공유해서 중복개발을 막는 사내 웹.
> **최대한 단순하게** 만든다. 커지면 그때 구조화한다.

---

## 0. 구현 규칙 (Claude CLI는 먼저 읽을 것)

1. **단순함이 최우선이다.**
   - 파일을 최소로 쓰고, 추상화 계층을 만들지 않는다 (service / repository 분리 금지).
   - ORM을 쓰지 않는다.
   - 상태관리 라이브러리를 쓰지 않는다.
2. **HTTP는 GET과 POST만 쓴다.** 사내망 제약 때문에 PUT / PATCH / DELETE는 금지한다. 수정과 삭제도 `POST /.../update`처럼 POST로 처리한다.
3. **새 프로젝트로 생성한다.** 집에서 구현한 뒤 회사로 옮길 예정이다. 회사의 기존 프로젝트와 같은 형태로 만든다.
   - Backend
     - `python app.py`로 시작한다. `app.py` 안에서 `uvicorn.run(...)`을 호출한다.
     - `src/<기능폴더>/router.py`의 `APIRouter`를 `app.py`에서 `include_router`로 등록한다.
   - Frontend
     - `pnpm run dev`로 실행한다.
     - 메뉴별 폴더는 `src/pages/<메뉴>/`에 둔다.
     - `src/routes/index.jsx`에 route 배열(또는 `<Routes>`)을 모아서 등록한다.
4. **backend와 frontend는 독립 프로젝트로 만든다.** 회사에서는 둘을 **별도 git 저장소로 분리**한다. 그래서 서로의 파일을 import하거나 참조하지 않는다. 각 폴더가 자체 `.gitignore`, `.env.example`, `README.md`를 가진다.
5. **버전은 고정한다.**
   - Node **20.8.1**, React / react-dom **18**, Python **3.11.16**
   - 한 번 설치한 버전은 임의로 올리지 않는다 (lock 파일 커밋).
   - Vite 7은 Node 20.19 이상이 필요하므로 **금지**한다.
6. **실행은 각 폴더에서 한다.** `backend/`에서 `python app.py`, `frontend/`에서 `pnpm run dev`.
7. **UI 스택을 지킨다.**
   - UI는 antd v4 컴포넌트를 먼저 쓴다. 직접 CSS는 최소화한다.
   - 표는 무조건 AG Grid Community로 만든다.
   - 그래프는 `@xyflow/react`로 만든다.
   - 그 외 UI 라이브러리는 추가하지 않는다.

---

## 1. 원칙

- **계열 + 변형**: workflow는 `family`(문자열)로 묶는다. 변형이 생기면 같은 family에 **새 workflow를 등록**한다.
- **버전 관리 없음**: 대신 `derived_from` 필드에 원본 workflow의 key 한 줄만 남긴다.
- **불변**:
  - 로직(코드, 구조, 스키마)은 수정하지 않는다. 바뀌면 새 key로 등록한다.
  - 이름, 설명, 태그, 공개범위, 폐기 여부만 수정할 수 있다.
- **메타는 공개, 코드는 제한**: 코드 원문은 원 개발자가 허락한 경우에만 열람할 수 있다.
- **등록은 운영팀만**: raw code를 받아 로컬 Claude CLI로 분해한 뒤, zip 파일로 업로드한다.

### 용어

- **Tool**: 사내 데이터를 조회하는 코드 (query 위주)
- **Skill**: 조회한 데이터를 전처리하거나 보여주는 코드
- **업무 workflow**: 사람이 읽는 세로 단계 (`biz_steps`)
- **Code workflow**: tool과 skill 노드로 이루어진 그래프 (`code_nodes` + `code_edges`)

---

## 2. 의존성

### UI 기본 규칙

- **UI는 antd v4**(4.24.x)로 만든다. **antd v5 문법(`theme` token, `App` 컴포넌트 등)은 쓰지 않는다.**
- **표는 모두 AG Grid Community**(무료, MIT)로 만든다. antd `Table`은 쓰지 않는다.
- **Enterprise 기능은 쓰지 않는다.** `ag-grid-enterprise`를 설치하지 않으며, row grouping, pivot, master-detail, 엑셀 export 등은 금지한다.

### 추가 패키지

| 위치 | 패키지 | 버전 | 용도 |
|---|---|---|---|
| Backend | python-multipart | 최신 | zip 업로드 |
| Backend | PyYAML | `>=6` | manifest 파싱 |
| Backend | python-dotenv | 최신 | .env 로딩 |
| Frontend | react / react-dom | `@18` | — |
| Frontend | react-router-dom | `@6` (회사 버전 확인) | 라우팅 |
| Frontend | antd | `@4` (4.24.x) | 전체 UI |
| Frontend | ag-grid-react (+ ag-grid-community 자동 설치) | 회사 버전을 알면 그 버전, 아니면 React 18이 peerDependencies에 포함된 최신 버전 | 목록 표, 스키마 표 |
| Frontend | @xyflow/react | `^12` | code workflow 그래프 |
| Frontend | @dagrejs/dagre | `^1` | 그래프 자동 배치 (위→아래) |

### AG Grid 사용 규칙

- **모듈 등록**: v33 이상은 모듈 등록이 필수이다. 설치된 버전 문서에 맞춰 앱 진입점에서 **한 번만** 등록한다.
  - `ModuleRegistry.registerModules([AllCommunityModule])` 또는 `<AgGridProvider modules={[AllCommunityModule]}>` (최신 버전 방식)
- **테마**: 버전 기본 테마(Quartz)를 쓴다. 폰트와 크기는 antd와 비슷하게 맞추는 정도만 조정한다.
- **작은 표**(스키마, 파라미터)는 `domLayout="autoHeight"`로 높이를 내용에 맞춘다.

### 기타

- **DB**: Python 내장 `sqlite3`만 쓴다. 파일 위치는 `data/hub.db`이다.
- **업무 workflow**: 별도 패키지 없이 **antd `Steps`**를 `direction="vertical"`로 쓰고, `onChange`로 단계를 클릭할 수 있게 한다.
- **코드 표시**: 라이브러리 없이 antd `Tabs`와 `<pre><code>`로 보여준다. 하이라이트는 나중에 필요하면 추가한다.

---

## 3. 파일 구조

집에서는 한 폴더(`mcp-hub-platform/`) 안에서 개발한다. 회사로 옮길 때는 `backend/`와 `frontend/`를 **각각 별도 git 저장소**로 올린다.

```
mcp-hub-platform/
  agent-hub-design.md          # 이 설계서
  samples/                     # 테스트용 등록 zip (+ zip 생성 스크립트)
  backend/                     # → 회사 backend 저장소
  frontend/                    # → 회사 frontend 저장소
```

### backend/

```
backend/
  app.py                  # FastAPI 생성 + include_router + uvicorn.run (python app.py)
  src/
    __init__.py
    hub/
      __init__.py
      router.py           # 모든 API (APIRouter, prefix=/api/hub)
      db.py               # sqlite 연결, 테이블 생성, JSON 헬퍼
      importer.py         # zip → 검증 → 저장
  data/                   # hub.db 자동 생성 (gitignore)
  storage/                # 업로드 코드 storage/<tool|skill>/<key>/ (gitignore)
  requirements.txt        # fastapi, uvicorn, python-multipart, PyYAML, python-dotenv (버전 고정)
  .env.example
  .gitignore              # .venv, __pycache__, data/, storage/, .env
  README.md               # venv 생성 → pip install → python app.py
```

**app.py 형태**

```python
import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.hub.router import router as hub_router

load_dotenv()
app = FastAPI(title="Agent Hub")

# CORS: env CORS_ORIGINS(콤마 구분)이 있을 때만 켠다
if os.getenv("CORS_ORIGINS"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS").split(","),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

app.include_router(hub_router)

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "0") == "1",
    )
```

### frontend/

```
frontend/
  package.json            # "dev": "vite", engines.node ">=20.8.1"
  pnpm-lock.yaml
  vite.config.js          # server.proxy: /api → env VITE_PROXY_TARGET (기본 http://localhost:8000)
  index.html
  .env.example
  .gitignore              # node_modules, dist, .env
  README.md
  src/
    main.jsx              # ReactDOM.createRoot, antd ConfigProvider(ko_KR), AG Grid 모듈 등록, 라우터
    App.jsx               # antd Layout(상단 메뉴) + <Outlet/>
    routes/index.jsx      # route 배열 등록
    pages/hub/
      api.js              # fetch 함수 모음 (GET/POST만, base = import.meta.env.VITE_API_BASE || '/api')
      HubHome.jsx         # 목록 + 검색 (탭: Workflows / Tools / Skills)
      WorkflowDetail.jsx  # 핵심 화면: 업무 flow + code flow + drawer
      CodeFlow.jsx        # xyflow + dagre
      Grid.jsx            # AG Grid 공통 래퍼
      ItemDetail.jsx      # tool/skill 상세 내용 (Drawer와 Page가 공유)
      ItemDrawer.jsx
      ItemPage.jsx
      Admin.jsx           # zip 업로드 + 메타 수정
      hub.css
```

### 프로젝트 생성 (Claude CLI가 실행)

**backend**

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fastapi uvicorn python-multipart PyYAML python-dotenv
pip freeze > requirements.txt
```

**frontend** — Node 20.8.1에서 돌아가도록 버전을 고정한다.

```bash
cd frontend
pnpm create vite@5 . --template react      # JS 템플릿
pnpm add react@18 react-dom@18 react-router-dom@6 antd@4 \
         ag-grid-react ag-grid-community @xyflow/react@12 @dagrejs/dagre@1
pnpm add -D vite@5 @vitejs/plugin-react@4
```

- 설치 후 `package.json`에서 `react`와 `react-dom`이 18.x인지 확인한다. 템플릿 기본값이 19라면 18로 내린다.
- `ag-grid-react`의 `peerDependencies`에 React 18이 포함되어 있는지 확인한다. 회사에서 쓰는 AG Grid 버전을 알면 그 버전으로 고정한다.
- 설치 경고에 `engines` 불일치(Node 버전)가 나오면 해당 패키지 버전을 낮춘다.

---

## 4. DB (테이블 3개)

리스트나 객체 형태의 값은 **JSON 문자열**로 저장한다. 조인 테이블은 만들지 않는다.

```sql
CREATE TABLE IF NOT EXISTS workflows (
  key TEXT PRIMARY KEY,           -- 불변
  name TEXT NOT NULL,
  description TEXT,
  family TEXT NOT NULL,           -- 계열명 (예: 품질분석)
  team TEXT, owner TEXT,
  derived_from TEXT,              -- 원본 workflow key (nullable)
  tags TEXT DEFAULT '[]',         -- JSON list
  biz_steps TEXT NOT NULL,        -- JSON: [{key,title,description,code_nodes:[nodeKey]}]
  code_nodes TEXT NOT NULL,       -- JSON: [{key,type:'tool'|'skill',ref:itemKey}]
  code_edges TEXT NOT NULL,       -- JSON: [[srcNodeKey, dstNodeKey]]
  deprecated INTEGER DEFAULT 0,
  replaced_by TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS items (   -- tool과 skill을 한 테이블로
  key TEXT PRIMARY KEY,           -- 불변
  type TEXT NOT NULL,             -- 'tool' | 'skill'
  name TEXT NOT NULL,
  description TEXT,
  team TEXT, owner TEXT,
  tags TEXT DEFAULT '[]',
  spec TEXT NOT NULL,             -- JSON. 아래 참고
  entrypoint TEXT,                -- 메인 파일 상대경로
  code_hash TEXT,                 -- 코드 sha256 (중복/불변 체크)
  code_visibility TEXT DEFAULT 'private',  -- public | allowlist | private
  allowlist TEXT DEFAULT '[]',    -- JSON list of user_id
  deprecated INTEGER DEFAULT 0,
  replaced_by TEXT,
  created_at TEXT
);
```

### `items.spec` 형식

**tool**
```json
{ "data_source": "MES", "tables": ["MES.BAD_LOT"],
  "params": [{"name":"start_date","type":"date","required":true}],
  "output_schema": [{"name":"lot_id","type":"str"}] }
```

**skill**
```json
{ "input_schema": [{"name":"lot_id","type":"str"}],
  "output_type": "table", "prompt": null }
```

### 사용처(역참조)

별도 테이블 없이 계산한다. `workflows`를 전부 읽어서 `code_nodes`에 해당 `ref`가 들어 있는 workflow만 골라낸다. 수백 건 규모까지는 이 방식으로 충분하다.

---

## 5. 사용자와 권한

- **사용자 식별**: 요청 헤더 `SM_USER`(SiteMinder)에서 읽는다. 헤더명은 env `SM_USER_HEADER`로 바꿀 수 있다.
  - 헤더가 없으면 env `DEV_USER` 값을 쓴다 (로컬 개발용).
- **관리자**: env `ADMIN_USERS`(콤마 구분)에 있는 사용자. `/api/hub/admin/*` 요청은 관리자가 아니면 403을 반환한다.
- **코드 열람 허용 조건** (하나라도 해당하면 허용):
  - 관리자이거나 owner인 경우
  - `code_visibility`가 `public`인 경우
  - `code_visibility`가 `allowlist`이고 allowlist에 포함된 경우
- **메타데이터 조회**: 누구나 가능하다.

---

## 6. 등록 패키지

### zip 구조

```
package.zip
  manifest.yaml
  tools/<key>/...
  skills/<key>/...
```

### manifest.yaml

```yaml
workflow:
  key: wf_bad_lot_cause_teamA
  name: 불량 LOT 원인 분석 (A팀형)
  description: ...
  family: 품질분석
  team: A팀
  owner: "12345678"
  derived_from: wf_bad_lot_cause      # 선택
  tags: [불량]

biz_steps:
  - { key: s1, title: 불량 데이터 조회, description: ..., code_nodes: [n1, n2] }
  - { key: s2, title: 원인 후보 정리, code_nodes: [n3] }
  - { key: s3, title: 리포트 생성, code_nodes: [n4] }

code_nodes:
  - { key: n1, type: tool,  ref: tool_bad_lot_query }
  - { key: n2, type: tool,  ref: tool_equipment_history }   # 이미 등록된 tool이면 ref만
  - { key: n3, type: skill, ref: skill_outlier_preprocess }
  - { key: n4, type: skill, ref: skill_summary_report }

code_edges: [[n1, n3], [n2, n3], [n3, n4]]

items:                                 # 이번에 새로 들어오는 tool/skill만
  - key: tool_bad_lot_query
    type: tool
    name: 불량 LOT 조회
    description: ...
    team: A팀
    owner: "12345678"
    entrypoint: tools/tool_bad_lot_query/main.py
    code_visibility: allowlist
    allowlist: ["23456789"]
    spec:
      data_source: MES
      tables: [MES.BAD_LOT, MES.LOT_HIST]
      params: [{ name: start_date, type: date, required: true }]
      output_schema: [{ name: lot_id, type: str }, { name: qty, type: int }]
```

### importer 검증 (`importer.py`, 함수 몇 개로 끝낸다)

**에러** — 등록을 중단한다.
1. 필수 필드가 빠졌거나 YAML을 파싱할 수 없다.
2. workflow key가 이미 존재한다.
3. `code_nodes.ref`가 이번 `items`에도 DB에도 없다.
4. `biz_steps.code_nodes`나 `code_edges`가 정의되지 않은 node key를 참조한다.
5. 같은 item key가 이미 있는데 code_hash가 다르다. ("로직 변경은 새 key로")
6. entrypoint 파일이 zip 안에 없다.

**경고** — 등록은 허용한다.
1. 같은 item key이고 code_hash도 같으면 기존 것을 재사용한다.
2. 비슷한 tool이 이미 있다: 같은 `data_source`이면서 `tables`가 하나라도 겹친다.
3. 코드에 password, pwd, secret, token 같은 문자열이 있다.

### 등록 흐름

- `dry_run=1`: 검증 결과만 반환한다.
- `dry_run=0`: DB에 insert하고 `storage/`에 코드 파일을 저장한다. 실패하면 DB는 rollback하고 저장한 파일도 지운다.

---

## 7. API (GET / POST만, prefix `/api/hub`)

| Method | Path | 설명 |
|---|---|---|
| GET | `/me` | `{user_id, is_admin}` |
| GET | `/workflows?q=&family=&team=` | 목록 (biz_steps / nodes 제외한 요약). family별 정렬 |
| GET | `/workflows/{key}` | 상세. code_nodes에 item의 name, type, data_source를 붙여서 반환. 같은 family의 형제 workflow 목록도 포함 |
| GET | `/items?type=&q=&data_source=` | tool/skill 목록. 각 항목에 `used_by_count` 포함 |
| GET | `/items/{key}` | 상세 + `used_by`(workflow 목록) + `can_view_code` |
| GET | `/items/{key}/code` | 파일 목록과 내용. 권한이 없으면 403 |
| POST | `/admin/import?dry_run=1` | multipart `file`(zip) → `{errors, warnings, created}` |
| POST | `/admin/update` | body: `{target: 'workflow'\|'item', key, fields:{name?,description?,tags?,team?,owner?}}`. 허용된 필드 외에는 400 |
| POST | `/admin/deprecate` | body: `{target, key, replaced_by?}` |
| POST | `/admin/visibility` | body: `{key, code_visibility, allowlist}` |

`q` 검색은 name, description, tags에 대한 `LIKE` 검색이다. items는 spec(테이블명 포함)도 검색 대상에 넣는다.

---

## 8. 화면

### Routes

| 경로 | 화면 |
|---|---|
| `/hub` | HubHome |
| `/hub/workflows/:key` | WorkflowDetail |
| `/hub/items/:key` | ItemPage |
| `/hub/admin` | Admin (관리자만 메뉴 노출) |

### 사용 컴포넌트 매핑

| 용도 | 컴포넌트 |
|---|---|
| 레이아웃 | antd `Layout`, `Row` / `Col`, `Card`, `Space`, `Typography` |
| 검색 / 필터 | antd `Input.Search`, `Select` (+ AG Grid 컬럼 필터, quick filter) |
| 목록 / 표 | **AG Grid** (`Grid.jsx` 래퍼) |
| 업무 workflow | antd `Steps` (vertical, clickable) |
| code workflow | `@xyflow/react` (노드 내부에 antd `Tag` / `Tooltip`) |
| 상세 패널 | antd `Drawer` + `Descriptions` |
| 상태 표시 | antd `Tag`(type, data_source), `Alert`(폐기 배너, 검증 결과), `Empty`, `Spin` |
| 관리 | antd `Tabs`, `Upload.Dragger`, `Form`, `Modal.confirm`, `message` |

### 8.1 HubHome
- 상단: `Input.Search` (서버 `q` 검색) + `Tabs` 3개 — **Workflows / Tools / Skills**
- 각 탭은 **AG Grid 한 개**로 구성한다.
  - 정렬, 컬럼 필터, 그룹 표시는 Community 기능 안에서 처리한다.
  - 기본 정렬은 Workflows는 family, Tools는 data_source, Skills는 output_type이다.
  - 행을 클릭하면 상세로 이동한다 (`onRowClicked`).
- **Workflows 컬럼**: 이름, family, 팀, owner, 단계 수, 태그(`Tag` cellRenderer), 원본(`derived_from`), 상태(폐기된 행은 회색 `rowClassRules`)
- **Tools 컬럼**: 이름, data_source, tables, 사용처 수, 팀, 공개범위
- **Skills 컬럼**: 이름, output_type, 사용처 수, 팀, 공개범위
- 사용처 수는 목록 API에서 `used_by_count`로 내려준다.

### 8.2 WorkflowDetail (핵심 화면)

```
┌──────────────────────┬────────────────────────────────┐
│ 업무 Workflow (세로)   │ Code Workflow                   │
│ ① 불량 데이터 조회      │  [T] 불량LOT조회  [T] 설비이력     │
│        ↓             │         ↘        ↙              │
│ ② 원인 후보 정리        │      [S] 이상치 전처리             │
│        ↓             │            ↓                    │
│ ③ 리포트 생성          │      [S] 요약 리포트               │
└──────────────────────┴────────────────────────────────┘
                              노드 클릭 → 우측 ItemDrawer
```

- **헤더**: 이름, 팀, owner, family, 원본 링크(`derived_from`), 같은 family의 다른 변형 링크. 폐기된 경우 상단에 배너를 띄운다.
- **레이아웃**: `Row`로 좌우를 나눈다.
  - 좌측 `Col span={8}`: 업무 단계
  - 우측 `Col span={16}`: `Card` 안에 CodeFlow (높이 약 600px)
- **업무 단계**: antd `Steps direction="vertical" current={선택 index} onChange={...}`
  - 각 step에 `title`과 `description`을 넣고, description 아래에 연결된 노드 수를 작은 `Tag`로 표시한다.
  - 단계를 클릭하면 해당 단계의 code node만 강조하고 나머지는 흐리게(opacity 0.3) 한다.
  - "전체 보기" 버튼으로 선택을 해제한다.
- **CodeFlow** (`@xyflow/react`)
  - dagre(`rankdir: 'TB'`)로 자동 배치한다.
  - `nodesDraggable={false}`, `nodesConnectable={false}`로 드래그와 연결을 막고, `fitView`를 켠다. `Controls`와 `Background`를 쓴다.
  - 커스텀 노드 2종:
    - `toolNode`: 파란 계열, 상단에 `Tag`로 data_source 표시
    - `skillNode`: 초록 계열, 상단에 `Tag`로 output_type 표시
  - 노드에 hover하면 연결된 업무 단계를 `Tooltip`으로 표시한다.
  - `@xyflow/react/dist/style.css`를 import한다.
  - **ReactFlow 부모 요소에는 반드시 높이를 지정한다.** 높이가 없으면 그래프가 렌더링되지 않는다.
- **노드 클릭**: ItemDrawer를 연다.
- **선택 상태는 URL에 넣는다** (`?step=s2&node=n3`). 링크로 공유할 수 있다.

### 8.3 ItemDrawer / ItemPage
- antd `Drawer` (width 520)
- **기본 정보**: `Descriptions`(이름, key, type, 팀, owner, 설명, 공개범위)
- **spec**:
  - tool: data_source, tables는 `Tag`로 표시하고, params와 output_schema는 **AG Grid**(autoHeight)로 표시한다.
  - skill: input_schema는 **AG Grid**로, output_type은 `Tag`로, prompt는 `Collapse` 안에 `<pre>`로 표시한다.
- **사용 중인 workflow**: **AG Grid**(이름, family, 팀). 행을 클릭하면 해당 workflow로 이동한다.
- **[코드 보기] 버튼**
  - 권한이 없으면 `disabled`로 두고 `Tooltip`으로 "원 개발자 허락 필요"를 표시한다.
  - 권한이 있으면 `Modal`(width 1000)을 열고, 파일별 `Tabs` 안에 `<pre>`로 코드를 보여준다.
- ItemPage는 같은 내용을 전체 페이지로 보여준다 (`ItemDetail` 내용 컴포넌트를 Drawer와 Page에서 공유).

### 8.4 Admin
- `Tabs`: **업로드 / 수정**
- **업로드 탭**
  - `Upload.Dragger`(zip, `beforeUpload`에서 `false`를 반환해 수동 전송) → [검증] 버튼
  - 결과: 에러는 `Alert type="error"`, 경고는 `Alert type="warning"`으로 리스트 표시하고, 생성 예정 항목은 **AG Grid**로 보여준다.
  - 에러가 없을 때만 [등록] 버튼을 활성화하고, 누르면 `Modal.confirm`으로 한 번 더 확인한다.
- **수정 탭**
  - key를 입력해서 불러오면 `Form`에 메타 필드가 채워지고, [저장](POST `/admin/update`)한다.
  - [폐기]: `Modal`에서 대체 key를 입력받아 POST한다.
  - 공개범위: `Radio.Group`(public / allowlist / private)과 `Select mode="tags"`(allowlist 사번)로 설정하고 POST한다.

---

## 9. 로컬 분해 지시문 (운영팀이 raw code 폴더에서 Claude CLI에 사용)

```
이 폴더의 agent 코드를 Agent Hub 등록 패키지로 만들어줘. 규격은 agent-hub-design.md §6.
1. 사내 데이터 조회(DB query/API 호출) 코드는 type: tool, 가공/전처리/시각화/LLM 처리는 type: skill.
2. tool은 data_source, tables, params, output_schema / skill은 input_schema, output_type 추출. 불확실하면 "TODO:".
3. 사람이 읽는 biz_steps 3~7개 작성 후 code_nodes 매핑, 실행 순서대로 code_edges 작성.
4. 비밀번호/토큰/접속문자열은 환경변수 참조로 치환하고 위치를 보고.
5. dist/<workflow_key>/ 에 manifest.yaml + tools/ + skills/ 생성 후 zip.
```

---

## 10. 구현 순서

0. **프로젝트 생성**
   - §3 "프로젝트 생성" 순서대로 `backend/`, `frontend/`를 만든다. `.gitignore`, `.env.example`, `README.md`도 이때 함께 만든다.
   - ✅ 확인: `backend/`에서 `python app.py` → `http://localhost:8000/docs`, `frontend/`에서 `pnpm run dev` → 기본 화면이 뜨는가
1. **뼈대**
   - Backend: `db.py`(테이블 자동 생성) + `/me`
   - Frontend: `main.jsx`(antd ConfigProvider, AG Grid 모듈 등록) + `App.jsx` 메뉴 + `routes/index.jsx` + 빈 페이지 + `api.js`
   - ✅ 확인: 화면에서 `/api/hub/me` 결과가 표시되는가 (Vite proxy 경유)
2. **등록**
   - `importer.py` + `/admin/import`
   - 샘플 zip: `samples/`에 tool 2개, skill 2개, 단계 3개짜리를 만들고, 다시 만들 수 있게 `samples/make_sample.py`도 둔다.
   - Admin 업로드 화면
   - ✅ 확인: 같은 zip을 다시 올리면 에러가 나는가
3. **조회**
   - 목록/상세 API, HubHome, WorkflowDetail(CodeFlow, 단계↔노드 강조, Drawer), ItemPage
4. **권한과 관리**
   - 코드 보기 권한 체크, `/admin/update` · `/deprecate` · `/visibility` + Admin 수정 화면
   - ✅ 확인: `DEV_USER`를 바꿔가며 권한을 확인한다

### env

**backend/.env.example**

```
HOST=0.0.0.0
PORT=8000
RELOAD=1                    # 집 개발용. 회사 운영은 0
SM_USER_HEADER=SM_USER
DEV_USER=12345678           # 집에는 SiteMinder가 없으므로 필수. 회사 운영에서는 비움
ADMIN_USERS=12345678
DB_PATH=./data/hub.db
STORAGE_DIR=./storage
CORS_ORIGINS=               # 프록시를 쓰면 비움. 프론트를 다른 도메인에서 호스팅하면 그 주소
```

**frontend/.env.example**

```
VITE_API_BASE=/api                       # 회사에서 백엔드 주소가 다르면 전체 URL
VITE_PROXY_TARGET=http://localhost:8000  # pnpm run dev 프록시 대상
```

---

## 10-1. 회사 이관 체크리스트

집 환경과 회사 환경이 다른 부분은 **전부 env로 뺀다.** 코드를 고치지 않고 env만 바꿔서 회사에서 돌아가게 하는 것이 목표다.

| 항목 | 집 | 회사 | 처리 방법 |
|---|---|---|---|
| 사용자 식별 | `DEV_USER` | SiteMinder `SM_USER` 헤더 | `DEV_USER`를 비우면 헤더만 사용 |
| 백엔드 주소 | localhost:8000 (Vite proxy) | 사내 cloud 주소 | `VITE_API_BASE`, `VITE_PROXY_TARGET` |
| CORS | 불필요 (proxy) | 프론트와 백엔드 도메인이 다르면 필요 | `CORS_ORIGINS` |
| 패키지 설치 | 공개 npm / PyPI | 사내 미러일 수 있음 | lock 파일(`pnpm-lock.yaml`, `requirements.txt` 버전 고정)을 커밋 |
| 데이터 | 샘플 | 실제 등록 | `data/`, `storage/`는 커밋 금지. 회사에서 새로 시작 |

**이관 순서**

1. `backend/`와 `frontend/`를 각각 회사 git 저장소에 push한다. 루트의 `samples/`와 설계서는 backend 저장소의 `docs/` 아래로 옮기는 것을 권장한다.
2. 회사 기존 프로젝트와 버전을 비교한다 (`react-router-dom`, `antd`, `ag-grid-react`). 다르면 회사 버전에 맞춘다. 문법 차이가 있을 수 있으니 이때 Claude CLI로 점검한다.
3. 각 저장소에서 `.env.example`을 복사해 `.env`를 만들고 회사 값을 넣는다.
4. **HTTP 메서드를 확인한다.** 사내망에서 GET과 POST만 통과하는지, 그리고 multipart 업로드(zip)가 막히지 않는지 먼저 확인한다.
5. 브라우저 개발자도구에서 `/api/hub/me` 응답의 `user_id`가 실제 사번으로 나오는지 확인한다. 이걸로 SiteMinder 헤더가 정상적으로 전달되는지 검증한다.

---

## 11. 지금 안 하는 것

- 버전 관리, 이력
- 요청함, 열람 로그
- 통계 대시보드, 호환 추천
- 코드 하이라이트
- 웹에서 workflow 실행
