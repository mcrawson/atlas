/**
 * ATLAS 2.0 Web Dashboard JavaScript
 *
 * Handles WebSocket connections and real-time updates
 */

class ATLASWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.statusElement = document.getElementById('ws-status');
        this.activityFeed = document.getElementById('activity-feed');

        this.connect();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => this.onOpen();
            this.ws.onclose = () => this.onClose();
            this.ws.onerror = (error) => this.onError(error);
            this.ws.onmessage = (event) => this.onMessage(event);
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.scheduleReconnect();
        }
    }

    onOpen() {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.updateStatus('connected', 'Connected');
    }

    onClose() {
        console.log('WebSocket disconnected');
        this.updateStatus('disconnected', 'Disconnected');
        this.scheduleReconnect();
    }

    onError(error) {
        console.error('WebSocket error:', error);
        this.updateStatus('disconnected', 'Error');
    }

    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }

    handleMessage(data) {
        const type = data.type;

        switch (type) {
            case 'ping':
                this.send({ type: 'pong' });
                break;

            case 'init':
                this.updateAgentStatus(data.agents);
                break;

            case 'agent_status':
                this.updateSingleAgentStatus(data.agent, data.data);
                this.addActivity(data);
                break;

            case 'agent_start':
            case 'agent_complete':
                this.addActivity(data);
                break;

            case 'workflow_start':
                this.addActivity({
                    type: 'workflow',
                    message: `Workflow started: ${data.data.task.substring(0, 50)}...`,
                    timestamp: data.timestamp
                });
                break;

            case 'workflow_complete':
                this.addActivity({
                    type: 'workflow',
                    message: `Workflow completed. Verdict: ${data.data.final_verdict}`,
                    timestamp: data.timestamp
                });
                break;

            case 'workflow_error':
                this.addActivity({
                    type: 'error',
                    message: `Workflow error: ${data.data.error}`,
                    timestamp: data.timestamp
                });
                break;

            case 'task_complete':
                this.addActivity({
                    type: 'task',
                    message: 'Task completed successfully',
                    timestamp: new Date().toISOString()
                });
                break;

            case 'task_error':
                this.addActivity({
                    type: 'error',
                    message: `Task error: ${data.error}`,
                    timestamp: new Date().toISOString()
                });
                break;

            default:
                console.log('Unknown message type:', type, data);
        }
    }

    updateStatus(className, text) {
        if (this.statusElement) {
            this.statusElement.className = `status-indicator ${className}`;
            this.statusElement.textContent = text;
        }
    }

    updateAgentStatus(agents) {
        // This will be handled by HTMX polling, but we can force a refresh
        const container = document.getElementById('agent-status-container');
        if (container) {
            htmx.trigger(container, 'htmx:load');
        }
    }

    updateSingleAgentStatus(agentName, data) {
        // Update the specific agent card if it exists
        const cards = document.querySelectorAll('.agent-card');
        cards.forEach(card => {
            const name = card.querySelector('.agent-name');
            if (name && name.textContent.toLowerCase().includes(agentName)) {
                // Update status indicator
                const indicator = card.querySelector('.status-indicator');
                if (indicator) {
                    indicator.className = `status-indicator ${data.status}`;
                    indicator.innerHTML = data.status === 'working'
                        ? '<span class="spinner"></span>' + data.status
                        : data.status;
                }

                // Update current task
                let taskDiv = card.querySelector('.current-task');
                if (data.task) {
                    if (!taskDiv) {
                        taskDiv = document.createElement('div');
                        taskDiv.className = 'current-task';
                        card.appendChild(taskDiv);
                    }
                    taskDiv.innerHTML = `
                        <span class="task-label">Working on:</span>
                        <span class="task-text">${data.task.substring(0, 50)}...</span>
                    `;
                } else if (taskDiv) {
                    taskDiv.remove();
                }

                // Update card class
                card.classList.remove('status-idle', 'status-working', 'status-thinking',
                    'status-completed', 'status-error');
                card.classList.add(`status-${data.status}`);
            }
        });
    }

    addActivity(data) {
        if (!this.activityFeed) return;

        // Remove empty state if present
        const emptyState = this.activityFeed.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const item = document.createElement('div');
        item.className = `activity-item type-${data.type}`;

        const time = data.timestamp
            ? new Date(data.timestamp).toLocaleTimeString()
            : new Date().toLocaleTimeString();

        let message = data.message || '';
        if (!message && data.data) {
            if (data.type === 'agent_start') {
                message = `Starting ${data.data.phase}`;
            } else if (data.type === 'agent_complete') {
                message = `Completed ${data.data.phase}`;
                if (data.data.verdict) {
                    message += ` - ${data.data.verdict}`;
                }
            } else if (data.type === 'agent_status') {
                message = `Status: ${data.data.status}`;
            }
        }

        const agentName = data.agent_name || data.agent || '';
        const agentDisplay = agentName ? this.formatAgentName(agentName) : '';

        item.innerHTML = `
            <span class="activity-time">${time}</span>
            ${agentDisplay ? `<span class="activity-agent">${agentDisplay}</span>` : ''}
            <span class="activity-message">${message}</span>
        `;

        // Insert at the top
        this.activityFeed.insertBefore(item, this.activityFeed.firstChild);

        // Keep only last 50 items
        const items = this.activityFeed.querySelectorAll('.activity-item');
        if (items.length > 50) {
            items[items.length - 1].remove();
        }
    }

    formatAgentName(name) {
        const icons = {
            'architect': '&#x1F4D0;',
            'mason': '&#x1F528;',
            'oracle': '&#x1F52E;'
        };

        const displayNames = {
            'architect': 'Architect',
            'mason': 'Mason',
            'oracle': 'Oracle'
        };

        const baseName = name.split('_')[0].toLowerCase();
        const icon = icons[baseName] || '';
        const display = displayNames[baseName] || name;

        return `${icon} ${display}`;
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            this.updateStatus('disconnected', 'Connection failed');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        this.updateStatus('disconnected', 'Reconnecting...');

        setTimeout(() => this.connect(), delay);
    }

    executeTask(task, mode = 'sequential') {
        this.send({
            type: 'execute_task',
            task: task,
            mode: mode
        });
    }
}

// Initialize WebSocket connection when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.atlasWS = new ATLASWebSocket();
});

// Handle HTMX events
document.addEventListener('htmx:afterRequest', (event) => {
    // Handle form submission success
    if (event.detail.successful) {
        // Clear form inputs after successful submission
        const form = event.detail.elt;
        if (form.tagName === 'FORM') {
            const inputs = form.querySelectorAll('input[type="text"], textarea');
            inputs.forEach(input => {
                if (!input.name.includes('mode')) {
                    input.value = '';
                }
            });
        }
    }
});

// Handle HTMX request errors
document.addEventListener('htmx:responseError', (event) => {
    console.error('HTMX request error:', event.detail);

    // Show error in activity feed
    if (window.atlasWS) {
        window.atlasWS.addActivity({
            type: 'error',
            message: `Request failed: ${event.detail.xhr.statusText}`,
            timestamp: new Date().toISOString()
        });
    }
});
