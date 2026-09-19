#!/usr/bin/env python3
"""Orchestrator yardımcıları — harici bağımlılık yok (PyYAML varsa kullanılır).

Kullanım:
  orch.py body   deploy.yml [ref] [env]   → kayıt/deploy gövdesi (JSON)
  orch.py table  < yanit.json             → deployment listesini tablo olarak yaz
  orch.py field  <ad> < yanit.json        → tek alanı yaz (id, status ...)

Yanıt biçimine toleranslıdır: [...], {"deployments": [...]}, {"data": [...]}
veya n8n'in [{"json": {...}}] biçimi.
"""
import json
import sys

# Orchestrator alan adları projeden projeye değişebildiği için her sütun için
# sırayla denenecek anahtarlar tutulur. Yeni bir ad çıkarsa buraya eklemek yeter.
FIELDS = {
    "id":        ("id", "deployment_id", "uuid", "pk"),
    "project":   ("project", "project_name", "name"),
    "server":    ("server", "runner", "target", "host", "machine"),
    "status":    ("status", "state", "result"),
    "trigger":   ("trigger", "triggered_by", "source", "event"),
    "timestamp": ("timestamp", "created_at", "started_at", "finished_at", "updated_at"),
    "ref":       ("ref", "branch", "commit", "sha"),
    "url":       ("url", "log_url", "link"),
}


def pick(row, field):
    for key in FIELDS.get(field, (field,)):
        val = row.get(key)
        if val not in (None, ""):
            return val
    return ""


def rows(data):
    """Yanıtın hangi biçimde geldiğinden bağımsız olarak kayıt listesi döndürür."""
    if isinstance(data, dict):
        for key in ("deployments", "data", "items", "results", "rows"):
            if isinstance(data.get(key), list):
                return rows(data[key])
        return [data] if data else []
    out = []
    for row in data if isinstance(data, list) else []:
        if isinstance(row, dict) and isinstance(row.get("json"), dict):
            row = row["json"]
        if isinstance(row, dict):
            out.append(row)
    return out


def load_stdin():
    raw = sys.stdin.read().strip()
    if not raw:
        return []
    try:
        return rows(json.loads(raw))
    except json.JSONDecodeError:
        print(f"! orchestrator JSON döndürmedi: {raw[:200]}", file=sys.stderr)
        sys.exit(1)


def parse_yaml(path):
    """deploy.yml'i okur. PyYAML varsa onu kullanır.

    Yoksa: 'anahtar: değer' ve girintiyle iç içe geçmiş eşlemeleri çözen küçük
    bir ayrıştırıcı devreye girer. Liste ve çok satırlı değer desteklemez —
    deploy.yml bu alt kümede tutulmalıdır (Pi/macOS'ta PyYAML olmayabilir).
    """
    try:
        import yaml  # noqa
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except ImportError:
        pass
    root = {}
    stack = [(-1, root)]  # (girinti, o seviyedeki sözlük)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].rstrip()
            if not line.strip() or ":" not in line:
                continue
            indent = len(line) - len(line.lstrip())
            key, _, val = line.strip().partition(":")
            key, val = key.strip(), val.strip().strip("'\"")
            while len(stack) > 1 and indent <= stack[-1][0]:
                stack.pop()
            parent = stack[-1][1]
            if val:
                parent[key] = val
            else:
                child = {}
                parent[key] = child
                stack.append((indent, child))
    return root


def cmd_body(argv):
    """deploy.yml → orchestrator'a gönderilecek JSON gövde.

    ref önceliği: komut satırı > ortamın branch'i > deploy.yml branch > main
    """
    spec = parse_yaml(argv[0])
    explicit_ref = argv[1] if len(argv) > 1 and argv[1] else ""
    env = argv[2] if len(argv) > 2 and argv[2] else ""

    env_branch = ""
    envs = spec.get("environments")
    if env and isinstance(envs, dict) and isinstance(envs.get(env), dict):
        env_branch = envs[env].get("branch") or ""

    body = {
        "project": spec.get("project", ""),
        "repo": spec.get("repo", ""),
        "type": spec.get("type", ""),
        "runner": spec.get("runner", ""),
        "ref": explicit_ref or env_branch or spec.get("branch") or "main",
        "trigger": "cli",
    }
    if env:
        body["environment"] = env
    print(json.dumps({k: v for k, v in body.items() if v != ""}))


def cmd_table(argv):
    data = load_stdin()
    limit = int(argv[0]) if argv and argv[0].isdigit() else 10
    data = data[:limit]
    if not data:
        print("  kayıt yok")
        return
    cols = ("project", "server", "status", "trigger", "timestamp")
    table = [[str(pick(r, c)) for c in cols] for r in data]
    widths = [max(len(c), *(len(r[i]) for r in table)) for i, c in enumerate(cols)]
    fmt = "  ".join("{:<%d}" % w for w in widths)
    print("  " + fmt.format(*(c.upper() for c in cols)))
    for row in table:
        print("  " + fmt.format(*row))


def cmd_field(argv):
    data = load_stdin()
    if data:
        print(pick(data[0], argv[0]))


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    mode, argv = sys.argv[1], sys.argv[2:]
    handlers = {"body": cmd_body, "table": cmd_table, "field": cmd_field}
    if mode not in handlers:
        print(f"bilinmeyen mod: {mode}", file=sys.stderr)
        sys.exit(2)
    handlers[mode](argv)


if __name__ == "__main__":
    main()
