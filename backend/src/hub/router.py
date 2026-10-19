import json
import os

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from . import importer
from .db import STORAGE_DIR, connect, fetch_all, fetch_one, init_db

router = APIRouter(prefix="/api/hub", tags=["hub"])
init_db()

USER_HEADER = os.getenv("SM_USER_HEADER", "SM_USER")
DEV_USER = os.getenv("DEV_USER", "")
ADMIN_USERS = {u.strip() for u in os.getenv("ADMIN_USERS", "").split(",") if u.strip()}

TABLES = {"workflow": "workflows", "item": "items"}
EDITABLE = {"name", "description", "tags", "team", "owner"}
VISIBILITIES = {"public", "allowlist", "private"}


def current_user(request: Request):
    user = request.headers.get(USER_HEADER) or DEV_USER
    if not user:
        raise HTTPException(401, "사용자를 확인할 수 없습니다")
    return user



def can_view_code(item, user):
    return (
        user in ADMIN_USERS
        or user == item["owner"]
        or item["code_visibility"] == "public"
        or (item["code_visibility"] == "allowlist" and user in item["allowlist"])
    )


def used_by(item_key, workflows):
    return [w for w in workflows if any(n.get("ref") == item_key for n in w["code_nodes"])]


@router.get("/me")
def me(user: str = Depends(current_user)):
    return {"user_id": user, "is_admin": user in ADMIN_USERS}


@router.get("/workflows")
def list_workflows(q: str = "", family: str = "", team: str = ""):
    sql = "SELECT * FROM workflows WHERE 1=1"
    params = []
    if q:
        sql += " AND (name LIKE ? OR description LIKE ? OR tags LIKE ?)"
        params += [f"%{q}%"] * 3
    if family:
        sql += " AND family = ?"
        params.append(family)
    if team:
        sql += " AND team = ?"
        params.append(team)
    rows = fetch_all(sql + " ORDER BY family, name", params)
    for w in rows:
        w["step_count"] = len(w.pop("biz_steps"))
        del w["code_nodes"], w["code_edges"]
    return rows


@router.get("/workflows/{key}")
def get_workflow(key: str):
    wf = fetch_one("SELECT * FROM workflows WHERE key = ?", (key,))
    if not wf:
        raise HTTPException(404, "workflow가 없습니다")

    refs = [n["ref"] for n in wf["code_nodes"]]
    marks = ",".join("?" * len(refs))
    items = {i["key"]: i for i in fetch_all(f"SELECT * FROM items WHERE key IN ({marks})", refs)}
    for n in wf["code_nodes"]:
        item = items.get(n["ref"], {})
        spec = item.get("spec") or {}
        n.update(name=item.get("name", n["ref"]), data_source=spec.get("data_source"),
                 output_type=spec.get("output_type"), deprecated=item.get("deprecated", 0))

    wf["siblings"] = fetch_all(
        "SELECT key, name, team, derived_from, deprecated FROM workflows WHERE family = ? AND key != ? ORDER BY name",
        (wf["family"], key),
    )
    return wf


@router.get("/items")
def list_items(type: str = "", q: str = "", data_source: str = ""):
    sql = "SELECT * FROM items WHERE 1=1"
    params = []
    if type:
        sql += " AND type = ?"
        params.append(type)
    if q:
        sql += " AND (name LIKE ? OR description LIKE ? OR tags LIKE ? OR spec LIKE ?)"
        params += [f"%{q}%"] * 4
    if data_source:
        sql += " AND json_extract(spec, '$.data_source') = ?"
        params.append(data_source)
    rows = fetch_all(sql + " ORDER BY name", params)

    workflows = fetch_all("SELECT key, code_nodes FROM workflows")
    for i in rows:
        i["used_by_count"] = len(used_by(i["key"], workflows))
    return rows


@router.get("/items/{key}")
def get_item(key: str, user: str = Depends(current_user)):
    item = fetch_one("SELECT * FROM items WHERE key = ?", (key,))
    if not item:
        raise HTTPException(404, "item이 없습니다")
    workflows = fetch_all("SELECT key, name, family, team, deprecated, code_nodes FROM workflows ORDER BY family, name")
    item["used_by"] = [{k: v for k, v in w.items() if k != "code_nodes"} for w in used_by(key, workflows)]
    item["can_view_code"] = can_view_code(item, user)
    return item


@router.get("/items/{key}/code")
def get_item_code(key: str, user: str = Depends(current_user)):
    item = fetch_one("SELECT * FROM items WHERE key = ?", (key,))
    if not item:
        raise HTTPException(404, "item이 없습니다")
    if not can_view_code(item, user):
        raise HTTPException(403, "원 개발자의 허락이 필요합니다")

    root = STORAGE_DIR / item["type"] / key
    files = [
        {"path": p.relative_to(root).as_posix(), "content": p.read_text("utf-8", errors="replace")}
        for p in sorted(root.rglob("*")) if p.is_file()
    ]
    return {"entrypoint": item["entrypoint"], "files": files}


@router.post("/admin/import")
async def admin_import(dry_run: int = 1, file: UploadFile = File(...)):
    return importer.import_zip(await file.read(), dry_run=bool(dry_run))


class UpdateBody(BaseModel):
    target: str
    key: str
    fields: dict


class DeprecateBody(BaseModel):
    target: str
    key: str
    replaced_by: str | None = None


class VisibilityBody(BaseModel):
    key: str
    code_visibility: str
    allowlist: list[str] = []


def _table(target):
    if target not in TABLES:
        raise HTTPException(400, "target은 workflow 또는 item이어야 합니다")
    return TABLES[target]


def _execute(sql, params):
    with connect() as conn:
        if conn.execute(sql, params).rowcount == 0:
            raise HTTPException(404, "대상이 없습니다")


@router.post("/admin/update")
def admin_update(body: UpdateBody):
    table = _table(body.target)
    bad = set(body.fields) - EDITABLE
    if bad or not body.fields:
        raise HTTPException(400, f"수정할 수 없는 필드: {', '.join(sorted(bad)) or '(없음)'}")
    if "tags" in body.fields and not isinstance(body.fields["tags"], list):
        raise HTTPException(400, "tags는 목록이어야 합니다")

    values = {k: json.dumps(v, ensure_ascii=False) if k == "tags" else v for k, v in body.fields.items()}
    sets = ", ".join(f"{k} = ?" for k in values)
    _execute(f"UPDATE {table} SET {sets} WHERE key = ?", [*values.values(), body.key])
    return {"ok": True}


@router.post("/admin/deprecate")
def admin_deprecate(body: DeprecateBody):
    table = _table(body.target)
    _execute(f"UPDATE {table} SET deprecated = 1, replaced_by = ? WHERE key = ?", (body.replaced_by or None, body.key))
    return {"ok": True}


@router.post("/admin/visibility")
def admin_visibility(body: VisibilityBody):
    if body.code_visibility not in VISIBILITIES:
        raise HTTPException(400, "code_visibility는 public, allowlist, private 중 하나여야 합니다")
    _execute("UPDATE items SET code_visibility = ?, allowlist = ? WHERE key = ?",
             (body.code_visibility, json.dumps(body.allowlist), body.key))
    return {"ok": True}
