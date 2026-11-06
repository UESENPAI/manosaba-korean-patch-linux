#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -x "$SCRIPT_DIR/manosaba-patcher" ]; then
    exec "$SCRIPT_DIR/manosaba-patcher" "$@"
fi
if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Python 3.8 이상이 필요합니다. 배포판의 패키지 관리자로 python3를 설치하세요.' >&2
    exit 1
fi
exec python3 "$SCRIPT_DIR/manosaba_linux_patch.py" "$@"
