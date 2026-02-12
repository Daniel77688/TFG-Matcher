import { state } from './state.js';
import { api } from './api.js';
import { showNotification } from './ui.js';

let currentController = null;

/**
 * Inicia una petición de chat en modo streaming contra /api/chat/stream.
 *
 * El backend envía texto plano progresivamente; aquí lo vamos leyendo por chunks
 * y delegamos el renderizado en los callbacks del caller.
 */
export async function startChatStreaming(message, { onChunk, onComplete, onError, lastFeedbackPositive } = {}) {
    if (!message || !state.currentUser) return;
    if (state.isChatStreaming) return;

    // Historial que se envía al backend (solo tipos y contenido)
    const historyToSend = state.chatHistory.map(msg => ({
        type: msg.type,
        content: msg.content
    }));

    // Guardamos también en el historial del backend (no bloqueante)
    api.history.add(state.currentUser.id, {
        query: message,
        search_type: 'agente_ia'
    }).catch(console.error);

    const controller = new AbortController();
    currentController = controller;
    state.isChatStreaming = true;

    let fullText = '';

    try {
        const payload = {
            message,
            user_id: state.currentUser.id,
            chat_history: historyToSend
        };
        if (lastFeedbackPositive !== undefined) {
            payload.last_feedback_positive = lastFeedbackPositive;
        }
        const response = await fetch(`${state.API_BASE}/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload),
            signal: controller.signal
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `Error ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            if (!chunk) continue;

            fullText += chunk;
            if (onChunk) onChunk(chunk, fullText);
        }

        if (onComplete) onComplete(fullText, { aborted: false });
    } catch (error) {
        if (error.name === 'AbortError') {
            if (onComplete) onComplete(fullText, { aborted: true });
        } else {
            console.error('Chat streaming error:', error);
            showNotification('❌ Error: ' + error.message, 'error');
            if (onError) onError(error);
        }
    } finally {
        state.isChatStreaming = false;
        currentController = null;
    }
}

/**
 * Detiene la generación actual (si existe) abortando la petición fetch.
 */
export function stopChatStreaming() {
    if (currentController) {
        currentController.abort();
    }
}
