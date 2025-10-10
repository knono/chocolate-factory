/**
 * Chatbot BI - JavaScript Logic
 * Sprint 11 - Chatbot Conversacional
 */

// Global state
let chatbotState = {
    isLoading: false,
    totalQuestions: 0,
    totalCost: 0,
    sessionStartTime: Date.now()
};

/**
 * Enviar mensaje del chatbot
 */
async function sendChatbotMessage() {
    const input = document.getElementById('chatbotInput');
    const question = input.value.trim();

    if (!question || chatbotState.isLoading) {
        return;
    }

    // Clear input
    input.value = '';

    // Add user message to UI
    addChatMessage(question, 'user');

    // Show loading state
    setChatbotLoading(true);

    // Add typing indicator
    const typingId = addTypingIndicator();

    try {
        // Call chatbot API
        const response = await fetch('/chat/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                user_id: 'dashboard_user'
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Remove typing indicator
        removeTypingIndicator(typingId);

        // Add assistant response
        addChatMessage(data.answer, 'assistant', {
            tokens: data.tokens,
            latency_ms: data.latency_ms,
            cost_usd: data.cost_usd
        });

        // Update stats
        updateChatbotStats(data);

    } catch (error) {
        console.error('Chatbot error:', error);
        removeTypingIndicator(typingId);
        addChatMessage(
            `⚠️ Error: ${error.message}. Por favor, inténtalo de nuevo.`,
            'error'
        );
    } finally {
        setChatbotLoading(false);
    }
}

/**
 * Quick question button handler
 */
function askQuickQuestion(question) {
    const input = document.getElementById('chatbotInput');
    input.value = question;
    sendChatbotMessage();
}

/**
 * Add message to chat UI
 */
function addChatMessage(text, type, metadata = null) {
    const container = document.getElementById('chatMessagesContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;

    if (type === 'user') {
        messageDiv.innerHTML = `
            <div>
                <div class="message-bubble" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 1rem; border-radius: 12px 12px 0 12px; color: white; font-size: 0.95rem; line-height: 1.5; max-width: 70%; margin-left: auto;">
                    ${escapeHtml(text)}
                </div>
            </div>
        `;
        messageDiv.style.display = 'flex';
        messageDiv.style.justifyContent = 'flex-end';
    } else if (type === 'assistant') {
        const costBadge = metadata ?
            `<span class="chat-cost-badge">${metadata.latency_ms}ms · ${metadata.tokens.total} tokens · $${metadata.cost_usd.toFixed(6)}</span>`
            : '';

        messageDiv.innerHTML = `
            <div style="display: flex; gap: 1rem; align-items: flex-start;">
                <div style="font-size: 2rem; flex-shrink: 0;">🤖</div>
                <div style="flex: 1;">
                    <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
                        <div style="font-size: 0.95rem; line-height: 1.6; white-space: pre-wrap;">${formatAssistantMessage(text)}</div>
                        ${costBadge ? `<div style="margin-top: 0.5rem;">${costBadge}</div>` : ''}
                    </div>
                </div>
            </div>
        `;
    } else if (type === 'error') {
        messageDiv.innerHTML = `
            <div class="chat-error">
                ${escapeHtml(text)}
            </div>
        `;
    }

    container.appendChild(messageDiv);

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

/**
 * Add typing indicator
 */
function addTypingIndicator() {
    const container = document.getElementById('chatMessagesContainer');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-message assistant-message typing-indicator-container';
    typingDiv.id = `typing-${Date.now()}`;
    typingDiv.innerHTML = `
        <div style="display: flex; gap: 1rem; align-items: flex-start;">
            <div style="font-size: 2rem; flex-shrink: 0;">🤖</div>
            <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px;">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;
    return typingDiv.id;
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

/**
 * Set loading state
 */
function setChatbotLoading(loading) {
    chatbotState.isLoading = loading;
    const sendBtn = document.getElementById('chatbotSendBtn');
    const sendIcon = document.getElementById('chatbotSendIcon');
    const loadingIcon = document.getElementById('chatbotLoadingIcon');
    const input = document.getElementById('chatbotInput');

    if (loading) {
        sendBtn.disabled = true;
        sendIcon.style.display = 'none';
        loadingIcon.style.display = 'inline';
        input.disabled = true;
    } else {
        sendBtn.disabled = false;
        sendIcon.style.display = 'inline';
        loadingIcon.style.display = 'none';
        input.disabled = false;
        input.focus();
    }
}

/**
 * Update chatbot stats
 */
function updateChatbotStats(data) {
    chatbotState.totalQuestions++;
    chatbotState.totalCost += data.cost_usd;

    const statsElement = document.getElementById('chatbotStats');
    const avgCost = chatbotState.totalCost / chatbotState.totalQuestions;

    statsElement.innerHTML = `
        Preguntas: ${chatbotState.totalQuestions} ·
        Costo total: $${chatbotState.totalCost.toFixed(6)} ·
        Promedio: $${avgCost.toFixed(6)}/pregunta
    `;
}

/**
 * Format assistant message (convert markdown-like to HTML)
 */
function formatAssistantMessage(text) {
    // Escape HTML first
    let formatted = escapeHtml(text);

    // Convert **bold** to <strong>
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Convert *italic* to <em>
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Convert bullet points
    formatted = formatted.replace(/^- (.+)$/gm, '• $1');

    return formatted;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Initialize chatbot on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('🤖 Chatbot BI initialized (Sprint 11)');

    // Focus input
    const input = document.getElementById('chatbotInput');
    if (input) {
        input.focus();
    }
});
