#!/bin/sh
# Render every SVG in this folder to PNG with resvg.
# The workbuddy python needs PYTHONHOME set or it cannot find its stdlib.
set -e
cd "$(dirname "$0")"
PY=/Users/pinxiong/.workbuddy/binaries/python/envs/default/bin/python
export PYTHONHOME=/Users/pinxiong/.workbuddy/binaries/python/versions/3.11.9
unset PYTHONPATH
for f in *.svg; do
  name="${f%.svg}"
  env PYTHONHOME="$PYTHONHOME" "$PY" -c "
import re, resvg_py, pathlib
src = pathlib.Path('$name.svg').read_text()
w = int(re.search(r'viewBox=\"\S+ \S+ (\d+)', src).group(1))
b = resvg_py.svg_to_bytes(svg_path='$name.svg', background='#0a1024', width=w)
b = b.get('data') if isinstance(b, dict) else b
pathlib.Path('$name.png').write_bytes(b)
"
  echo "rendered $name.png"
done
