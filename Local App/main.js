const { app, BrowserWindow } = require("electron");
const { PythonShell } = require("python-shell");
require("electron-reload");
const path = require("path");
let pyshell;

function createWindow() {
  pyshell = new PythonShell(path.join(__dirname, "/../Interface.py"), {
    pythonPath: "python",
    stderr: function (err) {
      console.log(err);
    },
  });
  window = new BrowserWindow({ width: 1040, height: 900, minWidth: 500 });
  window.loadFile("index.html");
}

app.on("ready", createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    pyshell.end(function (err, code, signal) {
      if (err) throw err;
      console.log("The exit code was: " + code);
      console.log("The exit signal was: " + signal);
      console.log("finished");
    });
    app.quit();
  }
});
