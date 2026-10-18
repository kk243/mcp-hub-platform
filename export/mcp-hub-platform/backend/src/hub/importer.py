import hashlib
import io
import json
import re
import shutil
import zipfile
from datetime import datetime

import yaml

from .db import STORAGE_DIR, connect

KEY_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
SECRET_RE = re.compile(r"password|pwd|secret|token", re.IGNORECASE)
FOLDER = {"tool": "tools", "skill": "skills"}


def read_zip(data):
    """zip → (manifest dict, {경로: bytes})"""
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/"):
                raise ValueError(f"허용되지 않는 경로: {name}")
            files[name] = zf.read(info)
    if "manifest.yaml" not in files:
        raise ValueError("manifest.yaml이 없습니다")
    manifest = yaml.safe_load(files.pop("manifest.yaml"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest.yaml 형식이 잘못되었습니다")
    return manifest, files


def item_files(item, files):
    prefix = f"{FOLDER[item['type']]}/{item['key']}/"
    return {p[len(prefix):]: b for p, b in files.items() if p.startswith(prefix)}


def code_hash(file_map):
    h = hashlib.sha256()
    for path in sorted(file_map):
        h.update(path.encode())
        h.update(file_map[path])
    return h.hexdigest()


def check_required(manifest):
    errors = []
    wf = manifest.get("workflow") or {}
    for f in ("key", "name", "family"):
        if not wf.get(f):
            errors.append(f"workflow.{f} 필드가 없습니다")
    if wf.get("key") and not KEY_RE.match(str(wf["key"])):
        errors.append(f"workflow key 형식 오류: {wf['key']}")
    for f in ("biz_steps", "code_nodes", "code_edges"):
        if not isinstance(manifest.get(f), list):
            errors.append(f"{f} 목록이 없습니다")
    for i, it in enumerate(manifest.get("items") or []):
        for f in ("key", "type", "name", "entrypoint", "spec"):
            if not it.get(f):
                errors.append(f"items[{i}].{f} 필드가 없습니다")
        if it.get("type") and it["type"] not in FOLDER:
            errors.append(f"items[{i}].type은 tool 또는 skill이어야 합니다")
        if it.get("key") and not KEY_RE.match(str(it["key"])):
            errors.append(f"item key 형식 오류: {it['key']}")
    return errors


def similar_tools(key, spec, db_items):
    tables = set(spec.get("tables") or [])
    for o in db_items.values():
        if o["type"] != "tool":
            continue
        ospec = json.loads(o["spec"])
        if ospec.get("data_source") == spec.get("data_source") and tables & set(ospec.get("tables") or []):
            yield f"{key}: 비슷한 tool이 있습니다 → {o['key']} ({o['name']})"


def validate(manifest, files):
    """반환: errors, warnings, created, new_items[(item, 파일들, hash)]"""
    errors = check_required(manifest)
    if errors:
        return errors, [], [], []

    warnings, created, new_items = [], [], []
    wf = manifest["workflow"]

    with connect() as conn:
        if conn.execute("SELECT 1 FROM workflows WHERE key=?", (wf["key"],)).fetchone():
            errors.append(f"workflow key가 이미 존재합니다: {wf['key']}")
        db_items = {r["key"]: dict(r) for r in conn.execute("SELECT key, type, name, spec, code_hash FROM items")}
    created.append({"kind": "workflow", "key": wf["key"], "name": wf["name"], "status": "신규"})

    item_types = {}
    for it in manifest.get("items") or []:
        key = it["key"]
        if key in item_types:
            errors.append(f"items에 같은 key가 두 번 있습니다: {key}")
            continue
        item_types[key] = it["type"]

        if it["entrypoint"] not in files or not it["entrypoint"].startswith(f"{FOLDER[it['type']]}/{key}/"):
            errors.append(f"{key}: entrypoint 파일이 zip 안에 없습니다 ({it['entrypoint']})")
            continue
        fmap = item_files(it, files)
        h = code_hash(fmap)

        old = db_items.get(key)
        if old and old["code_hash"] != h:
            errors.append(f"{key}: 같은 key로 다른 코드가 이미 등록되어 있습니다. 로직 변경은 새 key로 등록하세요")
            continue
        if old:
            warnings.append(f"{key}: 이미 등록된 코드와 같아서 기존 것을 재사용합니다")
            created.append({"kind": it["type"], "key": key, "name": it["name"], "status": "재사용"})
            continue

        if it["type"] == "tool":
            warnings.extend(similar_tools(key, it["spec"], db_items))
        for path, content in fmap.items():
            if SECRET_RE.search(content.decode("utf-8", errors="ignore")):
                warnings.append(f"{key}/{path}: password, secret, token 같은 문자열이 있습니다")

        created.append({"kind": it["type"], "key": key, "name": it["name"], "status": "신규"})
        new_items.append((it, fmap, h))

    node_keys = set()
    for n in manifest["code_nodes"]:
        node_keys.add(n.get("key"))
        ref = n.get("ref")
        ref_type = item_types.get(ref) or (db_items[ref]["type"] if ref in db_items else None)
        if not ref_type:
            errors.append(f"node {n.get('key')}: {ref}가 items에도 DB에도 없습니다")
        elif ref_type != n.get("type"):
            errors.append(f"node {n.get('key')}: type({n.get('type')})이 {ref}의 type({ref_type})과 다릅니다")

    for s in manifest["biz_steps"]:
        for nk in s.get("code_nodes") or []:
            if nk not in node_keys:
                errors.append(f"step {s.get('key')}: 정의되지 않은 node {nk}를 참조합니다")
    for e in manifest["code_edges"]:
        if not isinstance(e, list) or len(e) != 2:
            errors.append(f"code_edges 형식 오류: {e}")
            continue
        for nk in e:
            if nk not in node_keys:
                errors.append(f"edge {e}: 정의되지 않은 node {nk}를 참조합니다")

    return errors, warnings, created, new_items


def save(manifest, new_items):
    wf = manifest["workflow"]
    now = datetime.now().isoformat(timespec="seconds")
    written = []
    conn = connect()
    try:
        conn.execute(
            """INSERT INTO workflows (key, name, description, family, team, owner, derived_from, tags,
                                      biz_steps, code_nodes, code_edges, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (wf["key"], wf["name"], wf.get("description"), wf["family"], wf.get("team"), _str(wf.get("owner")),
             wf.get("derived_from"), _json(wf.get("tags") or []), _json(manifest["biz_steps"]),
             _json(manifest["code_nodes"]), _json(manifest["code_edges"]), now),
        )
        for it, fmap, h in new_items:
            conn.execute(
                """INSERT INTO items (key, type, name, description, team, owner, tags, spec, entrypoint,
                                      code_hash, code_visibility, allowlist, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (it["key"], it["type"], it["name"], it.get("description"), it.get("team"), _str(it.get("owner")),
                 _json(it.get("tags") or []), _json(it["spec"]), it["entrypoint"], h,
                 it.get("code_visibility") or "private", _json([str(u) for u in it.get("allowlist") or []]), now),
            )
            target = STORAGE_DIR / it["type"] / it["key"]
            written.append(target)
            for path, content in fmap.items():
                (target / path).parent.mkdir(parents=True, exist_ok=True)
                (target / path).write_bytes(content)
        conn.commit()
    except Exception:
        conn.rollback()
        for d in written:
            shutil.rmtree(d, ignore_errors=True)
        raise
    finally:
        conn.close()


def import_zip(data, dry_run=True):
    try:
        manifest, files = read_zip(data)
    except (zipfile.BadZipFile, yaml.YAMLError, ValueError) as e:
        return {"errors": [f"패키지를 읽을 수 없습니다: {e}"], "warnings": [], "created": []}

    errors, warnings, created, new_items = validate(manifest, files)
    if not errors and not dry_run:
        save(manifest, new_items)
    return {"errors": errors, "warnings": warnings, "created": created}


def _json(v):
    return json.dumps(v, ensure_ascii=False)


def _str(v):
    return None if v is None else str(v)
