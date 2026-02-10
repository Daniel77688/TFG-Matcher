import { state, setCurrentUser } from './state.js';
import { api } from './api.js';
import { showNotification } from './ui.js';

export async function checkAuth() {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    if (token && userStr) {
        state.currentUser = JSON.parse(userStr);
        return true;
    }
    // Limpiar datos inconsistentes
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    return false;
}

export async function login(username, password) {
    if (!username || !password) {
        showNotification('⚠️ Completa todos los campos', 'error');
        return null;
    }

    try {
        const data = await api.auth.login({ username, password });
        if (data.success) {
            // Guardar JWT token y datos del usuario
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            setCurrentUser(data.user);
            return data.user;
        }
        return null;
    } catch (error) {
        showNotification('❌ Error: ' + error.message, 'error');
        return null;
    }
}

export async function register(username, email, password) {
    try {
        const data = await api.auth.register({ username, email, password });
        if (data.success) {
            showNotification('✅ Cuenta creada. Por favor inicia sesión.', 'success');
            return true;
        }
        return false;
    } catch (error) {
        showNotification('❌ Error: ' + error.message, 'error');
        return false;
    }
}

export function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    state.currentUser = null;
    state.chatHistory = [];
    state.comparisonList = [];
    window.location.reload();
}
