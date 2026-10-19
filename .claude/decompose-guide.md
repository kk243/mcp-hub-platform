# Raw code 분해 가이드 (운영팀용)

> AI agent 개발자에게서 받은 raw code를 Agent Hub 등록 zip으로 만드는 방법을 정리한다.
> zip 규격은 `agent-hub-design.md` §6, 기본 지시문은 §9를 따른다. 이 문서는 그 사이에서 **어떻게 나눌지**를 판단하는 기준이다.

---

## 0. 전체 흐름

```
1. 개발자에게서 raw code + 메타 정보 받기
2. 허브의 기존 item 목록 받기           (GET /items)
3. Claude CLI로 분해                    (§5 지시문)
4. dry_run 검증 → 에러 0개까지 수정      (POST /admin/import?dry_run=1)
5. 사람이 원본과 비교해 검토             (§6 체크리스트)
6. 업로드                               (POST /admin/import?dry_run=0)
```

---

## 1. 개발자에게서 받을 것

코드만 받으면 Claude가 추측으로 채우게 된다. 아래는 **코드에 없는 정보**이므로 반드시 사람에게 받는다.

| 항목 | 예시 | 비고 |
|---|---|---|
| raw code 폴더 | `bad_lot_agent/` | 실행 가능한 상태 그대로 |
| 실행 방법 | `python main.py --start 2026-01-01` | 진입점과 입력값 확인용 |
| team / owner(사번) | 품질팀 / `12345678` | |
| 코드 공개범위 | public / allowlist / private | allowlist면 사번 목록 |
| family | 품질분석 | 모르면 운영팀이 정한다 |
| derived_from | `wf_bad_lot_cause` | 기존 workflow를 고쳐 만든 경우만 |
| 업무 설명 | "불량 LOT 원인 설비를 찾는다" | biz_steps 작성의 근거 |

---

## 2. Tool / Skill 나누는 기준

### 한 줄 규칙

- **Tool** = 사내 데이터를 **가져오는** 코드. DB query, 사내 API 호출.
- **Skill** = 가져온 데이터를 **다루는** 코드. 전처리, 집계, 시각화, 리포트, LLM 호출.

### 판단표

| 코드가 하는 일 | 분류 |
|---|---|
| `SELECT ...` 실행, `requests.get(사내 API)` | tool |
| 파일 서버/공유폴더에서 원천 데이터 읽기 | tool |
| pandas 집계, 필터, join, 이상치 탐지 | skill |
| 차트, markdown/HTML 리포트 생성 | skill |
| LLM 호출 (prompt + 결과 정리) | skill (prompt는 `spec.prompt`에) |
| query 후 바로 컬럼 이름만 바꾸는 정도 | tool에 포함 (따로 떼지 않는다) |
| query + 무거운 가공이 한 함수에 섞임 | **경계에서 잘라** tool 1 + skill 1 |

### 크기 기준

- **하나의 item = 하나의 `run()` 함수 = 한 가지 일.** 이름을 "~ 조회", "~ 전처리", "~ 리포트"처럼 한 동사로 붙일 수 있어야 한다.
- **너무 잘게 나누지 않는다.** 다른 workflow에서 따로 재사용될 가능성이 없는 3줄짜리 가공은 앞뒤 skill에 붙인다.
- **tool은 테이블/API 단위로 나눈다.** 재사용이 가장 많이 일어나는 곳이 tool이다. 서로 다른 data_source를 한 tool에 섞지 않는다.
- 판단이 애매하면 **"다른 팀이 이것만 가져다 쓸 일이 있는가?"** 를 묻는다. 있으면 분리한다.

---

## 3. 기존 item 재사용 (가장 중요)

허브의 목적은 중복개발을 막는 것이다. 새 item을 만들기 전에 이미 있는지부터 본다.

1. 분해 전에 `GET /items` 결과를 `existing_items.json`으로 저장해 Claude에게 같이 준다.
2. 새 tool의 `data_source`가 같고 `tables`가 겹치는 기존 tool이 있으면:
   - 하는 일이 같다 → **새 item을 만들지 않는다.** `code_nodes`에 기존 key를 `ref`로만 건다. `items`에는 넣지 않는다.
   - 조건/컬럼이 조금 다르다 → 새 key로 등록한다. 기존 key를 그대로 쓰면 code_hash가 달라서 importer 에러 5번이 난다.
3. 새로 만든 이유를 `description`에 한 줄 남긴다. 예: "tool_bad_lot_query에 설비 조건을 추가한 버전".

---

## 4. 코드 자르기 규칙

- **로직은 바꾸지 않는다.** 함수 경계만 옮긴다. 리팩토링, 변수명 정리, 성능 개선은 하지 않는다.
- 각 item은 `tools/<key>/main.py` 또는 `skills/<key>/main.py`에 `def run(...)` 하나를 진입점으로 둔다.
- 잘린 지점의 **데이터 형태를 맞춘다.** 앞 item의 `output_schema`와 뒤 item의 `input_schema`가 이어져야 한다. 이것이 `code_edges`가 된다.
- 전역 변수, 공용 유틸에 의존하면 해당 item 폴더 안으로 복사한다. item끼리 import하지 않는다.
- prompt 문자열은 skill 폴더 안의 별도 파일(`prompt.py` 등)로 두고, `spec.prompt`에도 같은 내용을 적는다.
- **비밀값 처리**: 비밀번호, 토큰, 접속문자열이 코드에 박혀 있으면 `os.environ["..."]`로 바꾸고 바꾼 위치를 보고한다. 환경변수 이름 때문에 importer가 "password 같은 문자열" 경고를 낼 수 있는데, 이 경고는 확인만 하고 넘어가도 된다.

### key 이름 규칙

- `tool_<대상>_<동작>`: `tool_bad_lot_query`, `tool_equipment_history`
- `skill_<대상>_<동작>`: `skill_outlier_preprocess`, `skill_llm_summary`
- `wf_<업무>[_<팀>]`: `wf_bad_lot_cause`, `wf_bad_lot_cause_teamA`
- 소문자 + 밑줄만 쓴다. 한 번 등록한 key는 바꿀 수 없다.

---

## 5. biz_steps / code_nodes / code_edges 작성

- **biz_steps**는 현업이 읽는 문서다. 3~7단계로, 코드 용어 없이 업무 용어로 쓴다.
  - 좋음: "불량 데이터 조회", "원인 후보 정리"
  - 나쁨: "SQL 실행", "DataFrame merge"
- 각 step은 실행되는 node를 `code_nodes`로 가리킨다. 모든 node는 최소 한 step에 속해야 한다.
- **code_edges**는 데이터가 흐르는 방향이다. 실행 순서가 아니라 **"누구의 출력을 누가 받는가"** 로 그린다. 병렬로 조회하는 tool 두 개는 서로 edge가 없다.

### Claude CLI 지시문 (raw code 폴더에서 실행)

```
이 폴더의 agent 코드를 Agent Hub 등록 패키지로 만들어줘.
규격은 agent-hub-design.md §6, 분해 기준은 decompose-guide.md를 따른다.

메타: team=<팀>, owner=<사번>, code_visibility=<public|allowlist|private>,
      allowlist=[<사번>...], family=<family>, derived_from=<key 또는 없음>
기존 item 목록: existing_items.json

1. decompose-guide.md §2 기준으로 tool/skill을 나누고, §3에 따라 기존 item은 ref만 건다.
2. 로직은 바꾸지 말고 함수 경계만 나눈다. 각 item은 main.py의 run()이 진입점이다.
3. tool은 data_source, tables, params, output_schema / skill은 input_schema, output_type, prompt를 채운다.
   코드에서 확실히 알 수 없는 값은 "TODO:"로 남긴다.
4. biz_steps 3~7개를 업무 용어로 쓰고 code_nodes, code_edges를 매핑한다.
5. 비밀값은 환경변수로 바꾸고 위치를 보고한다.
6. dist/<workflow_key>/ 에 manifest.yaml + tools/ + skills/ 를 만들고 zip으로 묶는다.
7. 마지막에 보고: 새 item 목록, 재사용한 기존 item, TODO 목록, 원본에서 바꾼 부분.
```

---

## 6. 업로드 전 체크리스트

dry_run 에러가 0개여도 아래는 사람이 본다.

- [ ] `TODO:`가 하나도 남지 않았다.
- [ ] 잘라낸 코드를 원본과 diff해서 로직이 바뀌지 않았다.
- [ ] 재사용한 기존 item이 정말 같은 일을 한다 (이름만 비슷한 게 아니다).
- [ ] 비슷한 tool 경고가 났다면, 새로 만든 이유가 description에 있다.
- [ ] 비밀값이 코드에 남아 있지 않다.
- [ ] biz_steps만 읽어도 업무 흐름이 이해된다.
- [ ] 공개범위가 개발자에게 받은 값과 같다.
- [ ] (가능하면) 분해한 코드를 순서대로 실행해서 원본과 같은 결과가 나온다.
