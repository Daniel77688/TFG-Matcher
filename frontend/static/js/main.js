import { state } from './state.js';
import * as auth from './auth.js';
import * as search from './search.js';
import * as chat from './chat.js';
import { api } from './api.js';
import { showNotification, escapeHtml, showLoading } from './ui.js';
import { renderPublicationsByYear, renderCategoriesPie, renderProfessorRadar } from './charts.js';

// ========== EXPOSE TO WINDOW (for legacy HTML onclick) ==========
window.loadPage = loadPage;
window.login = login;
window.register = register;
window.logout = auth.logout;
window.toggleProfileMenu = toggleProfileMenu;
window.switchTab = switchTab;
window.switchSearchTab = switchSearchTab;
window.searchByTheme = searchByTheme;
window.searchByProfessor = searchByProfessor;
window.viewProfessorDetail = viewProfessorDetail;
window.closeProfessorModal = closeProfessorModal;
window.contactProfessor = contactProfessor;
window.addToComparison = addToComparison;
window.removeFromComparison = removeFromComparison;
window.sendChatMessage = sendChatMessage;
window.clearChat = clearChat;
window.saveProfile = saveProfile;
window.clearHistory = clearHistory;
window.exportResults = exportResults;
window.toggleDarkMode = toggleDarkMode;

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    const isAuthenticated = await auth.checkAuth();
    loadProductionTypes();

    if (isAuthenticated) {
        showApp();
    } else {
        showAuth();
    }

    // Global click listener for dropdown
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('profileMenu');
        const btn = document.getElementById('profileBtn');
        if (dropdown && !dropdown.contains(e.target) && !btn.contains(e.target)) {
            dropdown.classList.remove('show');
        }
    });

    // Chat enter key
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendChatMessage();
        });
    }
});

// ========== DARK MODE ==========
function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
    }
    updateThemeIcon();
}

function toggleDarkMode() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcon();
}

function updateThemeIcon() {
    const btn = document.getElementById('themeToggle');
    if (btn) {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        btn.textContent = isDark ? '☀️' : '🌙';
    }
}

function showAuth() {
    document.getElementById('authPage').style.display = 'block';
    document.querySelectorAll('.page:not(#authPage)').forEach(p => p.style.display = 'none');
    document.querySelector('.header').style.display = 'none';
}

function showApp() {
    document.getElementById('authPage').style.display = 'none';
    document.querySelector('.header').style.display = 'block';
    document.getElementById('usernameDisplay').textContent = state.currentUser.username;
    loadPage('home');
}

function loadPage(page) {
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

    const menu = document.getElementById('profileMenu');
    if (menu) menu.classList.remove('show');

    const pageId = `${page}Page`;
    const pageElement = document.getElementById(pageId);
    if (pageElement) {
        pageElement.style.display = 'block';
    }

    // Nav-btn highlighting
    const navIndices = { home: 0, search: 1, chat: 2, compare: 3 };
    if (page in navIndices) {
        const btn = document.querySelectorAll('.nav-btn')[navIndices[page]];
        if (btn) btn.classList.add('active');
    }

    // Specific page loading logic
    switch (page) {
        case 'home': loadHome(); break;
        case 'search': switchSearchTab('theme'); break;
        case 'chat': loadChatUI(); break;
        case 'compare': loadCompare(); break;
        case 'recommendations': loadRecommendations(); break;
        case 'profile': loadProfile(); break;
        case 'history': loadHistoryListFull(); break;
    }
}

// ========== PAGE SPECIFIC HANDLERS ==========

async function login() {
    const user = document.getElementById('loginUsername').value;
    const pass = document.getElementById('loginPassword').value;
    const success = await auth.login(user, pass);
    if (success) showApp();
}

async function register() {
    const user = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const pass = document.getElementById('regPassword').value;
    const pass2 = document.getElementById('regPassword2').value;

    if (pass !== pass2) {
        showNotification('❌ Las contraseñas no coinciden', 'error');
        return;
    }

    const success = await auth.register(user, email, pass);
    if (success) switchTab('login');
}

function switchTab(tab) {
    document.getElementById('loginForm').style.display = tab === 'login' ? 'block' : 'none';
    document.getElementById('registerForm').style.display = tab === 'register' ? 'block' : 'none';
    document.querySelectorAll('.tab-btn').forEach((btn, idx) => {
        btn.classList.toggle('active', (tab === 'login' && idx === 0) || (tab === 'register' && idx === 1));
    });
}

function toggleProfileMenu() {
    document.getElementById('profileMenu').classList.toggle('show');
}

async function loadHome() {
    const grid = document.getElementById('statsGrid');
    const lists = document.getElementById('infoLists');
    showLoading(grid);

    try {
        const stats = await api.stats();
        grid.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${stats.total_documents || 0}</div>
                <div class="stat-label">📄 Documentos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.total_profesores || 0}</div>
                <div class="stat-label">👥 Profesores</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.años_cubiertos?.length || 0}</div>
                <div class="stat-label">📅 Años</div>
            </div>
        `;

        let html = '';
        if (stats.tipos_produccion) {
            html += renderInfoList('📊 Producción por Tipo', stats.tipos_produccion);
        }
        if (stats.categorias_populares) {
            html += renderInfoList('🏷️ Categorías Populares', stats.categorias_populares);
        }
        lists.innerHTML = html;

        // Charts
        const chartsHtml = `
            <div class="charts-grid">
                <div class="chart-card"><div class="chart-container" style="height:250px;"><canvas id="yearChart"></canvas></div></div>
                <div class="chart-card"><div class="chart-container" style="height:250px;"><canvas id="categoriesChart"></canvas></div></div>
            </div>
        `;
        lists.insertAdjacentHTML('beforeend', chartsHtml);

        // Render charts after DOM update
        setTimeout(() => {
            renderPublicationsByYear('yearChart', stats);
            renderCategoriesPie('categoriesChart', stats);
        }, 100);

        // Recommendations shortcuts
        const div = document.createElement('div');
        div.style.textAlign = 'center';
        div.style.marginTop = '2rem';
        div.innerHTML = `<button class="btn-primary" onclick="loadPage('recommendations')">💡 Ver Recomendaciones</button>`;
        lists.appendChild(div);

    } catch (error) {
        grid.innerHTML = '<p class="error">Error cargando estadísticas</p>';
    }
}

function renderInfoList(title, data) {
    return `
        <div class="info-list">
            <h3>${title}</h3>
            <ul>
                ${Object.entries(data).slice(0, 10).map(([key, val]) => `
                    <li><span class="item-name">${key}</span><span class="item-count">${val}</span></li>
                `).join('')}
            </ul>
        </div>
    `;
}

// BÚSQUEDA
function switchSearchTab(tab) {
    document.getElementById('themeSearch').style.display = tab === 'theme' ? 'block' : 'none';
    document.getElementById('professorSearch').style.display = tab === 'professor' ? 'block' : 'none';
    document.querySelectorAll('#searchPage .tab-btn').forEach((btn, idx) => {
        btn.classList.toggle('active', (tab === 'theme' && idx === 0) || (tab === 'professor' && idx === 1));
    });
}

async function loadProductionTypes() {
    try {
        const types = await api.productionTypes();
        const select = document.getElementById('typeFilter');
        if (select) {
            types.forEach(t => {
                const opt = document.createElement('option');
                opt.value = opt.textContent = t;
                select.appendChild(opt);
            });
        }
    } catch (e) { }
}

async function searchByTheme() {
    const params = {
        query: document.getElementById('themeQuery').value,
        limit: parseInt(document.getElementById('themeLimit').value),
        filters: {}
    };

    if (!params.query) return showNotification('⚠️ Ingresa un tema', 'error');

    const type = document.getElementById('typeFilter').value;
    const q = document.getElementById('quartileFilter').value;
    const ifMin = parseFloat(document.getElementById('minIF').value);

    if (type) params.filters.tipo_produccion = type;
    if (q) params.filters.q_sjr = q;
    if (ifMin > 0) params.filters.min_if_sjr = ifMin;

    const results = await search.searchByTheme(params);
    if (results) displayResults(results, 'themeResults');
}

async function searchByProfessor() {
    const name = document.getElementById('professorName').value;
    if (!name) return showNotification('⚠️ Ingresa un nombre', 'error');

    const profile = await search.searchByProfessor(name);
    if (profile) {
        const container = document.getElementById('professorResults');
        container.innerHTML = `
            <div class="professor-card">
                <div class="professor-name">${profile.profesor}</div>
                <div class="professor-stats">
                    <div class="stat-item"><div class="stat-item-value">${profile.estadisticas.total_trabajos}</div>Trabajos</div>
                    <div class="stat-item"><div class="stat-item-value">${profile.estadisticas.años_activo.length}</div>Años</div>
                </div>
                <div class="result-actions">
                    <button class="btn-primary" onclick="viewProfessorDetail('${profile.profesor}')">📋 Perfil</button>
                    <button class="btn-secondary" onclick="addToComparison('${profile.profesor}')">📊 Comparar</button>
                    <button class="btn-link" onclick="contactProfessor('${profile.profesor}')">📧 Email</button>
                </div>
            </div>
        `;

        // Also show some works
        const works = await api.search.general({ query: '', limit: 10, filters: { profesor: profile.profesor } });
        displayResults(works, null, container);
    }
}

function displayResults(results, containerId, target = null) {
    const el = target || document.getElementById(containerId);
    if (!results.results?.length) {
        el.innerHTML = '<p class="loading">No hay resultados</p>';
        return;
    }

    let html = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h3>Resultados (${results.total_results})</h3>
            <button class="btn-secondary" onclick="exportResults('${results.query || ''}', ${results.total_results})">📥 CSV</button>
        </div>
    `;

    results.results.forEach(res => {
        html += `
            <div class="result-card">
                <div class="result-title">${escapeHtml(res.titulo)}</div>
                <div class="result-meta">
                    <span>👨‍🏫 ${escapeHtml(res.profesor)}</span> | 📅 ${res.fecha} | 🏷️ ${res.tipo_produccion}
                </div>
                <div class="result-actions">
                    <button class="btn-link" onclick="viewProfessorDetail('${escapeHtml(res.profesor)}')">👤 Ver Profesor</button>
                    <button class="btn-secondary" onclick="addToComparison('${escapeHtml(res.profesor)}')">📊 Comparar</button>
                </div>
            </div>
        `;
    });
    el.innerHTML = html;
}

// PROFESSOR DETAIL & COMPARISON
async function viewProfessorDetail(name) {
    const profile = await search.searchByProfessor(name);
    if (!profile) return;

    const modal = document.getElementById('professorModal');
    const content = document.getElementById('professorModalContent');
    const stats = profile.estadisticas;

    content.innerHTML = `
        <h2 style="color: #8B1538;">${profile.profesor}</h2>
        <div class="professor-stats">
            <div class="stat-item"><div class="stat-item-value">${stats.total_trabajos}</div>Trabajos</div>
            <div class="stat-item"><div class="stat-item-value">${stats.años_activo.length}</div>Años</div>
            <div class="stat-item"><div class="stat-item-value">${stats.categorias.length}</div>Categorías</div>
        </div>
        <div style="margin-top: 1.5rem;">
            <h3>📚 Trabajos Recientes</h3>
            ${stats.trabajos_recientes.slice(0, 5).map(w => `
                <div style="padding: 0.5rem; border-bottom: 1px solid #eee;">
                    <strong>${w.titulo}</strong> (${w.fecha})
                </div>
            `).join('')}
        </div>
        <div style="margin-top: 1rem;">
            <button class="btn-primary" onclick="contactProfessor('${profile.profesor}')">📧 Contactar</button>
        </div>
    `;
    modal.classList.add('show');
}

function closeProfessorModal() {
    document.getElementById('professorModal').classList.remove('show');
}

function contactProfessor(name) {
    const email = search.getProfessorEmail(name);
    if (email) window.location.href = `mailto:${email}?subject=Consulta TFG`;
}

function addToComparison(name) {
    if (state.comparisonList.length >= 2) return showNotification('⚠️ Máximo 2', 'error');
    if (!state.comparisonList.includes(name)) {
        state.comparisonList.push(name);
        showNotification('✅ Agregado', 'success');
    }
}

function removeFromComparison(name) {
    state.comparisonList = state.comparisonList.filter(p => p !== name);
    loadCompare();
}

async function loadCompare() {
    const el = document.getElementById('compareContainer');
    if (!state.comparisonList.length) {
        el.innerHTML = '<p class="loading">Agrega profesores para comparar</p>';
        return;
    }

    let html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">';
    const profiles = [];

    for (const name of state.comparisonList) {
        const p = await api.search.professor(name);
        profiles.push(p);
        html += `
            <div class="professor-card">
                <h3>${p.profesor}</h3>
                <p>${p.estadisticas.total_trabajos} trabajos</p>
                <button class="btn-secondary" onclick="removeFromComparison('${name}')">Eliminar</button>
            </div>
        `;
    }
    html += '</div>';

    if (profiles.length === 2) {
        html += `
            <table class="compare-table" style="width: 100%; margin-top: 2rem;">
                <tr><th>Métrica</th><th>${profiles[0].profesor}</th><th>${profiles[1].profesor}</th></tr>
                <tr><td>Trabajos</td><td>${profiles[0].estadisticas.total_trabajos}</td><td>${profiles[1].estadisticas.total_trabajos}</td></tr>
                <tr><td>Años</td><td>${profiles[0].estadisticas.años_activo.length}</td><td>${profiles[1].estadisticas.años_activo.length}</td></tr>
            </table>
        `;
    }
    el.innerHTML = html;
}

// CHAT UI
function loadChatUI() {
    const el = document.getElementById('chatContainer');
    if (!state.chatHistory.length) {
        el.innerHTML = '<div class="chat-message assistant">¡Hola! ¿En qué puedo ayudarte con tu TFG?</div>';
    } else {
        el.innerHTML = state.chatHistory.map(m => `
            <div class="chat-message ${m.type}">${escapeHtml(m.content)}</div>
        `).join('');
    }
    el.scrollTop = el.scrollHeight;
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    state.chatHistory.push({ type: 'user', content: msg });
    loadChatUI();
    input.value = '';

    const container = document.getElementById('chatContainer');
    const thinking = document.createElement('div');
    thinking.className = 'chat-message assistant';
    thinking.textContent = '🤔 Pensando...';
    container.appendChild(thinking);
    container.scrollTop = container.scrollHeight;

    const response = await chat.sendChatMessage(msg);
    thinking.remove();

    if (response) {
        state.chatHistory.push({ type: 'assistant', content: response });
        loadChatUI();
    }
}

function clearChat() {
    state.chatHistory = [];
    loadChatUI();
}

// PROFILE
async function loadProfile() {
    try {
        const p = await api.profile.get(state.currentUser.id);
        document.getElementById('profileUsername').textContent = p.username;
        document.getElementById('profileEmail').textContent = p.email;
        document.getElementById('profileFullName').value = p.full_name || '';
        document.getElementById('profileDegree').value = p.degree || '';
        document.getElementById('profileYear').value = p.year || 1;
        document.getElementById('profileInterests').value = p.interests || '';
        document.getElementById('profileSkills').value = p.skills || '';
        document.getElementById('profileAreas').value = p.preferred_areas || '';

        const history = await api.history.get(state.currentUser.id);
        document.getElementById('historyList').innerHTML = history.map(h => `
            <div class="history-item"><strong>${h.query}</strong> <small>(${h.timestamp})</small></div>
        `).join('');
    } catch (e) { }
}

async function saveProfile() {
    const data = {
        full_name: document.getElementById('profileFullName').value,
        degree: document.getElementById('profileDegree').value,
        year: parseInt(document.getElementById('profileYear').value),
        interests: document.getElementById('profileInterests').value,
        skills: document.getElementById('profileSkills').value,
        preferred_areas: document.getElementById('profileAreas').value
    };

    try {
        await api.profile.update(state.currentUser.id, data);
        showNotification('✅ Guardado', 'success');
    } catch (e) {
        showNotification('❌ Error al guardar', 'error');
    }
}

async function loadHistoryListFull() {
    const history = await api.history.get(state.currentUser.id, 20);
    document.getElementById('historyListFull').innerHTML = history.map(h => `
        <div class="history-item"><strong>${h.query}</strong> <span>(${h.timestamp})</span></div>
    `).join('');
}

async function clearHistory() {
    if (!confirm('¿Eliminar historial?')) return;
    await api.history.clear(state.currentUser.id);
    showNotification('✅ Eliminado', 'success');
    loadPage('profile');
}

// RECOMMENDATIONS
async function loadRecommendations() {
    const el = document.getElementById('recommendationsContainer');
    showLoading(el, 'Analizando perfil...');

    try {
        const results = await api.search.recommendations(state.currentUser.id);
        if (results.message) {
            el.innerHTML = `<p style="text-align:center;">${results.message}</p>`;
            return;
        }
        displayResults(results, 'recommendationsContainer');
    } catch (e) {
        el.innerHTML = '<p class="error">Error cargando recomendaciones</p>';
    }
}

// UTILS
async function exportResults(query, limit) {
    // Legacy support or simplified for now
    showNotification('ℹ️ Iniciando descarga...', 'info');
    // Implement blob download if needed or call legacy endpoint
    try {
        const response = await fetch(`${state.API_BASE}/export/csv`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, limit })
        });
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `resultados.csv`;
        a.click();
    } catch (e) {
        showNotification('❌ Error exportando', 'error');
    }
}
