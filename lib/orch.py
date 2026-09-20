#!/usr/bin/env python3
"""Orchestrator yardımcıları — harici bağımlılık yok (PyYAML varsa kullanılır).

Kullanım:
  orch.py register deploy.yml           → POST /api/projects gövdesi (JSON)
  orch.py project  deploy.yml           → proje adı
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


def cmd_register(argv):
    """deploy.yml → POST /api/projects gövdesi.

    Zorunlu: name, git_url (HTTPS), target_runner, build_command, deploy_command.
    Opsiyonel: watch_paths, ios_secrets_dir, env_file, notifications.
    Göndermediğimiz alanlar orchestrator tarafında korunuyor, bu yüzden boş
    değerler gövdeye hiç konmaz.
    """
    spec = parse_yaml(argv[0])
    body = {}
    for key in ("name", "git_url", "target_runner", "build_command",
                "deploy_command", "ios_secrets_dir", "env_file", "notifications"):
        val = spec.get(key)
        if isinstance(val, str) and val.strip():
            body[key] = val.strip()
        elif val not in (None, "", {}, []):
            body[key] = val

    # watch_paths: mini ayrıştırıcı liste bilmediği için virgülle ayrılmış yazılır
    wp = spec.get("watch_paths")
    if isinstance(wp, str) and wp.strip():
        body["watch_paths"] = [p.strip() for p in wp.split(",") if p.strip()]
    elif isinstance(wp, list) and wp:
        body["watch_paths"] = wp

    # Yeni kayıtta orchestrator bunların hepsini zorunlu tutuyor; güncellemede
    # göndermediğin alan korunuyor ama boş göndermek üzerine yazar. Bu yüzden
    # boş bırakmak yerine kullanıcıdan doldurmasını istiyoruz.
    required = ("name", "git_url", "target_runner", "build_command", "deploy_command")
    missing = [k for k in required if not body.get(k)]
    if missing:
        print("! deploy.yml içinde doldurulmamış alan: " + ", ".join(missing),
              file=sys.stderr)
        sys.exit(1)

    # Orchestrator git_url'i HTTPS bekliyor; SSH biçimi sessizce başarısız olur
    if not body["git_url"].startswith("https://"):
        print("! git_url HTTPS olmalı (https://github.com/<kullanıcı>/<repo>.git): "
              + body["git_url"], file=sys.stderr)
        sys.exit(1)

    runners = ("pi", "ubuntu", "macos")
    if body["target_runner"] not in runners:
        print("! target_runner şunlardan biri olmalı: " + ", ".join(runners),
              file=sys.stderr)
        sys.exit(1)
    print(json.dumps(body))


def cmd_project(argv):
    """deploy.yml'deki proje adını yazar (URL'de kullanılır)."""
    spec = parse_yaml(argv[0])
    name = spec.get("name") or ""
    if not name:
        print("! deploy.yml içinde 'name' yok", file=sys.stderr)
        sys.exit(1)
    print(name)


def cmd_get(argv):
    """deploy.yml'den tek bir alanı yazar: orch.py get <anahtar> <dosya>"""
    spec = parse_yaml(argv[1])
    val = spec.get(argv[0])
    if isinstance(val, str) and val.strip():
        print(val.strip())


def cmd_errors(argv):
    """FastAPI 422 gövdesini okunur satırlara çevirir."""
    raw = sys.stdin.read().strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("  " + raw[:300])
        return
    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, str):
        print("  " + detail)
        return
    if not isinstance(detail, list):
        print("  " + json.dumps(data)[:300])
        return
    for item in detail:
        if not isinstance(item, dict):
            continue
        loc = [str(x) for x in item.get("loc", []) if x != "body"]
        print(f"  {'.'.join(loc) or '?'}: {item.get('msg', '')}")


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
    handlers = {"register": cmd_register, "project": cmd_project,
                "errors": cmd_errors, "get": cmd_get,
                "table": cmd_table, "field": cmd_field}
    if mode not in handlers:
        print(f"bilinmeyen mod: {mode}", file=sys.stderr)
        sys.exit(2)
    handlers[mode](argv)


if __name__ == "__main__":
    main()
