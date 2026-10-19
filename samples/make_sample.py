"""테스트용 등록 zip을 만든다.

    python samples/make_sample.py

- wf_chart_monitoring.zip : 차트 이상 감지 workflow (단계 3 = skill 3, tool 8)
"""
import zipfile
from pathlib import Path

import yaml

HERE = Path(__file__).parent

DAILY_TRIGGER = '''from apscheduler.schedulers.blocking import BlockingScheduler


def run(job):
    sched = BlockingScheduler(timezone="Asia/Seoul")
    sched.add_job(job, "cron", hour=7, minute=0)
    sched.start()
'''

CHART_LIST = '''from lake_client import query


def run(user_id):
    sql = "SELECT chart_id, chart_name, item, spec_usl, spec_lsl FROM smartTAS.MY_CHART WHERE user_id = :u"
    return query(sql, u=user_id)
'''

RESPONSE_DATA = '''from lake_client import query


def run(charts, base_date):
    sql = """
        SELECT chart_id, ts, value FROM smartTAS.RESPONSE_DATA
         WHERE chart_id IN :ids AND ts >= :d - INTERVAL '30' DAY
    """
    return query(sql, ids=tuple(c["chart_id"] for c in charts), d=base_date)
'''

RULE_CHECK = '''import pandas as pd


def run(charts, response):
    df = pd.DataFrame(response)
    result = []
    for c in charts:
        v = df[df["chart_id"] == c["chart_id"]]["value"]
        reasons = []
        if v.empty:
            reasons.append("Data 누락")
        else:
            if ((v > c["spec_usl"]) | (v < c["spec_lsl"])).any():
                reasons.append("Spec out")
            center = (c["spec_usl"] + c["spec_lsl"]) / 2
            if (v > center).mean() > 0.9 or (v < center).mean() > 0.9:
                reasons.append("편측")
        result.append({"chart_id": c["chart_id"], "reasons": reasons})
    return result
'''

ML_TREND_SHIFT = '''import joblib
import pandas as pd

MODEL = joblib.load("models/trend_shift.pkl")


def run(response):
    df = pd.DataFrame(response)
    feats = df.groupby("chart_id")["value"].agg(["mean", "std", "min", "max"]).reset_index()
    feats["trend_shift"] = MODEL.predict(feats[["mean", "std", "min", "max"]])
    return feats[["chart_id", "trend_shift"]].to_dict("records")
'''

NG_SUMMARY = '''def run(charts, rule_result, ml_result):
    info = {c["chart_id"]: c for c in charts}
    shift = {r["chart_id"]: r["trend_shift"] for r in ml_result}
    rows = []
    for r in rule_result:
        reasons = r["reasons"] + (["Trend Shift"] if shift.get(r["chart_id"]) else [])
        if reasons:
            c = info[r["chart_id"]]
            rows.append({"chart_id": c["chart_id"], "chart_name": c["chart_name"], "item": c["item"],
                         "ng_reason": ", ".join(reasons)})
    return rows
'''

SAVE_POSTGRES = '''import os
from datetime import date

import psycopg2


def run(ng_rows):
    with psycopg2.connect(os.environ["PG_DSN"]) as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO chart_ng (base_date, chart_id, chart_name, item, ng_reason) VALUES (%s, %s, %s, %s, %s)",
            [(date.today(), r["chart_id"], r["chart_name"], r["item"], r["ng_reason"]) for r in ng_rows],
        )
    return len(ng_rows)
'''

CUBE_SEND = '''import os

import requests


def run(ng_rows, channel_id):
    lines = [f"[이상 Chart {len(ng_rows)}건]"] + [f"- {r['chart_name']}: {r['ng_reason']}" for r in ng_rows]
    resp = requests.post(os.environ["CUBE_WEBHOOK"], json={"channel": channel_id, "text": "\\n".join(lines)},
                         timeout=30)
    resp.raise_for_status()
    return resp.json()
'''

TREND_SKILL = '''from tools.tool_chart_list.main import run as chart_list
from tools.tool_response_data.main import run as response_data


def run(user_id, base_date):
    charts = chart_list(user_id)
    return charts, response_data(charts, base_date)
'''

CLASSIFY_SKILL = '''from tools.tool_ml_trend_shift.main import run as ml_trend_shift
from tools.tool_ng_summary.main import run as ng_summary
from tools.tool_rule_check.main import run as rule_check


def run(charts, response):
    return ng_summary(charts, rule_check(charts, response), ml_trend_shift(response))
'''

CUBE_SKILL = '''from tools.tool_cube_send.main import run as cube_send
from tools.tool_save_postgres.main import run as save_postgres


def run(ng_rows, channel_id):
    save_postgres(ng_rows)
    return cube_send(ng_rows, channel_id)
'''

OWNER = {"team": "품질팀", "owner": "12345678"}
CHART_COLS = [{"name": "chart_id", "type": "str"}, {"name": "chart_name", "type": "str"},
              {"name": "item", "type": "str"}]
NG_COLS = CHART_COLS + [{"name": "ng_reason", "type": "str"}]


def tool(key, name, description, tags, data_source, tables, params, output_schema, visibility="public"):
    return {"key": key, "type": "tool", "name": name, "description": description, **OWNER, "tags": tags,
            "entrypoint": f"tools/{key}/main.py", "code_visibility": visibility,
            "spec": {"data_source": data_source, "tables": tables, "params": params, "output_schema": output_schema}}


def skill(key, name, description, tags, input_schema, output_type):
    return {"key": key, "type": "skill", "name": name, "description": description, **OWNER, "tags": tags,
            "entrypoint": f"skills/{key}/main.py", "code_visibility": "public",
            "spec": {"input_schema": input_schema, "output_type": output_type, "prompt": None}}


TOOLS = [
    tool("tool_daily_trigger", "Trigger", "매일 7시 스케줄링", ["스케줄"], "Scheduler", [],
         [{"name": "job", "type": "callable", "required": True}], []),
    tool("tool_chart_list", "Chart List 조회", "Lake에 접근하여 smartTAS-My Chart에서 List를 검색한다",
         ["Lake", "smartTAS"], "Lake", ["smartTAS.MY_CHART"],
         [{"name": "user_id", "type": "str", "required": True}],
         CHART_COLS + [{"name": "spec_usl", "type": "float"}, {"name": "spec_lsl", "type": "float"}]),
    tool("tool_response_data", "Response Data 조회",
         "List 조회로 얻은 Chart 정보를 바탕으로 Lake 접근하여 Response Data를 검색한다",
         ["Lake", "smartTAS"], "Lake", ["smartTAS.RESPONSE_DATA"],
         [{"name": "charts", "type": "list[dict]", "required": True},
          {"name": "base_date", "type": "date", "required": True}],
         [{"name": "chart_id", "type": "str"}, {"name": "ts", "type": "datetime"}, {"name": "value", "type": "float"}]),
    tool("tool_rule_check", "이상 분류-Rule", "Chart 별로 Rule 기반 검증(Spec out, Data 누락, 편측)",
         ["이상분류", "Rule"], "Rule", [],
         [{"name": "charts", "type": "list[dict]", "required": True},
          {"name": "response", "type": "list[dict]", "required": True}],
         [{"name": "chart_id", "type": "str"}, {"name": "reasons", "type": "list[str]"}]),
    tool("tool_ml_trend_shift", "이상 분류-ML", "ML 모델로 Trend Shift 여부를 판단", ["이상분류", "ML"], "ML Model", [],
         [{"name": "response", "type": "list[dict]", "required": True}],
         [{"name": "chart_id", "type": "str"}, {"name": "trend_shift", "type": "bool"}], visibility="private"),
    tool("tool_ng_summary", "Data 정리", "NG Chart에 대해서 차트 정보와 NG 사유를 정리", ["정리"], "Python", [],
         [{"name": "charts", "type": "list[dict]", "required": True},
          {"name": "rule_result", "type": "list[dict]", "required": True},
          {"name": "ml_result", "type": "list[dict]", "required": True}], NG_COLS),
    tool("tool_save_postgres", "Data 저장", "날짜, Chart 정보, NG 사유 등의 Data를 PostgreSQL DB에 저장",
         ["PostgreSQL"], "PostgreSQL", ["chart_ng"],
         [{"name": "ng_rows", "type": "list[dict]", "required": True}], [{"name": "count", "type": "int"}]),
    tool("tool_cube_send", "Cube 공유", "정리된 Data를 Cube 채널에 전송", ["Cube", "알림"], "CUBE", [],
         [{"name": "ng_rows", "type": "list[dict]", "required": True},
          {"name": "channel_id", "type": "str", "required": True}], []),
]

SKILLS = [
    skill("skill_trend_query", "Trend 조회", "My Chart List와 Response Data를 조회한다", ["Trend"],
          [{"name": "user_id", "type": "str"}, {"name": "base_date", "type": "date"}], "표"),
    skill("skill_abnormal_classify", "이상 Chart 분류", "Rule과 ML로 이상 Chart를 분류하고 NG 사유를 정리한다",
          ["이상분류"], [{"name": "chart_id", "type": "str"}, {"name": "value", "type": "float"}], "표"),
    skill("skill_cube_share", "Cube 공유", "NG Chart를 DB에 저장하고 Cube 채널에 공유한다", ["Cube"], NG_COLS, "표"),
]

# 업무 단계 하나 = skill 하나, 단계 안의 code node = tool
STEPS = [
    ("s1", "skill_trend_query", ["tool_daily_trigger", "tool_chart_list", "tool_response_data"]),
    ("s2", "skill_abnormal_classify", ["tool_rule_check", "tool_ml_trend_shift", "tool_ng_summary"]),
    ("s3", "skill_cube_share", ["tool_save_postgres", "tool_cube_send"]),
]
NODES = [t["key"] for t in TOOLS]
SKILL_BY_KEY = {s["key"]: s for s in SKILLS}

MANIFEST = {
    "workflow": {
        "key": "wf_chart_monitoring", "name": "이상 Chart 감지 및 Cube 공유", "family": "품질분석",
        "description": "매일 My Chart의 Trend를 조회해 이상 Chart를 분류하고 Cube로 공유한다",
        **OWNER, "tags": ["smartTAS", "이상감지", "Cube"],
    },
    "biz_steps": [
        {"key": k, "title": SKILL_BY_KEY[s]["name"], "description": SKILL_BY_KEY[s]["description"],
         "skill": s, "code_nodes": [f"n{NODES.index(t) + 1}" for t in tools]}
        for k, s, tools in STEPS
    ],
    "code_nodes": [{"key": f"n{i + 1}", "type": "tool", "ref": key} for i, key in enumerate(NODES)],
    "code_edges": [[f"n{i}", f"n{i + 1}"] for i in range(1, len(NODES))],
    "items": TOOLS + SKILLS,
}

CODE = {
    "tools/tool_daily_trigger/main.py": DAILY_TRIGGER,
    "tools/tool_chart_list/main.py": CHART_LIST,
    "tools/tool_response_data/main.py": RESPONSE_DATA,
    "tools/tool_rule_check/main.py": RULE_CHECK,
    "tools/tool_ml_trend_shift/main.py": ML_TREND_SHIFT,
    "tools/tool_ng_summary/main.py": NG_SUMMARY,
    "tools/tool_save_postgres/main.py": SAVE_POSTGRES,
    "tools/tool_cube_send/main.py": CUBE_SEND,
    "skills/skill_trend_query/main.py": TREND_SKILL,
    "skills/skill_abnormal_classify/main.py": CLASSIFY_SKILL,
    "skills/skill_cube_share/main.py": CUBE_SKILL,
}


def write_zip(name, manifest, files):
    with zipfile.ZipFile(HERE / name, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.yaml", yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False))
        for path, content in files.items():
            zf.writestr(path, content)
    print("created", HERE / name)


if __name__ == "__main__":
    write_zip("wf_chart_monitoring.zip", MANIFEST, CODE)
