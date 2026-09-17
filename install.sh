#!/usr/bin/env bash
# Tek satırlık kurulum:
#   curl -fsSL https://raw.githubusercontent.com/omerfkara/omerkara-bootstrap/main/install.sh | bash
#   curl -fsSL .../install.sh | bash -s -- init proje-adi --type web
set -euo pipefail
OMK_HOME="${OMK_HOME:-$HOME/.omerkara}"
REPO="${OMK_BOOTSTRAP_REPO:-https://github.com/omerfkara/omerkara-bootstrap.git}"
DEST="$OMK_HOME/bootstrap"

command -v git >/dev/null || { echo "git gerekli" >&2; exit 1; }
mkdir -p "$OMK_HOME"
if [ -d "$DEST/.git" ]; then git -C "$DEST" pull -q --ff-only
else git clone -q "$REPO" "$DEST"; fi

"$DEST/bin/omk" setup < /dev/tty
if [ $# -gt 0 ]; then "$DEST/bin/omk" "$@" < /dev/tty; fi
