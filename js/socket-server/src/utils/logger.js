function formatTimestamp() {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  const seconds = now.getSeconds().toString().padStart(2, '0');
  const milliseconds = now.getMilliseconds().toString().padStart(3, '0');
  const year = now.getFullYear();
  const month = (now.getMonth() + 1).toString().padStart(2, '0');
  const day = now.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}.${milliseconds}`;
}

function truncateLines(str, max = 150) {
  return str
    .toString()
    .split('\n')
    .map(line => line.length > max ? line.slice(0, max) + '...' : line)
    .join('\n');
}

function log(message, type = 'INFO') {
  const timestamp = formatTimestamp();
  const logMessage = `${timestamp} [${type.toUpperCase()}] ${truncateLines(message)}`;
  console.log(logMessage);
}

function info(message) {
  log(message, 'INFO');
}

function error(message) {
  log(message, 'ERROR');
}

function warn(message) {
  log(message, 'WARN');
}

function debug(message) {
  log(message, 'DEBUG');
}

function socketEvent(event, socketId, payload = {}) {
  const payloadStr = typeof payload === 'object' ? JSON.stringify(payload) : payload;
  log(`Socket event '${event}' from ${socketId}: ${payloadStr}`, 'SOCKET');
}

function socketConnection(socketId, details = '') {
  log(`Socket connected: ${socketId} ${details}`, 'SOCKET');
}

function socketDisconnect(socketId, reason, name = 'unknown') {
  log(`Socket disconnected: ${socketId} (${name}), reason: ${reason}`, 'SOCKET');
}

module.exports = {
  formatTimestamp,
  log,
  info,
  error,
  warn,
  debug,
  socketEvent,
  socketConnection,
  socketDisconnect
};
