const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow;
let backendProcess;
let backendUrl;

const projectRoot = path.resolve(__dirname, '..');
const backendDir = path.join(projectRoot, 'backend');
const frontendDir = path.join(projectRoot, 'frontend');

function readBackendConfig() {
  const envPath = path.join(backendDir, '.env');
  const values = {};
  const contents = fs.readFileSync(envPath, 'utf8');

  for (const line of contents.split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!match) continue;
    values[match[1]] = match[2].replace(/^(["'])(.*)\1$/, '$2');
  }

  const port = Number(values.APP_PORT);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error('APP_PORT must be a valid port in backend/.env.');
  }
  if (Boolean(values.TLS_CERTFILE) !== Boolean(values.TLS_KEYFILE)) {
    throw new Error('Set both TLS_CERTFILE and TLS_KEYFILE in backend/.env.');
  }

  const protocol = values.TLS_CERTFILE ? 'https' : 'http';
  const url = `${protocol}://127.0.0.1:${port}`;
  return { port, url };
}

function isBackendRunning(url) {
  return new Promise((resolve) => {
    const transport = url.startsWith('https:') ? require('https') : require('http');
    const req = transport.get(`${url}/api/health`, (res) => {
      res.resume();
      resolve(res.statusCode && res.statusCode < 500);
    });

    req.on('error', () => resolve(false));
    req.end();
  });
}

function launchBackend(url) {
  return isBackendRunning(url).then((alreadyRunning) => {
    if (alreadyRunning) {
      return;
    }

    const env = { ...process.env, PYTHONPATH: backendDir };
    const pythonExecutable = process.platform === 'win32'
      ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
      : path.join(backendDir, '.venv', 'bin', 'python');

    if (!require('fs').existsSync(pythonExecutable)) {
      throw new Error(`Python runtime not found: ${pythonExecutable}`);
    }

    backendProcess = spawn(pythonExecutable, ['-m', 'app.server'], {
      cwd: backendDir,
      env,
      shell: false,
      stdio: 'inherit',
    });

    backendProcess.on('error', (error) => {
      console.error('Failed to start backend:', error.message);
    });
  });
}

function waitForApp(url, timeoutMs = 30000) {
  const startedAt = Date.now();

  return new Promise((resolve, reject) => {
    const tryUrl = () => {
      if (Date.now() - startedAt > timeoutMs) {
        reject(new Error('Backend did not start in time.'));
        return;
      }

      const transport = url.startsWith('https:') ? require('https') : require('http');
      const req = transport.get(url, (res) => {
        res.resume();
        if (res.statusCode && res.statusCode < 500) {
          resolve();
          return;
        }
        setTimeout(tryUrl, 500);
      });

      req.on('error', () => setTimeout(tryUrl, 500));
      req.end();
    };

    tryUrl();
  });
}

function createWindow(url = backendUrl) {
  mainWindow = new BrowserWindow({
    width: 1366,
    height: 900,
    minWidth: 1040,
    minHeight: 700,
    backgroundColor: '#09090b',
    autoHideMenuBar: true,
    title: 'Model Khôi Phục Chữ Viết',
    icon: path.join(frontendDir, 'public', 'logo.svg'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
    },
  });

  mainWindow.loadURL(url).catch((error) => {
    dialog.showErrorBox('Could not open the application', error.message);
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  let backendConfig;
  try {
    backendConfig = readBackendConfig();
  } catch (error) {
    dialog.showErrorBox('Invalid backend configuration', error.message);
    app.quit();
    return;
  }
  backendUrl = backendConfig.url;
  const healthUrl = `${backendConfig.url}/api/health`;
  launchBackend(backendConfig.url)
    .then(() => waitForApp(healthUrl))
    .then(() => {
      createWindow(backendConfig.url);
    })
    .catch((error) => {
      dialog.showErrorBox('Could not start the application', error.message);
      app.quit();
    });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
  }

  if (process.platform !== 'darwin') {
    app.quit();
  }
});
