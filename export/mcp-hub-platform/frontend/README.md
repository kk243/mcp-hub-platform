# Agent Hub — frontend

React 18 + antd v4 + AG Grid Community + @xyflow/react. Node 20.8.1 기준.

## 실행

```bash
pnpm install
cp .env.example .env
pnpm run dev
```

http://localhost:5173 — `/api` 요청은 `VITE_PROXY_TARGET`(기본 http://localhost:8000)으로 프록시된다.
backend가 먼저 떠 있어야 한다.

## 화면

| 경로 | 화면 |
|---|---|
| `/hub/workflows`, `/hub/tools`, `/hub/skills` | 메뉴별 목록과 검색. 표/카드 전환은 `?view=card` |
| `/hub/workflows/:key` | 업무 단계 + code workflow 그래프. 선택 상태는 `?step=&node=` |
| `/hub/tools/:key`, `/hub/skills/:key` | tool / skill 상세 |
| `/hub/admin` | zip 업로드, 메타 수정 (관리자만 메뉴 노출) |

## 구조

```
src/main.jsx           antd ConfigProvider, AG Grid 모듈 등록, 라우터
src/App.jsx            상단 메뉴 레이아웃
src/routes/index.jsx   route 배열
src/pages/hub/         화면, api.js, Grid.jsx(AG Grid 공통 설정)
```

## 버전 규칙

- 버전은 `pnpm-lock.yaml` 그대로 쓴다. 임의로 올리지 않는다.
- Vite 7 이상과 ESLint 9는 Node 20.9 이상이 필요해서 쓰지 않는다.
- 표는 AG Grid Community만 쓴다 (`ag-grid-enterprise` 금지).

## env

| 이름 | 설명 |
|---|---|
| `VITE_API_BASE` | API 기본 경로. 백엔드가 다른 주소면 전체 URL |
| `VITE_PROXY_TARGET` | `pnpm run dev` 프록시 대상 |
