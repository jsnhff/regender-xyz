// Terminal renderer: xterm.js wired to PTY via preload IPC.
/* global Terminal, FitAddon, WebLinksAddon */

const term = new Terminal({
  fontFamily: '"SF Mono", Menlo, Monaco, "Courier New", monospace',
  fontSize: 14,
  lineHeight: 1.15,
  cursorBlink: true,
  cursorStyle: "block",
  allowProposedApi: true,
  scrollback: 5000,
  macOptionIsMeta: true,
  theme: {
    background: "#000000",
    foreground: "#e6e6e6",
    cursor: "#e6e6e6",
    cursorAccent: "#000000",
    selectionBackground: "rgba(255,255,255,0.25)",
    black: "#000000",
    red: "#ff6b6b",
    green: "#7ee787",
    yellow: "#f2cc60",
    blue: "#79c0ff",
    magenta: "#d2a8ff",
    cyan: "#a5d6ff",
    white: "#e6e6e6",
    brightBlack: "#6e7681",
    brightRed: "#ffa198",
    brightGreen: "#56d364",
    brightYellow: "#e3b341",
    brightBlue: "#79c0ff",
    brightMagenta: "#d2a8ff",
    brightCyan: "#a5d6ff",
    brightWhite: "#ffffff",
  },
});

const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);
term.loadAddon(
  new WebLinksAddon.WebLinksAddon((event, uri) => {
    // Open links in default browser (handled by main process)
    window.open(uri, "_blank");
  })
);

term.open(document.getElementById("terminal"));

function applyFit() {
  try {
    fitAddon.fit();
    window.regender.resize(term.cols, term.rows);
  } catch (_e) {
    // ignore transient fit errors during resize
  }
}

// PTY -> xterm
window.regender.onOutput((data) => term.write(data));

// xterm -> PTY
term.onData((data) => window.regender.sendInput(data));

// Keep Cmd+C / Cmd+V working for copy-paste; let Ctrl+C pass through to PTY
term.attachCustomKeyEventHandler((e) => {
  if (e.type !== "keydown") return true;
  // Cmd+C: copy if there's a selection, otherwise let xterm handle (no-op)
  if (e.metaKey && e.key === "c") {
    const sel = term.getSelection();
    if (sel) {
      navigator.clipboard.writeText(sel).catch(() => {});
      return false;
    }
  }
  // Cmd+V: paste
  if (e.metaKey && e.key === "v") {
    navigator.clipboard.readText().then((txt) => {
      if (txt) window.regender.sendInput(txt);
    });
    return false;
  }
  // Cmd+K: clear screen
  if (e.metaKey && e.key === "k") {
    term.clear();
    return false;
  }
  return true;
});

// Initial fit must happen AFTER the #terminal element has been laid out,
// otherwise xterm.js measures a 0×0 container and fit() returns garbage.
// Main process holds the Python spawn until it receives this first resize.
function initialFit() {
  // Two RAFs: first lets the browser commit layout, second runs after paint.
  requestAnimationFrame(() => requestAnimationFrame(applyFit));
}
initialFit();

let resizeTimer = null;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(applyFit, 50);
});

term.focus();
