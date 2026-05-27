const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('horus', {
  convertImage: (params) => ipcRenderer.invoke('convert-image', params),
  sendGcode: (params) => ipcRenderer.invoke('send-gcode', params),
  listPorts: () => ipcRenderer.invoke('list-ports'),
});
