const http = require('http');
const { Server } = require('socket.io');
const logger = require('./utils/logger');

class SocketServer {
    constructor({ host = 'localhost', port = 8081 } = {}) {
        this.host = host;
        this.port = port;
        this.server = http.createServer((req, res) => {
            res.writeHead(200, { 'Content-Type': 'text/plain' });
            res.end('Socket.IO server running');
        });
        this.io = null;
        this.clients = new Map();
    }

    start() {
        this.io = new Server(this.server, {
            cors: { origin: '*' },
            pingTimeout: 30000,
            pingInterval: 5000,
            connectTimeout: 10000,
            transports: ['websocket', 'polling']
        });

        this.io.use((socket, next) => {
            logger.socketConnection(socket.id, 'New connection attempt');
            next();
        });

        this.io.on('connection', socket => {
            logger.socketConnection(socket.id);
            this.clients.set(socket.id, 'unknown');

            logger.info(`Socket details - id: ${socket.id}, transport: ${socket.conn.transport.name}`);

            // Handle registration specifically
            socket.on('register', (payload, callback) => {
                const name = payload?.clientType || payload?.name || 'unknown';
                this.clients.set(socket.id, name);
                logger.info(`Client registered: ${socket.id} as ${name}`, JSON.stringify(payload));

                if (typeof callback === 'function') {
                    callback({ status: 'registered', id: socket.id, clientType: name });
                }
            });

            // Forward all other events automatically
            socket.onAny((eventName, payload, callback) => {
                // Skip register (handled above) and built-in Socket.IO events
                if (eventName === 'register') return;

                logger.socketEvent(eventName, socket.id, payload);

                // Broadcast to all other clients
                socket.broadcast.emit(eventName, payload);
                logger.info(`Broadcasted ${eventName} to other clients`);

                // Handle acknowledgment callback
                if (typeof callback === 'function') {
                    callback({ status: 'forwarded', event: eventName });
                }
            });

            socket.on('disconnect', (reason) => {
                const name = this.clients.get(socket.id) || 'unknown';
                logger.socketDisconnect(socket.id, reason, name);
                this.clients.delete(socket.id);
            });

            socket.on('error', err => {
                logger.error(`Socket error for ${socket.id}: ${err.message}`);
            });
        });

        this.server.listen(this.port, this.host, () => {
            logger.info(`Socket.IO server started on http://${this.host}:${this.port}`);
        });
    }

    stop() {
        this.io?.close();
        this.server.close();
        logger.info('Server stopped');
    }
}

if (require.main === module) {
    logger.info('Starting Socket.IO Server...');
    
    const host = process.env.HOST || '0.0.0.0';
    const port = parseInt(process.env.PORT) || 8081;
    
    logger.info(`Using configuration: host=${host}, port=${port}`);
    
    const server = new SocketServer({ host, port });
    server.start();
}

module.exports = SocketServer;
