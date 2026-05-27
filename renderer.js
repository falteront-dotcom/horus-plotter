// Horus Plotter — Renderer
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const previewSection = document.getElementById('preview-section');
const settingsSection = document.getElementById('settings-section');
const actionsSection = document.getElementById('actions-section');
const originalCanvas = document.getElementById('original-canvas');
const previewCanvas = document.getElementById('preview-canvas');
const btnConvert = document.getElementById('btn-convert');
const btnSend = document.getElementById('btn-send');
const statusEl = document.getElementById('status');
const portSelect = document.getElementById('port-select');

let currentImagePath = null;
let currentGcode = null;

// ─── Port Discovery ─────────────────────────────────────────────────────────
async function refreshPorts() {
  try {
    const ports = await window.horus.listPorts();
    portSelect.innerHTML = '';
    if (ports.length === 0) {
      portSelect.innerHTML = '<option value="COM3">COM3 (default)</option>';
      return;
    }
    for (const p of ports) {
      const opt = document.createElement('option');
      opt.value = p.path;
      opt.textContent = p.manufacturer ? `${p.path} (${p.manufacturer})` : p.path;
      portSelect.appendChild(opt);
    }
  } catch {
    portSelect.innerHTML = '<option value="COM3">COM3 (default)</option>';
  }
}

refreshPorts();

// ─── Drag & Drop ────────────────────────────────────────────────────────────
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    loadImage(file.path);
  }
});

fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) {
    // Electron gives file.path for real filesystem access
    loadImage(file.path);
  }
});

// ─── Image Loading ──────────────────────────────────────────────────────────
function loadImage(filePath) {
  currentImagePath = filePath;
  currentGcode = null;
  btnSend.disabled = true;

  // Show original image
  const img = new Image();
  img.onload = () => {
    const maxW = 400;
    const scale = maxW / img.width;
    originalCanvas.width = img.width * scale;
    originalCanvas.height = img.height * scale;
    const ctx = originalCanvas.getContext('2d');
    ctx.drawImage(img, 0, 0, originalCanvas.width, originalCanvas.height);

    // Clear preview
    previewCanvas.width = originalCanvas.width;
    previewCanvas.height = originalCanvas.height;
    const pctx = previewCanvas.getContext('2d');
    pctx.fillStyle = '#000';
    pctx.fillRect(0, 0, previewCanvas.width, previewCanvas.height);
    pctx.fillStyle = '#333';
    pctx.font = '14px sans-serif';
    pctx.textAlign = 'center';
    pctx.fillText('Click "Generate Preview"', previewCanvas.width / 2, previewCanvas.height / 2);
  };
  img.src = filePath;

  // Update drop zone
  const dropContent = dropZone.querySelector('.drop-content');
  dropContent.querySelector('p').textContent = filePath.split(/[\\/]/).pop();
  dropContent.querySelector('.hint').textContent = 'click to change';

  // Show sections
  previewSection.classList.remove('hidden');
  settingsSection.classList.remove('hidden');
  actionsSection.classList.remove('hidden');

  setStatus('Image loaded. Click "Generate Preview".', '');
}

// ─── Convert ────────────────────────────────────────────────────────────────
btnConvert.addEventListener('click', async () => {
  if (!currentImagePath) return;

  setStatus('Generating G-code...', 'working');
  btnConvert.disabled = true;

  const params = {
    imagePath: currentImagePath,
    style: document.getElementById('style').value,
    width: document.getElementById('width').value,
    penDown: document.getElementById('penDown').value,
    penUp: document.getElementById('penUp').value,
    speed: document.getElementById('speed').value,
    spacing: document.getElementById('spacing').value,
  };

  try {
    const result = await window.horus.convertImage(params);

    if (result.success) {
      currentGcode = result.gcode;
      btnSend.disabled = false;
      drawPreview(result.preview);
      const lines = result.gcode.split('\n').filter(l => l.trim() && !l.startsWith(';')).length;
      setStatus(`G-code generated: ${lines} commands`, 'success');
    } else {
      setStatus('Error: ' + result.error, 'error');
    }
  } catch (err) {
    setStatus('Error: ' + err.message, 'error');
  }

  btnConvert.disabled = false;
});

// ─── Send ───────────────────────────────────────────────────────────────────
btnSend.addEventListener('click', async () => {
  if (!currentGcode) return;

  const port = portSelect.value;
  setStatus(`Sending to ${port}...`, 'working');
  btnSend.disabled = true;
  btnConvert.disabled = true;

  try {
    const result = await window.horus.sendGcode({
      gcode: currentGcode,
      port: port,
    });

    if (result.success) {
      setStatus('Plot complete!', 'success');
    } else {
      setStatus('Error: ' + result.error, 'error');
    }
  } catch (err) {
    setStatus('Error: ' + err.message, 'error');
  }

  btnSend.disabled = false;
  btnConvert.disabled = false;
});

// ─── Preview Drawing ───────────────────────────────────────────────────────
function drawPreview(preview) {
  if (!preview || preview.length === 0) return;

  // Find bounds
  let maxX = 0, maxY = 0;
  for (const item of preview) {
    if (item.type === 'line') {
      maxX = Math.max(maxX, item.x1, item.x2);
      maxY = Math.max(maxY, item.y1, item.y2);
    } else if (item.type === 'circle') {
      maxX = Math.max(maxX, item.cx + item.r);
      maxY = Math.max(maxY, item.cy + item.r);
    } else if (item.type === 'dot' || item.type === 'point') {
      maxX = Math.max(maxX, item.cx || item.x);
      maxY = Math.max(maxY, item.cy || item.y);
    }
  }

  const padding = 10;
  const canvasW = previewCanvas.width;
  const canvasH = previewCanvas.height;
  const scaleX = (canvasW - padding * 2) / (maxX || 1);
  const scaleY = (canvasH - padding * 2) / (maxY || 1);
  const scale = Math.min(scaleX, scaleY);
  const offsetX = (canvasW - maxX * scale) / 2;
  const offsetY = (canvasH - maxY * scale) / 2;

  const ctx = previewCanvas.getContext('2d');
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, canvasW, canvasH);
  ctx.strokeStyle = '#6c63ff';
  ctx.fillStyle = '#6c63ff';
  ctx.lineWidth = 1;

  for (const item of preview) {
    if (item.type === 'line') {
      ctx.beginPath();
      ctx.moveTo(item.x1 * scale + offsetX, item.y1 * scale + offsetY);
      ctx.lineTo(item.x2 * scale + offsetX, item.y2 * scale + offsetY);
      ctx.stroke();
    } else if (item.type === 'circle') {
      ctx.beginPath();
      ctx.arc(item.cx * scale + offsetX, item.cy * scale + offsetY, item.r * scale, 0, Math.PI * 2);
      ctx.stroke();
    } else if (item.type === 'dot') {
      ctx.fillRect(item.cx * scale + offsetX - 1, item.cy * scale + offsetY - 1, 2, 2);
    } else if (item.type === 'point') {
      ctx.fillRect(item.x * scale + offsetX, item.y * scale + offsetY, 1, 1);
    }
  }
}

// ─── Helpers ────────────────────────────────────────────────────────────────
function setStatus(msg, type) {
  statusEl.textContent = msg;
  statusEl.className = 'status' + (type ? ' ' + type : '');
}
