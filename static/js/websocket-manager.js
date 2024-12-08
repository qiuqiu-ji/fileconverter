class WebSocketManager {
    constructor(options = {}) {
        this.options = {
            reconnectAttempts: 3,
            reconnectDelay: 1000,
            debug: false,
            ...options
        };
        
        this.connections = new Map();
        this.attemptCounts = new Map();
    }

    connect(url, handlers) {
        if (this.connections.has(url)) {
            this.log(`WebSocket connection to ${url} already exists`);
            return;
        }

        this.attemptCounts.set(url, 0);
        this.createConnection(url, handlers);
    }

    createConnection(url, handlers) {
        try {
            const ws = new WebSocket(url);
            
            ws.onopen = () => {
                this.log(`Connected to ${url}`);
                this.attemptCounts.set(url, 0);
                if (handlers.onOpen) handlers.onOpen();
            };

            ws.onmessage = (event) => {
                this.log(`Received message from ${url}:`, event.data);
                if (handlers.onMessage) handlers.onMessage(event);
            };

            ws.onclose = (event) => {
                this.log(`Connection to ${url} closed:`, event.code, event.reason);
                this.connections.delete(url);
                
                if (handlers.onClose) handlers.onClose(event);
                
                // 尝试重连
                const attempts = this.attemptCounts.get(url) || 0;
                if (attempts < this.options.reconnectAttempts) {
                    this.attemptCounts.set(url, attempts + 1);
                    setTimeout(() => {
                        this.log(`Attempting to reconnect to ${url}...`);
                        this.createConnection(url, handlers);
                    }, this.options.reconnectDelay);
                }
            };

            ws.onerror = (error) => {
                this.log(`Error in connection to ${url}:`, error);
                if (handlers.onError) handlers.onError(error);
            };

            this.connections.set(url, ws);

        } catch (error) {
            this.log(`Failed to create WebSocket connection to ${url}:`, error);
            if (handlers.onError) handlers.onError(error);
        }
    }

    disconnect(url) {
        const ws = this.connections.get(url);
        if (ws) {
            ws.close();
            this.connections.delete(url);
            this.attemptCounts.delete(url);
            this.log(`Disconnected from ${url}`);
        }
    }

    disconnectAll() {
        for (const url of this.connections.keys()) {
            this.disconnect(url);
        }
    }

    send(url, data) {
        const ws = this.connections.get(url);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(typeof data === 'string' ? data : JSON.stringify(data));
            this.log(`Sent message to ${url}:`, data);
            return true;
        }
        this.log(`Failed to send message to ${url}: Connection not open`);
        return false;
    }

    isConnected(url) {
        const ws = this.connections.get(url);
        return ws && ws.readyState === WebSocket.OPEN;
    }

    log(...args) {
        if (this.options.debug) {
            console.log('[WebSocketManager]', ...args);
        }
    }
} 