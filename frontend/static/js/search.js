import { state } from './state.js';
import { api } from './api.js';
import { showNotification, escapeHtml } from './ui.js';

export async function searchByTheme(params) {
    try {
        showNotification('🔍 Buscando...', 'info');
        const results = await api.search.general(params);

        // Save to history in background
        if (state.currentUser) {
            api.history.add(state.currentUser.id, {
                query: params.query,
                search_type: 'keywords'
            }).catch(console.error);
        }

        return results;
    } catch (error) {
        showNotification('❌ Error en búsqueda: ' + error.message, 'error');
        return null;
    }
}

export async function searchByProfessor(name) {
    try {
        showNotification('🔍 Buscando profesor...', 'info');
        const profile = await api.search.professor(name);
        return profile;
    } catch (error) {
        if (error.message.includes('404')) {
            showNotification('❌ Profesor no encontrado. Verifica las tildes.', 'error');
        } else {
            showNotification('❌ Error: ' + error.message, 'error');
        }
        return null;
    }
}

export function getProfessorEmail(professorName) {
    if (!professorName) return '';
    const parts = professorName.toLowerCase().split(' ').filter(p => p.length > 0);
    if (parts.length >= 2) {
        const first = parts[0].normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        const second = parts[1].normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        return `${first}.${second}@urjc.es`;
    }
    return '';
}
