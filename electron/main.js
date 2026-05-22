const { app, BrowserWindow, ipcMain, shell, dialog } = require("electron");
const path = require("node:path");
const fs = require("node:fs");
const os = require("node:os");
const pty = require("node-pty");

const IS_DEV = !app.isPackaged;

// ---- Paths ----------------------------------------------------------------

function getUserDataDir() {
  // ~/Library/Application Support/Regender on macOS
  return path.join(os.homedir(), "Library", "Application Support", "Regender");
}

function getResourcePaths() {
  if (IS_DEV) {
    // Dev: assume repo layout, use parent dir for python + regender source
    const repoRoot = path.resolve(__dirname, "..");
    return {
      pythonBin: path.join(repoRoot, "python-arm64", "bin", "python3.11"),
      regenderRoot: repoRoot,
      cliEntry: path.join(repoRoot, "regender_cli.py"),
      seedTextsDir: path.join(repoRoot, "books", "texts"),
    };
  }
  const res = process.resourcesPath;
  return {
    pythonBin: path.join(res, "python", "bin", "python3.11"),
    regenderRoot: path.join(res, "regender"),
    cliEntry: path.join(res, "regender", "regender_cli.py"),
    seedTextsDir: path.join(res, "regender", "books", "texts"),
  };
}

// ---- First-run seeding ----------------------------------------------------

function ensureUserDataSeeded() {
  const userDir = getUserDataDir();
  const sentinel = path.join(userDir, ".regender-initialized");

  fs.mkdirSync(userDir, { recursive: true });
  fs.mkdirSync(path.join(userDir, "books", "texts"), { recursive: true });
  fs.mkdirSync(path.join(userDir, "books", "output"), { recursive: true });
  fs.mkdirSync(path.join(userDir, "logs"), { recursive: true });

  if (fs.existsSync(sentinel)) return userDir;

  const { seedTextsDir } = getResourcePaths();
  if (fs.existsSync(seedTextsDir)) {
    // In dev we share the repo's books/texts/ which has ~20 full Gutenberg files —
    // only seed Pride & Prejudice + the sample so the user's data dir stays clean.
    const seedFilter = IS_DEV
      ? (name) => name === "pride-prejudice-sample.txt" || name.startsWith("pg1342-")
      : () => true;
    for (const file of fs.readdirSync(seedTextsDir)) {
      if (!seedFilter(file)) continue;
      const src = path.join(seedTextsDir, file);
      const dst = path.join(userDir, "books", "texts", file);
      if (!fs.existsSync(dst) && fs.statSync(src).isFile()) {
        fs.copyFileSync(src, dst);
      }
    }
  }
  fs.writeFileSync(sentinel, new Date().toISOString());
  return userDir;
}

// ---- PTY lifecycle --------------------------------------------------------

let ptyProcess = null;

function spawnPython(window, userDir, cols, rows) {
  const { pythonBin, regenderRoot, cliEntry } = getResourcePaths();

  if (!fs.existsSync(pythonBin)) {
    dialog.showErrorBox(
      "Bundled Python missing",
      `Could not find ${pythonBin}. Run electron/build.sh before launching.`
    );
    app.quit();
    return null;
  }

  ptyProcess = pty.spawn(pythonBin, [cliEntry], {
    name: "xterm-256color",
    cols,
    rows,
    cwd: userDir,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      PYTHONPATH: regenderRoot,
      REGENDER_DATA_DIR: userDir,
      TERM: "xterm-256color",
      COLORTERM: "truecolor",
      LANG: process.env.LANG || "en_US.UTF-8",
      LC_ALL: process.env.LC_ALL || "en_US.UTF-8",
    },
  });

  ptyProcess.onData((data) => {
    if (!window.isDestroyed()) window.webContents.send("pty-output", data);
  });

  ptyProcess.onExit(({ exitCode }) => {
    if (!window.isDestroyed()) {
      window.webContents.send(
        "pty-output",
        `\r\n\x1b[2m[regender exited with code ${exitCode}]\x1b[0m\r\n`
      );
    }
    ptyProcess = null;
  });

  return ptyProcess;
}

// ---- Window ---------------------------------------------------------------

function createWindow() {
  const win = new BrowserWindow({
    width: 960,
    height: 640,
    minWidth: 640,
    minHeight: 400,
    backgroundColor: "#000000",
    titleBarStyle: "hiddenInset",
    title: "Regender",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  win.loadFile(path.join(__dirname, "renderer", "index.html"));
  win.once("ready-to-show", () => win.show());

  // Open external links in the user's browser, not inside the Electron window
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  const userDir = ensureUserDataSeeded();

  // ---- IPC ----
  ipcMain.on("pty-input", (_evt, data) => {
    if (ptyProcess) ptyProcess.write(data);
  });

  // First resize message bootstraps the spawn so Python's initial frame
  // is drawn at the renderer's real cols/rows (not a guessed default).
  ipcMain.on("pty-resize", (_evt, { cols, rows }) => {
    if (!cols || !rows || cols < 4 || rows < 4) return;
    if (!ptyProcess) {
      spawnPython(win, userDir, cols, rows);
      return;
    }
    try {
      ptyProcess.resize(cols, rows);
    } catch (_e) {
      // pty already exited
    }
  });

  win.on("closed", () => {
    if (ptyProcess) {
      try {
        ptyProcess.kill();
      } catch (_e) {
        // already dead
      }
      ptyProcess = null;
    }
  });

  return win;
}

// ---- App lifecycle --------------------------------------------------------

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (ptyProcess) {
    try {
      ptyProcess.kill();
    } catch (_e) {
      // ignore
    }
  }
});
