const { SerialPort } = require('serialport');

/**
 * Send G-code to the plotter over serial port.
 * Handles GRBL flow control (wait for 'ok' after each command).
 */
async function sendGcode(gcode, portPath = 'COM3') {
  const commands = gcode
    .split('\n')
    .map(l => l.trim())
    .filter(l => l && !l.startsWith(';'));

  const port = new SerialPort({
    path: portPath,
    baudRate: 115200,
  });

  // Wait for port to open
  await new Promise((resolve, reject) => {
    port.on('open', resolve);
    port.on('error', reject);
  });

  // Read responses
  let buffer = '';

  function readResponse(timeout = 5000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Serial timeout')), timeout);
      const check = () => {
        const idx = buffer.indexOf('\n');
        if (idx !== -1) {
          const line = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 1);
          clearTimeout(timer);
          resolve(line);
        } else {
          setTimeout(check, 10);
        }
      };
      check();
    });
  }

  port.on('data', (data) => {
    buffer += data.toString();
  });

  // Wait for GRBL startup message
  await new Promise(r => setTimeout(r, 1500));

  // Unlock alarm if present
  port.write('$X\n');
  await readResponse();

  // Send each command, wait for 'ok'
  for (let i = 0; i < commands.length; i++) {
    const cmd = commands[i];
    port.write(cmd + '\n');

    try {
      const resp = await readResponse();
      if (resp.startsWith('error')) {
        console.warn(`GRBL error on "${cmd}": ${resp}`);
      }
    } catch (e) {
      console.warn(`Timeout on command ${i}: ${cmd}`);
    }
  }

  // Close port
  await new Promise(r => setTimeout(r, 500));
  port.close();

  return { commandsSent: commands.length };
}

module.exports = { sendGcode };
