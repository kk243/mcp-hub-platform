"""테스트용 등록 zip을 만든다.

    python samples/make_sample.py

- wf_bad_lot_cause.zip        : 원본 workflow (tool 2, skill 2, 단계 3)
- wf_bad_lot_cause_teamA.zip  : A팀 변형. tool 2개는 재사용, 리포트 skill만 새로 등록
"""
import zipfile
from pathlib import Path

import yaml

HERE = Path(__file__).parent

BAD_LOT_QUERY = '''import os

import oracledb


def run(start_date, end_date):
    conn = oracledb.connect(dsn=os.environ["MES_DSN"], user=os.environ["MES_USER"],
                            password=os.environ["MES_PASSWORD"])
    sql = """
        SELECT b.lot_id, b.qty, h.step_id
          FROM MES.BAD_LOT b JOIN MES.LOT_HIST h ON b.lot_id = h.lot_id
         WHERE b.bad_date BETWEEN :s AND :e
    """
    with conn.cursor() as cur:
        cur.execute(sql, s=start_date, e=end_date)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
'''

EQUIPMENT_HISTORY = '''import requests

EQP_API = "http://eqp-api.internal/history"


def run(lot_ids):
    resp = requests.post(EQP_API, json={"lot_ids": lot_ids}, timeout=30)
    resp.raise_for_status()
    return resp.json()["rows"]
'''

OUTLIER = '''import pandas as pd


def run(bad_lots, eqp_history):
    df = pd.DataFrame(bad_lots).merge(pd.DataFrame(eqp_history), on="lot_id")
    stats = df.groupby("eqp_id")["qty"].agg(["sum", "count"]).reset_index()
    limit = stats["sum"].mean() + 2 * stats["sum"].std()
    return stats[stats["sum"] > limit].to_dict("records")
'''

SUMMARY_REPORT = '''def run(candidates):
    lines = ["# 불량 원인 후보", ""]
    for c in candidates:
        lines.append(f"- {c['eqp_id']}: 불량 {c['sum']}건 / LOT {c['count']}개")
    return "\\n".join(lines)
'''

LLM_REPORT = '''from llm_client import chat

from .prompt import PROMPT


def run(candidates):
    return chat(PROMPT.format(candidates=candidates))
'''

LLM_PROMPT = 'PROMPT = """다음 설비별 불량 집계를 보고 원인 후보를 3줄로 요약해줘.\\n{candidates}"""\n'

TOOLS = [
    {
        "key": "tool_bad_lot_query", "type": "tool", "name": "불량 LOT 조회",
        "description": "기간 내 불량 LOT과 공정 이력을 조회한다", "team": "품질팀", "owner": "12345678",
        "tags": ["불량", "MES"], "entrypoint": "tools/tool_bad_lot_query/main.py",
        "code_visibility": "allowlist", "allowlist": ["23456789"],
        "spec": {
            "data_source": "MES", "tables": ["MES.BAD_LOT", "MES.LOT_HIST"],
            "params": [{"name": "start_date", "type": "date", "required": True},
                       {"name": "end_date", "type": "date", "required": True}],
            "output_schema": [{"name": "lot_id", "type": "str"}, {"name": "qty", "type": "int"},
                              {"name": "step_id", "type": "str"}],
        },
    },
    {
        "key": "tool_equipment_history", "type": "tool", "name": "설비 이력 조회",
        "description": "LOT이 거쳐간 설비 이력을 조회한다", "team": "설비팀", "owner": "34567890",
        "tags": ["설비"], "entrypoint": "tools/tool_equipment_history/main.py", "code_visibility": "public",
        "spec": {
            "data_source": "EQP_API", "tables": ["EQP.HISTORY"],
            "params": [{"name": "lot_ids", "type": "list[str]", "required": True}],
            "output_schema": [{"name": "lot_id", "type": "str"}, {"name": "eqp_id", "type": "str"},
                              {"name": "track_in", "type": "datetime"}],
        },
    },
]

OUTLIER_SKILL = {
    "key": "skill_outlier_preprocess", "type": "skill", "name": "이상치 전처리",
    "description": "설비별 불량 수를 집계하고 평균+2σ를 넘는 설비를 고른다", "team": "품질팀", "owner": "12345678",
    "tags": ["전처리"], "entrypoint": "skills/skill_outlier_preprocess/main.py", "code_visibility": "private",
    "spec": {"input_schema": [{"name": "lot_id", "type": "str"}, {"name": "qty", "type": "int"},
                              {"name": "eqp_id", "type": "str"}],
             "output_type": "table", "prompt": None},
}

BASE = {
    "workflow": {
        "key": "wf_bad_lot_cause", "name": "불량 LOT 원인 분석", "family": "품질분석",
        "description": "불량 LOT과 설비 이력을 묶어 원인 설비 후보를 찾는다",
        "team": "품질팀", "owner": "12345678", "tags": ["불량", "원인분석"],
    },
    "biz_steps": [
        {"key": "s1", "title": "불량 데이터 조회", "description": "기간 내 불량 LOT과 설비 이력을 가져온다",
         "code_nodes": ["n1", "n2"]},
        {"key": "s2", "title": "원인 후보 정리", "description": "설비별로 모아 이상치를 고른다", "code_nodes": ["n3"]},
        {"key": "s3", "title": "리포트 생성", "description": "후보 설비를 리포트로 정리한다", "code_nodes": ["n4"]},
    ],
    "code_nodes": [
        {"key": "n1", "type": "tool", "ref": "tool_bad_lot_query"},
        {"key": "n2", "type": "tool", "ref": "tool_equipment_history"},
        {"key": "n3", "type": "skill", "ref": "skill_outlier_preprocess"},
        {"key": "n4", "type": "skill", "ref": "skill_summary_report"},
    ],
    "code_edges": [["n1", "n3"], ["n2", "n3"], ["n3", "n4"]],
    "items": TOOLS + [
        OUTLIER_SKILL,
        {
            "key": "skill_summary_report", "type": "skill", "name": "요약 리포트",
            "description": "원인 후보를 markdown 리포트로 만든다", "team": "품질팀", "owner": "12345678",
            "tags": ["리포트"], "entrypoint": "skills/skill_summary_report/main.py", "code_visibility": "public",
            "spec": {"input_schema": [{"name": "eqp_id", "type": "str"}, {"name": "sum", "type": "int"},
                                      {"name": "count", "type": "int"}],
                     "output_type": "markdown", "prompt": None},
        },
    ],
}

TEAM_A = {
    "workflow": {
        "key": "wf_bad_lot_cause_teamA", "name": "불량 LOT 원인 분석 (A팀형)", "family": "품질분석",
        "description": "원본 흐름에서 리포트를 LLM 요약으로 바꾼 A팀 변형",
        "team": "A팀", "owner": "23456789", "derived_from": "wf_bad_lot_cause", "tags": ["불량", "LLM"],
    },
    "biz_steps": BASE["biz_steps"][:2] + [
        {"key": "s3", "title": "LLM 요약", "description": "후보 설비를 LLM으로 요약한다", "code_nodes": ["n4"]},
    ],
    "code_nodes": BASE["code_nodes"][:3] + [{"key": "n4", "type": "skill", "ref": "skill_llm_summary"}],
    "code_edges": BASE["code_edges"],
    "items": [
        {
            "key": "skill_llm_summary", "type": "skill", "name": "LLM 원인 요약",
            "description": "설비별 집계를 LLM으로 3줄 요약한다", "team": "A팀", "owner": "23456789",
            "tags": ["LLM", "리포트"], "entrypoint": "skills/skill_llm_summary/main.py", "code_visibility": "private",
            "spec": {"input_schema": [{"name": "eqp_id", "type": "str"}, {"name": "sum", "type": "int"}],
                     "output_type": "text",
                     "prompt": "다음 설비별 불량 집계를 보고 원인 후보를 3줄로 요약해줘.\n{candidates}"},
        },
    ],
}


def write_zip(name, manifest, files):
    with zipfile.ZipFile(HERE / name, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.yaml", yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False))
        for path, content in files.items():
            zf.writestr(path, content)
    print("created", HERE / name)


if __name__ == "__main__":
    write_zip("wf_bad_lot_cause.zip", BASE, {
        "tools/tool_bad_lot_query/main.py": BAD_LOT_QUERY,
        "tools/tool_equipment_history/main.py": EQUIPMENT_HISTORY,
        "skills/skill_outlier_preprocess/main.py": OUTLIER,
        "skills/skill_summary_report/main.py": SUMMARY_REPORT,
    })
    write_zip("wf_bad_lot_cause_teamA.zip", TEAM_A, {
        "skills/skill_llm_summary/main.py": LLM_REPORT,
        "skills/skill_llm_summary/prompt.py": LLM_PROMPT,
    })
