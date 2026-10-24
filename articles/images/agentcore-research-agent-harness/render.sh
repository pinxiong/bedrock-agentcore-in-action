#!/bin/sh
# Render every SVG in this folder to PNG: body figures at 2880 (2x),
# covers at their shipped sizes (2400x1350, 1400x788, 2000x840).
set -e
cd "$(dirname "$0")"
PY=/Users/pinxiong/.workbuddy/binaries/python/envs/default/bin/python
export PYTHONHOME=/Users/pinxiong/.workbuddy/binaries/python/versions/3.11.9
unset PYTHONPATH
for f in *.svg; do
  name="${f%.svg}"
  case "$name" in
    cover)        width=2400 ;;
    cover-medium) width=1400 ;;
    cover-devto)  width=2000 ;;
    *)            width=2880 ;;
  esac
  "$PY" -c "
import re, resvg_py, pathlib
src = pathlib.Path('$name.svg').read_text()
b = resvg_py.svg_to_bytes(svg_path='$name.svg', background='#0a1024', width=$width)
b = b.get('data') if isinstance(b, dict) else b
pathlib.Path('$name.png').write_bytes(b)
"
  echo "rendered $name.png at $width"
done
