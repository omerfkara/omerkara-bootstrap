#!/usr/bin/env python3
"""Task API /documents yanıtını işler. Yanıt biçimine toleranslıdır:
[...], {"documents": [...]}, {"data": [...]} veya n8n'in [{"json": {...}}] biçimi."""
import json, os, re, sys


def items(data):
    if isinstance(data, dict):
        for k in ("documents", "data", "items", "results"):
            if isinstance(data.get(k), list):
                return items(data[k])
        return [data] if "name" in data else []
    out = []
    for d in data if isinstance(data, list) else []:
        if isinstance(d, dict) and isinstance(d.get("json"), dict):
            d = d["json"]
        if isinstance(d, dict) and d.get("name"):
            out.append(d)
    return out


def main():
    mode = sys.argv[1]
    raw = sys.stdin.read().strip()
    docs = items(json.loads(raw)) if raw else []
    if mode == "names":
        for d in docs:
            print(d["name"])
    elif mode == "write":
        target = sys.argv[2]
        for d in docs:
            name = re.sub(r"[^A-Za-z0-9_.-]", "_", d["name"])
            content = d.get("content")
            if content is None:
                continue
            path = os.path.join(target, name if name.endswith(".md") else name + ".md")
            if os.path.exists(path):
                print(f"  mevcut, atlandı: {path}")
                continue
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ indirildi: {path}")


if __name__ == "__main__":
    main()
