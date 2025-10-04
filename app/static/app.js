// Chat application JavaScript with real-time status updates

class ChatApp {
    constructor() {
        this.userId = this.generateUserId();
        this.apiBaseUrl = '/api';
        this.showStatus = true;

        this.elements = {
            messageInput: document.getElementById('messageInput'),
            sendButton: document.getElementById('sendButton'),
            clearButton: document.getElementById('clearButton'),
            chatMessages: document.getElementById('chatMessages'),
            statusPanel: document.getElementById('statusPanel'),
            statusContent: document.getElementById('statusContent'),
            showStatusToggle: document.getElementById('showStatus'),
            userIdDisplay: document.getElementById('userIdDisplay'),
            healthIndicator: document.getElementById('healthIndicator'),
        };

        this.init();
    }

    generateUserId() {
        // Generate or retrieve user ID from localStorage
        let userId = localStorage.getItem('sre_bot_user_id');
        if (!userId) {
            userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            localStorage.setItem('sre_bot_user_id', userId);
        }
        return userId;
    }

    init() {
        // Display user ID
        this.elements.userIdDisplay.textContent = this.userId;

        // Set up event listeners
        this.elements.sendButton.addEventListener('click', () => this.sendMessage());
        this.elements.clearButton.addEventListener('click', () => this.clearHistory());
        this.elements.showStatusToggle.addEventListener('change', (e) => this.toggleStatus(e.target.checked));

        // Handle Enter key in textarea (Shift+Enter for new line)
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
        this.elements.messageInput.addEventListener('input', () => this.autoResizeTextarea());

        // Check health on load
        this.checkHealth();

        // Periodic health check every 30 seconds
        setInterval(() => this.checkHealth(), 30000);

        // Load session history
        this.loadSessionHistory();
    }

    async checkHealth() {
        try {
            const response = await fetch('/health');
            const data = await response.json();

            const indicator = this.elements.healthIndicator;
            const statusDot = indicator.querySelector('.status-dot');
            const statusText = indicator.querySelector('.status-text');

            if (data.status === 'healthy') {
                statusDot.className = 'status-dot healthy';
                statusText.textContent = 'Connected';
            } else {
                statusDot.className = 'status-dot degraded';
                statusText.textContent = 'Degraded';
            }
        } catch (error) {
            const indicator = this.elements.healthIndicator;
            const statusDot = indicator.querySelector('.status-dot');
            const statusText = indicator.querySelector('.status-text');

            statusDot.className = 'status-dot error';
            statusText.textContent = 'Error';
        }
    }

    toggleStatus(show) {
        this.showStatus = show;
        this.elements.statusPanel.style.display = show ? 'block' : 'none';
    }

    autoResizeTextarea() {
        const textarea = this.elements.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }

    async loadSessionHistory() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/session/${this.userId}`);
            const data = await response.json();

            if (data.messages && data.messages.length > 0) {
                // Clear existing messages except system message
                const systemMessage = this.elements.chatMessages.querySelector('.message.system');
                this.elements.chatMessages.innerHTML = '';
                if (systemMessage) {
                    this.elements.chatMessages.appendChild(systemMessage);
                }

                // Add historical messages
                data.messages.forEach(msg => {
                    this.addMessage(msg.content, msg.role);
                });
            }
        } catch (error) {
            console.error('Error loading session history:', error);
        }
    }

    async sendMessage() {
        const message = this.elements.messageInput.value.trim();

        if (!message) return;

        // Disable input while processing
        this.setInputState(false);

        // Add user message to chat
        this.addMessage(message, 'user');

        // Clear input
        this.elements.messageInput.value = '';
        this.autoResizeTextarea();

        // Update status
        this.updateStatus('Sending message...', 'processing');

        try {
            const response = await fetch(`${this.apiBaseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    message: message,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Process events for real-time status
            if (data.events && data.events.length > 0) {
                for (const event of data.events) {
                    this.handleEvent(event);
                    // Small delay between events for visual effect
                    await this.sleep(100);
                }
            }

            // Add assistant response
            if (data.response) {
                this.addMessage(data.response, 'assistant');
            }

            // Update status
            this.updateStatus('Ready', 'idle');

        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage(`Error: ${error.message}`, 'error');
            this.updateStatus('Error occurred', 'error');
        } finally {
            // Re-enable input
            this.setInputState(true);
            this.elements.messageInput.focus();
        }
    }

    handleEvent(event) {
        if (!this.showStatus) return;

        switch (event.type) {
            case 'thinking':
                this.updateStatus('🤔 Agent is thinking...', 'thinking');
                break;

            case 'tool_use':
                const toolName = event.tool_name || 'unknown';
                this.updateStatus(`🔧 Using tool: ${toolName}`, 'tool-use');
                break;

            case 'agent_message':
                this.updateStatus('✍️ Generating response...', 'responding');
                break;

            case 'error':
                this.updateStatus(`❌ Error: ${event.message}`, 'error');
                break;

            default:
                console.log('Unknown event:', event);
        }
    }

    updateStatus(text, statusClass) {
        const statusContent = this.elements.statusContent;
        const statusElement = document.createElement('p');
        statusElement.className = `status-${statusClass}`;
        statusElement.textContent = text;

        // Clear previous status and add new one
        statusContent.innerHTML = '';
        statusContent.appendChild(statusElement);
    }

    addMessage(content, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        // Render markdown for assistant messages, plain text for others
        if (role === 'assistant' && typeof marked !== 'undefined') {
            messageContent.innerHTML = marked.parse(content);
        } else {
            // For user/system/error messages, preserve newlines with plain text
            const messageParagraph = document.createElement('p');
            messageParagraph.style.whiteSpace = 'pre-wrap';
            messageParagraph.textContent = content;
            messageContent.appendChild(messageParagraph);
        }

        messageDiv.appendChild(messageContent);

        this.elements.chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    }

    async clearHistory() {
        if (!confirm('Are you sure you want to clear your chat history?')) {
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/session/${this.userId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Clear messages except system message
            const systemMessage = this.elements.chatMessages.querySelector('.message.system');
            this.elements.chatMessages.innerHTML = '';
            if (systemMessage) {
                this.elements.chatMessages.appendChild(systemMessage);
            }

            this.updateStatus('History cleared', 'idle');

        } catch (error) {
            console.error('Error clearing history:', error);
            alert('Failed to clear history. Please try again.');
        }
    }

    setInputState(enabled) {
        this.elements.messageInput.disabled = !enabled;
        this.elements.sendButton.disabled = !enabled;
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
