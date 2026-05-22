const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("regender", {
  onOutput: (callback) => {
    const listener = (_evt, data) => callback(data);
    ipcRenderer.on("pty-output", listener);
    return () => ipcRenderer.removeListener("pty-output", listener);
  },
  sendInput: (data) => ipcRenderer.send("pty-input", data),
  resize: (cols, rows) => ipcRenderer.send("pty-resize", { cols, rows }),
});
