const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { convertImageToGcode } = require('./gcode/converter');
const { sendGcode } = require('./gcode/sender');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 750,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    title: 'Horus Plotter',
    backgroundColor: '#1a1a2e',
    autoHideMenuBar: true,
  });

  mainWindow.loadFile('index.html');
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  app.quit();
});

// IPC handlers
ipcMain.handle('convert-image', async (_event, { imagePath, style, width, penDown, penUp, speed, spacing }) => {
  try {
    const result = await convertImageToGcode(imagePath, {
      style,
      width: parseFloat(width),
      penDown: parseFloat(penDown),
      penUp: parseFloat(penUp),
      speed: parseInt(speed),
      spacing: parseFloat(spacing),
    });
    return { success: true, gcode: result.gcode, preview: result.preview };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

ipcMain.handle('send-gcode', async (_event, { gcode, port }) => {
  try {
    await sendGcode(gcode, port);
    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

ipcMain.handle('list-ports', async () => {
  try {
    const { SerialPort } = require('serialport');
    const ports = await SerialPort.list();
    return ports.map(p => ({ path: p.path, manufacturer: p.manufacturer }));
  } catch (err) {
    return [];
  }
});
