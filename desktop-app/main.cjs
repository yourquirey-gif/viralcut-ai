const { app, BrowserWindow, dialog, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { promisify } = require("node:util");
const { execFile } = require("node:child_process");

const execFileAsync = promisify(execFile);
const DASHBOARD_URL = "https://viralcut-ai-ayuddys-projects.vercel.app";
const ENGINE_HEALTH = "http://127.0.0.1:8765/health";
const ENGINE_API = "http://127.0.0.1:8765/api/v1";
let mainWindow;
let engineProcess;
let quitting = false;
let logStream;

function setStatus(message) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    const safe = JSON.stringify(message);
    mainWindow.webContents.executeJavaScript(
      `document.getElementById("status").textContent = ${safe};`
    ).catch(() => {});
  }
}

function showStartupWindow() {
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 720,
    minWidth: 820,
    minHeight: 560,
    backgroundColor: "#0b1020",
    title: "ViralCut",
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });
  const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ViralCut</title><style>
  *{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 50% 20%,#1c2a4a,#0b1020 65%);color:#eef2ff;font:15px Segoe UI,Arial,sans-serif}.panel{width:min(560px,90vw);padding:42px;border:1px solid #293653;border-radius:22px;background:#111a2dcc;box-shadow:0 24px 80px #0006}h1{margin:0 0 8px;font-size:34px;letter-spacing:-1px}.sub{color:#9aa8c5;margin-bottom:30px}.spinner{width:22px;height:22px;border:3px solid #42516f;border-top-color:#8bb8ff;border-radius:50%;animation:r .8s linear infinite;display:inline-block;vertical-align:middle;margin-right:12px}@keyframes r{to{transform:rotate(360deg)}}#status{line-height:1.7;color:#dbe5ff}.note{margin-top:24px;padding-top:18px;border-top:1px solid #293653;color:#8d9ab5;font-size:12px}
  </style></head><body><main class="panel"><h1>ViralCut</h1><div class="sub">Your PC. Your processing power.</div><p><span class="spinner"></span><span id="status">Preparing your local clipping engine...</span></p><div class="note">The first launch installs local Python packages and may take several minutes. Keep this window open.</div></main></body></html>`;
  mainWindow.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(html));
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

function packagedEnginePath() {
  if (app.isPackaged) return path.join(process.resourcesPath, "engine");
  return path.join(__dirname, "..", "engine");
}

function localEnginePath() {
  return path.join(app.getPath("userData"), "engine");
}

async function ensureFfmpeg() {
  try {
    await execFileAsync("where.exe", ["ffmpeg"], { windowsHide: true });
    return;
  } catch {}
  setStatus("FFmpeg was not found. Trying to install it with Windows Package Manager...");
  try {
    await execFileAsync("winget", [
      "install", "--id", "Gyan.FFmpeg.Shared", "--exact",
      "--accept-package-agreements", "--accept-source-agreements"
    ], { windowsHide: true, timeout: 600000, maxBuffer: 4 * 1024 * 1024 });
    const refreshed = await execFileAsync("powershell.exe", [
      "-NoProfile", "-Command",
      '$m=[Environment]::GetEnvironmentVariable("Path","Machine");$u=[Environment]::GetEnvironmentVariable("Path","User");[Console]::Write($m+";"+$u)'
    ], { windowsHide: true });
    process.env.PATH = refreshed.stdout + ";" + process.env.PATH;
    await execFileAsync("where.exe", ["ffmpeg"], { windowsHide: true });
  } catch (error) {
    throw new Error("FFmpeg is required. Install it from https://ffmpeg.org/download.html, add its bin folder to PATH, then reopen ViralCut. " + (error.message || ""));
  }
}

async function prepareEngine() {
  const source = packagedEnginePath();
  const target = localEnginePath();
  if (!fs.existsSync(path.join(source, "app.py"))) {
    throw new Error("ViralCut engine files are missing from this installation. Reinstall the desktop app.");
  }
  fs.mkdirSync(target, { recursive: true });
  fs.cpSync(source, target, {
    recursive: true,
    force: true,
    filter: (src) => !src.includes(path.sep + "data" + path.sep) &&
      !src.includes(path.sep + ".venv" + path.sep) &&
      !src.includes(path.sep + "__pycache__" + path.sep)
  });

  setStatus("Checking Python 3.11...");
  try {
    await execFileAsync("py", ["-3.11", "--version"], { windowsHide: true });
  } catch {
    throw new Error("Python 3.11 is required. Install Python 3.11 for Windows from https://www.python.org/downloads/release/python-3119/ and enable the Python Launcher, then reopen ViralCut.");
  }
  await ensureFfmpeg();

  const venvPython = path.join(target, ".venv", "Scripts", "python.exe");
  if (!fs.existsSync(venvPython)) {
    setStatus("Creating the private ViralCut Python environment...");
    await execFileAsync("py", ["-3.11", "-m", "venv", path.join(target, ".venv")], {
      windowsHide: true,
      timeout: 120000
    });
  }

  setStatus("Installing or updating yt-dlp and local AI packages...");
  await execFileAsync(venvPython, ["-m", "pip", "install", "--upgrade", "pip"], {
    cwd: target, windowsHide: true, timeout: 300000, maxBuffer: 8 * 1024 * 1024
  });
  await execFileAsync(venvPython, ["-m", "pip", "install", "-r", path.join(target, "requirements.txt")], {
    cwd: target, windowsHide: true, timeout: 900000, maxBuffer: 12 * 1024 * 1024
  });
  return { target, venvPython };
}

async function waitForEngine() {
  for (let i = 0; i < 45; i++) {
    if (engineProcess && engineProcess.exitCode !== null) {
      throw new Error("The local engine stopped during startup. Check the engine log in " + app.getPath("userData"));
    }
    try {
      const response = await fetch(ENGINE_HEALTH, { signal: AbortSignal.timeout(2500) });
      if (response.ok) {
        const body = await response.json();
        if (body.status === "ok" && body.tools.ffmpeg && body.tools.yt_dlp) return;
      }
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  throw new Error("Local Engine did not become ready within 45 seconds. Check viralcut-engine.log in " + app.getPath("userData"));
}

async function startEngine(engine) {
  try {
    const existing = await fetch(ENGINE_HEALTH, { signal: AbortSignal.timeout(2000) });
    if (existing.ok) {
      const body = await existing.json();
      if (body.status === "ok" && body.tools.ffmpeg && body.tools.yt_dlp) return;
    }
  } catch {}
  const logPath = path.join(app.getPath("userData"), "viralcut-engine.log");
  logStream = fs.createWriteStream(logPath, { flags: "a" });
  const env = {
    ...process.env,
    PATH: path.join(engine.target, ".venv", "Scripts") + path.delimiter + process.env.PATH,
    VIRALCUT_ALLOWED_ORIGINS: "https://viralcut-ai-ayuddys-projects.vercel.app,https://viralcut-ai-beta.vercel.app",
    VIRALCUT_DATA_DIR: path.join(app.getPath("userData"), "data")
  };
  engineProcess = spawn(engine.venvPython, [
    "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8765"
  ], { cwd: engine.target, env, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
  engineProcess.stdout.on("data", chunk => logStream.write(chunk));
  engineProcess.stderr.on("data", chunk => logStream.write(chunk));
  engineProcess.on("error", error => logStream.write(String(error) + "\n"));
  await waitForEngine();
}

async function openDashboard() {
  setStatus("Local Engine is ready. Opening your ViralCut workspace...");
  await mainWindow.loadURL(DASHBOARD_URL);
  mainWindow.setTitle("ViralCut");
}

async function stopEngineSafely() {
  if (!engineProcess || engineProcess.exitCode !== null) return;
  try {
    const response = await fetch(ENGINE_API + "/jobs", { signal: AbortSignal.timeout(3000) });
    const data = await response.json();
    const active = (data.jobs || []).filter(job => ["checking", "capturing", "stopping"].includes(job.status));
    for (const job of active) {
      await fetch(ENGINE_API + "/jobs/" + encodeURIComponent(job.id) + "/stop", {
        method: "POST", signal: AbortSignal.timeout(3000)
      }).catch(() => {});
    }
    for (let i = 0; i < 12 && active.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 500));
      const check = await fetch(ENGINE_API + "/jobs", { signal: AbortSignal.timeout(2000) }).catch(() => null);
      if (!check) break;
      const latest = await check.json();
      if (!(latest.jobs || []).some(job => ["checking", "capturing", "stopping"].includes(job.status))) break;
    }
  } catch {}
  engineProcess.kill();
  if (logStream) logStream.end();
}

app.on("before-quit", event => {
  if (quitting) return;
  event.preventDefault();
  quitting = true;
  stopEngineSafely().finally(() => app.exit(0));
});

app.whenReady().then(async () => {
  showStartupWindow();
  try {
    const engine = await prepareEngine();
    setStatus("Starting the local engine on this PC...");
    await startEngine(engine);
    await openDashboard();
  } catch (error) {
    setStatus(error.message || "ViralCut could not start.");
    dialog.showMessageBox(mainWindow, {
      type: "error",
      title: "ViralCut setup required",
      message: error.message || "ViralCut could not start.",
      detail: "Your existing projects and recordings are kept on this PC. Fix the requirement above and launch ViralCut again.",
      buttons: ["OK"]
    });
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
