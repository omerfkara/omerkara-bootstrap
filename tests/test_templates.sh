#!/usr/bin/env bash
# Şablonlardaki omk komutları CLI ile tutarlı mı (#681). Çalıştır: bash tests/test_templates.sh
set -u
cd "$(dirname "$0")/.."
fails=0
check() { # açıklama beklenen gerçek
  if [ "$2" = "$3" ]; then printf '  ✓ %s\n' "$1"; else printf '  ✗ %s: beklenen [%s], gelen [%s]\n' "$1" "$2" "$3"; fails=$((fails + 1)); fi
}
tmpl=templates/CLAUDE.md.tmpl
help="$(bin/omk help 2>&1)"

# Şablondaki her 'omk deploy ... --bayrak' omk help'te geçmeli
for flag in $(grep -o 'omk deploy[^`]*' "$tmpl" | grep -oE -- '--[a-z-]+' | sort -u); do
  printf '%s\n' "$help" | grep -qE -- "^  $flag( |$)" && r=var || r=yok
  check "şablondaki $flag omk help'te tanımlı" var "$r"
done

# --env bir ortam adıyla gösterilmemeli
grep -qE -- '--env (staging|production|prod|dev)' "$tmpl" && r=var || r=yok
check "şablon --env'i ortam adıyla göstermiyor" yok "$r"

# --env'e ortam adı verilince CLI, credential'a dokunmadan açıklayıcı hata verir
out="$(HOME="$(mktemp -d)" bin/omk deploy demo --env production --dry-run 2>&1)"; code=$?
check "--env production hata koduyla çıkar" 1 "$code"
printf '%s' "$out" | grep -q "ortam seçmez" && r=var || r=yok
check "--env production hatası nedenini söyler" var "$r"

[ "$fails" = 0 ] && echo "tamam" || { echo "$fails test başarısız"; exit 1; }
