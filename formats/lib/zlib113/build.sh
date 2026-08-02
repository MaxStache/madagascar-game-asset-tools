#!/usr/bin/env bash
# Builds the vendored zlib 1.1.3 encoder into a shared library that
# formats/lib/zlib113/__init__.py loads via ctypes.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

case "$(uname -s)" in
    Darwin) OUT=libzlib113.dylib; SHARED_FLAG=-dynamiclib ;;
    Linux)  OUT=libzlib113.so; SHARED_FLAG=-shared ;;
    *) echo "Unsupported platform: $(uname -s)" >&2; exit 1 ;;
esac

cc -O2 -fPIC "$SHARED_FLAG" -o "$OUT" \
    wrapper.c \
    vendor/deflate.c vendor/trees.c vendor/adler32.c vendor/zutil.c

echo "Built $OUT"
