#!/usr/bin/env bash
set -e

echo ""
echo "  ◆ regender.xyz"
echo ""

# ── Check Python ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "  Python 3 is required but wasn't found on your computer."
  echo "  Download it free at → https://python.org/downloads"
  echo ""
  exit 1
fi

PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
if [ "$PY_MAJOR" -lt 3 ] || [ "$PY_MINOR" -lt 9 ]; then
  echo "  Python 3.9 or later is required (you have Python $PY_MAJOR.$PY_MINOR)."
  echo "  Download the latest version at → https://python.org/downloads"
  echo ""
  exit 1
fi

# ── Clone or update ───────────────────────────────────────────────────────────
DEST="$HOME/regender-xyz"

if [ -d "$DEST/.git" ]; then
  echo "  → Found existing install at $DEST"
  echo "  → Checking for updates..."
  git -C "$DEST" pull --quiet
else
  echo "  → Downloading regender.xyz to $DEST ..."
  git clone --quiet --depth 1 https://github.com/jsnhff/regender-xyz.git "$DEST"
fi

# ── Install dependencies ──────────────────────────────────────────────────────
# A virtual environment of its own, so the install works on Pythons that
# refuse system-wide pip installs (Homebrew's, for one) and touches nothing else.
if [ ! -x "$DEST/.venv/bin/python" ]; then
  echo "  → Setting up a private Python environment..."
  python3 -m venv "$DEST/.venv"
fi
PY="$DEST/.venv/bin/python"

echo "  → Installing dependencies (this may take a minute)..."
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r "$DEST/requirements.txt"

# ── Launch ────────────────────────────────────────────────────────────────────
echo "  → Done! Starting regender.xyz..."
echo ""
cd "$DEST"
"$PY" regender_cli.py
