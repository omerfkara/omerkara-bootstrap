#!/usr/bin/env bash
# lib/common.sh yardımcılarının testleri (#372). Çalıştır: bash tests/test_common.sh
set -u
cd "$(dirname "$0")/.."
# shellcheck source=../lib/common.sh
. lib/common.sh >/dev/null 2>&1
fails=0
check() { # açıklama beklenen gerçek
  if [ "$2" = "$3" ]; then printf '  ✓ %s\n' "$1"; else printf '  ✗ %s: beklenen [%s], gelen [%s]\n' "$1" "$2" "$3"; fails=$((fails + 1)); fi
}
ID=0123456789abcdef0123456789abcdef.access
check "cf_normalize başlık önekini atar" "$ID" "$(cf_normalize "CF-Access-Client-Id: $ID")"
check "cf_normalize çift yapıştırmayı teke indirir" "$ID" "$(cf_normalize "$ID$ID")"
check "cf_normalize boşlukları kırpar" "abc" "$(cf_normalize "  abc  ")"
check "cf_normalize secret önekini de atar" "s3cr3t" "$(cf_normalize "cf-access-client-secret:s3cr3t")"
cf_id_valid "$ID" && r=ok || r=bad; check "cf_id_valid geçerli ID" ok "$r"
cf_id_valid "abc" && r=ok || r=bad; check "cf_id_valid kısa değer" bad "$r"
cf_id_valid "$ID$ID" && r=ok || r=bad; check "cf_id_valid çift değer" bad "$r"
resp="$(printf '{"a":1}\n302')"
check "http_code_of son satır" 302 "$(http_code_of "$resp")"
check "http_body_of gövde" '{"a":1}' "$(http_body_of "$resp")"
check "urlencode boşluk ve Türkçe" "a%20%C3%A7" "$(urlencode "a ç")"
[ "$fails" = 0 ] && echo "tamam" || { echo "$fails test başarısız"; exit 1; }
