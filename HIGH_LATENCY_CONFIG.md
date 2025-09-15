# High Latency Network Configuration Guide

This guide explains how to handle high network latency issues with the Coffee Shop Queue System's SocketIO implementation.

## Server-Side Improvements Made

### 1. Enhanced SocketIO Configuration

- **Increased ping timeout**: 60 seconds (default: 20s)
- **Ping interval**: 25 seconds (default: 25s)
- **Compression enabled**: For large payloads
- **Connection retry**: Always connect enabled
- **Error handling**: Safe emit functions with error catching

### 2. Connection Monitoring

- Real-time client tracking
- Room membership monitoring
- Connection health endpoints
- Detailed logging for debugging

### 3. HTTP Polling Fallback

- `/api/queue/poll` endpoint for when SocketIO fails
- Combined queue status and analytics in single request
- Timestamp tracking for change detection

## Client-Side Configuration

### SocketIO Client Setup (JavaScript)

```javascript
import io from "socket.io-client";

// Configure for high latency networks
const socket = io("http://localhost:5002", {
	// Connection settings
	timeout: 60000, // 60 seconds
	forceNew: true, // Force new connection

	// Reconnection settings
	reconnection: true,
	reconnectionDelay: 1000, // Start with 1 second
	reconnectionDelayMax: 5000, // Max 5 seconds
	maxReconnectionAttempts: 10,

	// Transport settings
	transports: ["websocket", "polling"], // Fallback to polling
	upgrade: true, // Allow transport upgrades

	// Ping/pong settings
	pingTimeout: 60000, // Match server timeout
	pingInterval: 25000, // Match server interval
});

// Connection event handlers
socket.on("connect", () => {
	console.log("Connected to server");
	// Join appropriate rooms
	socket.emit("join_queue_room");
	// For staff: socket.emit('join_staff_room');
});

socket.on("disconnect", reason => {
	console.log("Disconnected:", reason);
	// Implement fallback to HTTP polling
	if (reason === "io server disconnect" || reason === "io client disconnect") {
		startPollingFallback();
	}
});

socket.on("reconnect", attemptNumber => {
	console.log("Reconnected after", attemptNumber, "attempts");
	// Rejoin rooms
	socket.emit("join_queue_room");
});

// Handle server events
socket.on("queue_updated", data => {
	updateQueueDisplay(data);
});

socket.on("analytics_updated", data => {
	updateAnalyticsDisplay(data);
});

// Ping/pong for connection health
socket.on("ping", () => {
	socket.emit("pong");
});

// Send periodic ping to server
setInterval(() => {
	if (socket.connected) {
		socket.emit("ping");
	}
}, 30000); // Every 30 seconds
```

### HTTP Polling Fallback

```javascript
let pollingInterval = null;
let lastTimestamp = null;

function startPollingFallback() {
	console.log("Starting HTTP polling fallback");

	// Clear any existing polling
	if (pollingInterval) {
		clearInterval(pollingInterval);
	}

	// Poll every 5 seconds
	pollingInterval = setInterval(async () => {
		try {
			const response = await fetch("/api/queue/poll");
			const data = await response.json();

			// Check if data has changed
			if (data.timestamp !== lastTimestamp) {
				lastTimestamp = data.timestamp;

				// Update UI with new data
				updateQueueDisplay(data.queue_status);
				updateAnalyticsDisplay(data.analytics);
			}
		} catch (error) {
			console.error("Polling error:", error);
		}
	}, 5000);
}

function stopPollingFallback() {
	if (pollingInterval) {
		clearInterval(pollingInterval);
		pollingInterval = null;
	}
}

// Switch back to SocketIO when reconnected
socket.on("connect", () => {
	stopPollingFallback();
	// Resume normal SocketIO operation
});
```

### React Hook Example

```javascript
import { useState, useEffect, useRef } from "react";
import io from "socket.io-client";

export function useQueueSystem() {
	const [queueStatus, setQueueStatus] = useState(null);
	const [analytics, setAnalytics] = useState(null);
	const [connectionStatus, setConnectionStatus] = useState("disconnected");
	const socketRef = useRef(null);
	const pollingRef = useRef(null);

	useEffect(() => {
		// Initialize SocketIO connection
		const socket = io("http://localhost:5002", {
			timeout: 60000,
			reconnection: true,
			reconnectionDelay: 1000,
			reconnectionDelayMax: 5000,
			maxReconnectionAttempts: 10,
			transports: ["websocket", "polling"],
		});

		socketRef.current = socket;

		// Connection handlers
		socket.on("connect", () => {
			setConnectionStatus("connected");
			socket.emit("join_queue_room");
			stopPolling();
		});

		socket.on("disconnect", reason => {
			setConnectionStatus("disconnected");
			if (reason === "io server disconnect") {
				startPolling();
			}
		});

		socket.on("reconnect", () => {
			setConnectionStatus("connected");
			socket.emit("join_queue_room");
			stopPolling();
		});

		// Data handlers
		socket.on("queue_updated", setQueueStatus);
		socket.on("analytics_updated", setAnalytics);

		// Cleanup
		return () => {
			socket.disconnect();
			stopPolling();
		};
	}, []);

	const startPolling = () => {
		if (pollingRef.current) return;

		pollingRef.current = setInterval(async () => {
			try {
				const response = await fetch("/api/queue/poll");
				const data = await response.json();
				setQueueStatus(data.queue_status);
				setAnalytics(data.analytics);
			} catch (error) {
				console.error("Polling failed:", error);
			}
		}, 5000);
	};

	const stopPolling = () => {
		if (pollingRef.current) {
			clearInterval(pollingRef.current);
			pollingRef.current = null;
		}
	};

	return {
		queueStatus,
		analytics,
		connectionStatus,
		isConnected: connectionStatus === "connected",
	};
}
```

## Monitoring and Debugging

### Server Endpoints

- `GET /api/connections` - View active connections
- `GET /api/health` - Server health check
- `GET /api/queue/poll` - HTTP polling fallback

### Client-Side Debugging

```javascript
// Enable SocketIO debugging
localStorage.debug = "socket.io-client:*";

// Monitor connection quality
socket.on("connect", () => {
	console.log("Connection quality:", socket.io.engine.transport.name);
});

socket.io.engine.on("upgrade", () => {
	console.log("Upgraded to:", socket.io.engine.transport.name);
});
```

## Best Practices

1. **Always implement fallback**: Use HTTP polling when SocketIO fails
2. **Monitor connection quality**: Track transport type and reconnection events
3. **Handle reconnections gracefully**: Rejoin rooms and sync state
4. **Use appropriate timeouts**: Match server and client timeout settings
5. **Implement exponential backoff**: For reconnection attempts
6. **Cache critical data**: Store important state locally for offline scenarios

## Troubleshooting

### Common Issues

1. **Frequent disconnections**: Check network stability and increase timeouts
2. **Missing updates**: Ensure proper room joining and fallback polling
3. **Slow updates**: Consider reducing ping interval or using compression
4. **Memory leaks**: Properly clean up intervals and event listeners

### Network Quality Detection

```javascript
function detectNetworkQuality() {
	const connection =
		navigator.connection ||
		navigator.mozConnection ||
		navigator.webkitConnection;

	if (connection) {
		const { effectiveType, downlink, rtt } = connection;

		if (effectiveType === "slow-2g" || effectiveType === "2g" || rtt > 1000) {
			// Use more aggressive polling and longer timeouts
			return "poor";
		} else if (effectiveType === "3g" || rtt > 500) {
			return "fair";
		} else {
			return "good";
		}
	}

	return "unknown";
}
```

This configuration should significantly improve the reliability of real-time updates in high latency network conditions.
