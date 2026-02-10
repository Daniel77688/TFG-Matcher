import { state } from './state.js';
import { api } from './api.js';
import { showNotification } from './ui.js';

export async function sendChatMessage(message) {
    if (!message || !state.currentUser) return null;

    // Prepare history
    const historyToSend = state.chatHistory.map(msg => ({
        type: msg.type,
        content: msg.content
    }));

    try {
        const data = await api.chat.send({
            message,
            user_id: state.currentUser.id,
            chat_history: historyToSend
        });

        // Save to background history
        api.history.add(state.currentUser.id, {
            query: message,
            search_type: 'agente_ia'
        }).catch(console.error);

        return data.response;
    } catch (error) {
        showNotification('❌ Error: ' + error.message, 'error');
        return null;
    }
}
