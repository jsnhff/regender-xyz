#!/usr/bin/env bash
# Build Regender.app + .dmg for macOS arm64.
#
# Prereqs (one-time on the build machine):
#   - macOS arm64 host
#   - Node 18+ and npm
#   - Xcode command-line tools (for codesign / node-pty native build)
#   - Apple Developer ID Application cert installed in the login keychain
#   - Signing/notarization env vars (see "Signing & notarization" below)
#
# Usage:
#   ./build.sh             # full pipeline: deps -> bundle python -> dmg
#   ./build.sh --dev       # skip notarization (faster, ad-hoc signed only)

set -euo pipefail

cd "$(dirname "$0")"
ELECTRON_DIR="$(pwd)"
REPO_ROOT="$(cd .. && pwd)"

DEV_MODE=0
if [[ "${1:-}" == "--dev" ]]; then
  DEV_MODE=1
fi

PYTHON_VERSION="3.11.9"
# Pin the python-build-standalone release tag. Update both PBS_TAG and PBS_FILENAME
# together when bumping. Check https://github.com/astral-sh/python-build-standalone/releases
# for the latest matching cpython-${PYTHON_VERSION}+<date>-aarch64-apple-darwin-install_only.tar.gz
PBS_TAG="20240814"
PBS_FILENAME="cpython-${PYTHON_VERSION}+${PBS_TAG}-aarch64-apple-darwin-install_only.tar.gz"
PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${PBS_FILENAME}"

PYTHON_DIR="${REPO_ROOT}/python-arm64"

# ---------------------------------------------------------------------------
echo "==> [1/5] Bundle Python (python-build-standalone, arm64)"
# ---------------------------------------------------------------------------
if [[ ! -x "${PYTHON_DIR}/bin/python3.11" ]]; then
  TMP="$(mktemp -d)"
  echo "    downloading ${PBS_FILENAME}"
  curl -fL -o "${TMP}/python.tar.gz" "${PBS_URL}"
  echo "    extracting -> ${PYTHON_DIR}"
  rm -rf "${PYTHON_DIR}"
  mkdir -p "${PYTHON_DIR}"
  tar -xzf "${TMP}/python.tar.gz" -C "${PYTHON_DIR}" --strip-components=1
  rm -rf "${TMP}"
else
  echo "    ${PYTHON_DIR} already exists, skipping download"
fi

PY="${PYTHON_DIR}/bin/python3.11"
echo "    using: $("${PY}" --version)"

# ---------------------------------------------------------------------------
echo "==> [2/5] Install Python deps into bundled site-packages"
# ---------------------------------------------------------------------------
SITE_PKGS="${PYTHON_DIR}/lib/python3.11/site-packages"
"${PY}" -m pip install --upgrade pip --target "${SITE_PKGS}" >/dev/null
"${PY}" -m pip install --no-warn-script-location \
  --target "${SITE_PKGS}" \
  -r "${REPO_ROOT}/requirements.txt"

# Strip caches to shrink bundle
find "${PYTHON_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} + || true
find "${PYTHON_DIR}" -type d -name "tests" -prune -exec rm -rf {} + || true
find "${PYTHON_DIR}" -name "*.pyc" -delete || true

echo "    bundled python size: $(du -sh "${PYTHON_DIR}" | cut -f1)"

# ---------------------------------------------------------------------------
echo "==> [3/5] Install Node deps & rebuild node-pty for Electron"
# ---------------------------------------------------------------------------
cd "${ELECTRON_DIR}"
if [[ ! -d "node_modules" ]]; then
  npm install
fi
npx electron-rebuild -f -w node-pty

# ---------------------------------------------------------------------------
echo "==> [4/5] Smoke test (dev launch)"
# ---------------------------------------------------------------------------
# Verify the bundled python can at least import the regender entry point.
"${PY}" -c "import sys; sys.path.insert(0, '${REPO_ROOT}'); import regender_cli" \
  && echo "    regender_cli imports OK"

# ---------------------------------------------------------------------------
echo "==> [5/5] Package & notarize"
# ---------------------------------------------------------------------------
if [[ "${DEV_MODE}" -eq 1 ]]; then
  echo "    --dev: building unsigned .dmg (no notarization)"
  CSC_IDENTITY_AUTO_DISCOVERY=false npx electron-builder --mac --arm64 \
    -c.mac.identity=null \
    -c.mac.notarize=false
else
  # Required env vars for signed + notarized build:
  : "${CSC_LINK:?set CSC_LINK to your .p12 path or base64 (Developer ID Application)}"
  : "${CSC_KEY_PASSWORD:?set CSC_KEY_PASSWORD}"
  : "${APPLE_ID:?set APPLE_ID}"
  : "${APPLE_APP_SPECIFIC_PASSWORD:?set APPLE_APP_SPECIFIC_PASSWORD (app-specific password from appleid.apple.com)}"
  : "${APPLE_TEAM_ID:?set APPLE_TEAM_ID}"
  npx electron-builder --mac --arm64 \
    -c.mac.notarize.teamId="${APPLE_TEAM_ID}"
fi

echo ""
echo "==> Done. Output:"
ls -lh dist/*.dmg 2>/dev/null || echo "    (no .dmg produced — check logs above)"
