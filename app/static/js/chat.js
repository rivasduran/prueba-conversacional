document.addEventListener('DOMContentLoaded', () => {
    // Elementos del DOM
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-btn');
    const resetButton = document.getElementById('reset-chat');
    
    // Simular mensaje de bienvenida automático
    setTimeout(() => {
        // Esto desencadenará el mensaje de bienvenida del bot
        sendMessage('');
    }, 500);
    
    // Evento para enviar mensaje
    sendButton.addEventListener('click', () => {
        const message = messageInput.value.trim();
        if (message) {
            // Mostrar mensaje del usuario
            appendMessage('user', message);
            messageInput.value = '';
            
            // Enviar mensaje al backend
            sendMessage(message);
        }
    });
    
    // Envío de mensaje con Enter
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendButton.click();
        }
    });
    
    // Evento para reiniciar chat
    resetButton.addEventListener('click', () => {
        resetChat();
    });
    
    // Función para añadir un mensaje al chat
    function appendMessage(sender, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const now = new Date();
        const timeString = now.getHours().toString().padStart(2, '0') + ':' + 
                          now.getMinutes().toString().padStart(2, '0');
        
        messageDiv.innerHTML = `
            <div class="message-content">
                ${content}
                <div class="message-time">${timeString}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll al último mensaje
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Función para mostrar indicador de escritura
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator bot-message message';
        typingDiv.id = 'typing-indicator';
        
        typingDiv.innerHTML = `
            <div class="message-content">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Función para ocultar indicador de escritura
    function hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Función para enviar mensaje al backend
    function sendMessage(message) {
        // Mostrar indicador de escritura
        showTypingIndicator();
        
        fetch('/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        })
        .then(response => response.json())
        .then(data => {
            // Ocultar indicador de escritura
            hideTypingIndicator();
            
            // Mostrar respuesta del bot
            appendMessage('bot', data.response);
        })
        .catch(error => {
            console.error('Error:', error);
            hideTypingIndicator();
            appendMessage('bot', 'Lo siento, ha ocurrido un error. Por favor, inténtalo de nuevo.');
        });
    }
    
    // Función para reiniciar chat
    function resetChat() {
        // Limpiar el chat
        chatMessages.innerHTML = '';
        
        // Enviar petición para reiniciar conversación
        fetch('/reset_conversation', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Mostrar mensaje de bienvenida
                setTimeout(() => {
                    sendMessage('');
                }, 500);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            appendMessage('bot', 'Lo siento, ha ocurrido un error al reiniciar el chat.');
        });
    }
});