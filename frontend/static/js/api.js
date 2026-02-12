import { state } from './state.js';

export async function request(endpoint, options = {}) {
    const url = `${state.API_BASE}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };

    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `Error ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

export const api = {
    auth: {
        login: (credentials) => request('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
        register: (details) => request('/auth/register', { method: 'POST', body: JSON.stringify(details) })
    },
    profile: {
        get: (userId) => request(`/profile/${userId}`),
        update: (userId, data) => request(`/profile/${userId}`, { method: 'PUT', body: JSON.stringify(data) })
    },
    search: {
        general: (params) => request('/search', { method: 'POST', body: JSON.stringify(params) }),
        professor: (name) => request(`/professor/${encodeURIComponent(name)}`),
        recommendations: (userId, limit = 15) => request(`/recommendations/${userId}?limit=${limit}`),
        ranking: () => request('/professors/ranking')
    },
    chat: {
        send: (payload) => request('/chat', { method: 'POST', body: JSON.stringify(payload) })
    },
    history: {
        get: (userId, limit = 10) => request(`/history/${userId}?limit=${limit}`),
        add: (userId, entry) => request(`/history/${userId}`, { method: 'POST', body: JSON.stringify(entry) }),
        clear: (userId) => request(`/history/${userId}`, { method: 'DELETE' })
    },
    stats: () => request('/stats'),
    productionTypes: () => request('/production-types')
};
