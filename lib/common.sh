#!/usr/bin/env bash
# Ortak yardımcılar — bash 3.2 (macOS) uyumlu tutulmalı.

OMK_HOME="${OMK_HOME:-$HOME/.omerkara}"
OMK_CONFIG_DIR="${OMK_CONFIG_DIR:-$HOME/.config/omerkara}"
OMK_CRED_FILE="$OMK_CONFIG_DIR/credentials"
OMK_CONF_FILE="$OMK_CONFIG_DIR/config"
OMK_GITHUB_USER="${OMK_GITHUB_USER:-omerfkara}"

if [ -t 1 ]; then
  C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YLW=$'\033[33m'; C_BLU=$'\033[34m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YLW=""; C_BLU=""; C_DIM=""; C_RST=""
fi

info() { printf '%s›%s %s\n' "$C_BLU" "$C_RST" "$*"; }
ok()   { printf '%s✓%s %s\n' "$C_GRN" "$C_RST" "$*"; }
warn() { printf '%s!%s %s\n' "$C_YLW" "$C_RST" "$*" >&2; }
die()  { printf '%s✗%s %s\n' "$C_RED" "$C_RST" "$*" >&2; exit 1; }
dim()  { printf '%s  %s%s\n' "$C_DIM" "$*" "$C_RST"; }

has() { command -v "$1" >/dev/null 2>&1; }

# DRY_RUN=1 ise komutu sadece yazdırır
run() {
  if [ "${DRY_RUN:-0}" = "1" ]; then dim "[dry-run] $*"; return 0; fi
  "$@"
}

os_name() {
  case "$(uname -s)" in
    Darwin) echo macos ;;
    Linux)  if grep -qi raspberry /proc/device-tree/model 2>/dev/null; then echo pi; else echo linux; fi ;;
    *)      echo other ;;
  esac
}

install_hint() {
  case "$(os_name)" in
    macos) echo "brew install $1" ;;
    *)     echo "sudo apt-get install -y $1" ;;
  esac
}

require_cmds() {
  missing=""
  for c in "$@"; do has "$c" || missing="$missing $c"; done
  if [ -n "$missing" ]; then
    for c in $missing; do warn "Eksik komut: $c  →  $(install_hint "$c")"; done
    die "Önce eksik bağımlılıkları kurun."
  fi
}

# Ortamdan gelen değerlerin dosyadakini ezmesi gereken anahtarlar
OMK_OVERRIDABLE="TASK_TOKEN ORCH_TOKEN TASK_API TASK_MCP_URL ORCH_API ORCH_REGISTER_PATH ORCH_DEPLOY_PATH ORCH_HEALTH_PATH TASK_PROJECT"

# Makine seviyesi credential ve config dosyalarını yükler.
# Öncelik: ortam değişkeni > credentials > config > varsayılan.
# (Dosyalar 'set -a' ile source edildiği için ortamdaki değer önce saklanır,
#  sonra geri yazılır; aksi halde tek seferlik ORCH_API=... gibi override'lar
#  sessizce yok sayılır.)
load_credentials() {
  for _v in $OMK_OVERRIDABLE; do
    # Boş ama tanımlı bir değer de kasıtlıdır (ör. ORCH_API= ile devre dışı bırakma).
    # Koşul eval'in DIŞINDA: eval 1 dönerse set -e script'i sonlandırır.
    if eval "[ -n \"\${$_v+x}\" ]"; then eval "OMK_ENV_$_v=\"\$$_v\""; fi
  done
  # shellcheck disable=SC1090
  [ -f "$OMK_CONF_FILE" ] && { set -a; . "$OMK_CONF_FILE"; set +a; }
  # shellcheck disable=SC1090
  [ -f "$OMK_CRED_FILE" ] && { set -a; . "$OMK_CRED_FILE"; set +a; }
  for _v in $OMK_OVERRIDABLE; do
    if eval "[ -n \"\${OMK_ENV_$_v+x}\" ]"; then
      eval "$_v=\"\$OMK_ENV_$_v\""
      # shellcheck disable=SC2163  # değişken ADI $_v içinde; kasıtlı
      export "$_v"
    fi
  done
  unset _v
  export TASK_API="${TASK_API:-https://n8n.omerkara.com/webhook}"
  export TASK_SPEC_URL="${TASK_SPEC_URL:-https://tasks.omerkara.com/task-management.md}"
  # Task MCP uzak sunucu, OAuth ile kimlik doğrular — .mcp.json'a token yazılmaz
  export TASK_MCP_URL="${TASK_MCP_URL:-https://tasks.omerkara.com/api/mcp}"
  export ORCH_API="${ORCH_API:-}"
  export ORCH_REGISTER_PATH="${ORCH_REGISTER_PATH:-/projects}"
  export ORCH_DEPLOY_PATH="${ORCH_DEPLOY_PATH:-/deployments}"
  export ORCH_HEALTH_PATH="${ORCH_HEALTH_PATH:-/health}"
}

# Değeri güvenli şekilde KEY=VALUE dosyasına yazar/günceller
set_kv() { # file key value
  f="$1"; k="$2"; v="$3"
  umask 077; touch "$f"
  tmp="$f.tmp.$$"
  grep -v "^$k=" "$f" > "$tmp" 2>/dev/null || true
  printf "%s='%s'\n" "$k" "$(printf '%s' "$v" | sed "s/'/'\\\\''/g")" >> "$tmp"
  mv "$tmp" "$f"; chmod 600 "$f"
}

# Secret okuma: önce ortam, sonra 1Password referansı, sonra kullanıcıya sor
read_secret() { # var_name prompt op_ref_var
  name="$1"; prompt="$2"; ref_var="$3"
  eval "cur=\${$name:-}"
  [ -n "$cur" ] && { printf '%s' "$cur"; return 0; }
  eval "ref=\${$ref_var:-}"
  if [ -n "$ref" ] && has op; then
    op read "$ref" 2>/dev/null && return 0
    warn "1Password'den okunamadı: $ref"
  fi
  val=""
  if ( : < /dev/tty ) 2>/dev/null; then
    printf '%s: ' "$prompt" > /dev/tty
    # Ctrl-C ya da hata halinde terminali echo kapalı bırakma
    trap 'stty echo < /dev/tty 2>/dev/null || true' INT TERM EXIT
    stty -echo < /dev/tty 2>/dev/null || true
    IFS= read -r val < /dev/tty || true
    stty echo < /dev/tty 2>/dev/null || true
    trap - INT TERM EXIT
    printf '\n' > /dev/tty
  fi
  printf '%s' "$val"
}

# Anahtar dosyada kayıtlı mı?
has_kv() { [ -f "$1" ] && grep -q "^$2=" "$1"; }

# {{VAR}} yer tutucularını ortam değişkenleriyle doldurur.
# ${VAR} ifadelerine dokunmaz (ör. .mcp.json içindeki ${TASK_TOKEN}).
render_template() { # src dst [force]
  src="$1"; dst="$2"; force="${3:-0}"
  if [ -e "$dst" ] && [ "$force" != "1" ]; then dim "mevcut, atlandı: $dst"; return 0; fi
  [ "${DRY_RUN:-0}" = "1" ] && { dim "[dry-run] yaz: $dst"; return 0; }
  mkdir -p "$(dirname "$dst")"
  perl -pe 's/\{\{([A-Z0-9_]+)\}\}/exists $ENV{$1} ? $ENV{$1} : "{{$1}}"/ge' "$src" > "$dst"
  ok "yazıldı: $dst"
}

# Satır dosyada yoksa ekler
ensure_line() { # file line
  touch "$1"
  grep -qxF "$2" "$1" || printf '%s\n' "$2" >> "$1"
}

# Task API çağrısı: method path [json_body]
task_api() {
  m="$1"; p="$2"; body="${3:-}"
  if [ -n "$body" ]; then
    curl -fsS -X "$m" "$TASK_API$p" -H "X-Task-Token: $TASK_TOKEN" \
      -H "Content-Type: application/json" --data-binary "$body" --max-time 20
  else
    curl -fsS -X "$m" "$TASK_API$p" -H "X-Task-Token: $TASK_TOKEN" --max-time 20
  fi
}

# Doküman adını normalize eder: "PROMPT.md" -> "PROMPT"
doc_key() { printf '%s' "${1%.md}"; }

urlencode() { python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$1"; }

# Bir uç noktayı yoklar ve HTTP kodunu yazar; ulaşılamazsa 000.
# (curl zaten 000 yazdığı için '|| echo 000' kalıbı "000000" üretiyordu.)
http_ping() { # url [timeout]
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time "${2:-10}" "$1" 2>/dev/null || true)"
  case "$code" in ''|*[!0-9]*) code=000 ;; esac
  printf '%s' "$code"
}

# Orchestrator API çağrısı: method path [json_body]
# Gövdeyi stdout'a, HTTP kodunu son satıra yazar.
orch_api() {
  m="$1"; p="$2"; body="${3:-}"
  [ -n "${ORCH_API:-}" ]   || { warn "ORCH_API tanımlı değil"; return 2; }
  [ -n "${ORCH_TOKEN:-}" ] || { warn "ORCH_TOKEN tanımlı değil"; return 2; }
  if [ -n "$body" ]; then
    curl -sS -X "$m" "$ORCH_API$p" -H "Authorization: Bearer $ORCH_TOKEN" \
      -H "Content-Type: application/json" --data-binary "$body" \
      -w '\n%{http_code}' --max-time "${ORCH_TIMEOUT:-30}"
  else
    curl -sS -X "$m" "$ORCH_API$p" -H "Authorization: Bearer $ORCH_TOKEN" \
      -w '\n%{http_code}' --max-time "${ORCH_TIMEOUT:-30}"
  fi
}

# orch_api çıktısından HTTP kodunu / gövdeyi ayırır
http_code_of() { printf '%s' "$1" | tail -n1; }
http_body_of() { printf '%s' "$1" | sed '$d'; }

# Git repo'yu klonla ya da güncelle
sync_repo() { # url dest
  url="$1"; dest="$2"
  if [ -d "$dest/.git" ]; then
    if run git -C "$dest" pull -q --ff-only; then ok "güncel: $dest"; else warn "güncellenemedi (yerel değişiklik?): $dest"; fi
  elif [ -e "$dest" ]; then
    warn "git reposu değil, atlandı: $dest"
  else
    mkdir -p "$(dirname "$dest")"
    if GIT_TERMINAL_PROMPT=0 run git clone -q "$url" "$dest"; then ok "klonlandı: $dest"
    else warn "klonlanamadı: $url (private repo ise 'gh auth login' veya SSH anahtarı gerekir)"; return 1; fi
  fi
}
