#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
test -x .venv/bin/python || python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
exec .venv/bin/python app.py
