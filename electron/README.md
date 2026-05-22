# Regender Mac App (Electron wrapper)

Wraps the Textual TUI inside an Electron-hosted terminal so non-technical users can run Regender by double-clicking a `.dmg`. No Python install, no `pip`, no terminal.

Target: macOS Apple Silicon (arm64) only.

## Develop locally

```bash
# From repo root, build the bundled Python once (downloads ~30 MB):
./electron/build.sh --dev   # full pipeline, unsigned

# Or step-by-step from electron/:
cd electron
npm install
npx electron-rebuild -f -w node-pty
npm start                   # launches Electron pointing at ../python-arm64 + ../regender_cli.py
```

In dev mode `main.js` resolves Python and the regender source from the parent repo, so live edits to `src/cli/tui.py` show up on next launch.

## Ship a .dmg

```bash
# One-time: enroll in Apple Developer, install your "Developer ID Application" cert
# Export it as .p12 and set these env vars (or put them in a .env you source):
export CSC_LINK="/path/to/developer-id.p12"
export CSC_KEY_PASSWORD="..."
export APPLE_ID="you@example.com"
export APPLE_APP_SPECIFIC_PASSWORD="abcd-efgh-ijkl-mnop"   # appleid.apple.com
export APPLE_TEAM_ID="ABCDE12345"

./electron/build.sh         # signed + notarized .dmg in electron/dist/
```

The script:
1. Downloads `python-build-standalone` arm64 → `python-arm64/`
2. `pip install --target` of `requirements.txt` into the bundled site-packages
3. `electron-rebuild` for `node-pty`
4. `electron-builder` → `dist/Regender-<version>-arm64.dmg`

## Architecture

```
Electron renderer (xterm.js)  <─IPC─>  main process  <─node-pty─>  bundled python3.11
                                                                     └─ regender_cli.py
                                                                        CWD = ~/Library/Application Support/Regender/
```

On first launch the app seeds `~/Library/Application Support/Regender/` with starter books and creates `books/output/` + `logs/`. The friendly-mode wizard (`src/cli/tui.py:923-1070`) handles API-key onboarding inside the embedded terminal — no Electron-side modal.

## TODO before first real release

- Replace placeholder app icon: drop a real `build/icon.icns` (1024×1024 source) into `electron/build/`. Without it, electron-builder uses the default Electron icon on the .dmg and the dock.
- Run `./build.sh --dev` end-to-end at least once and verify the Textual TUI renders correctly inside xterm.js (gradient text, spinners, file browser screen, Ctrl+C cancel). This is the highest-risk unknown — Textual's alt-screen + mouse handling needs to play nicely with xterm.js.
- Bump `version` in `package.json` per release.
