import { state } from './state.js';
import * as auth from './auth.js';
import * as search from './search.js';
import * as chat from './chat.js';
import { api } from './api.js';
import { showNotification, escapeHtml, showLoading } from './ui.js';
import { renderPublicationsByYear, renderCategoriesPie, renderProfessorRadar } from './charts.js';
import { startTour, shouldShowOnLogin, setShowOnLogin } from './tour.js';
import { AVATAR_OPTIONS, DEFAULT_AVATAR, getStoredAvatar, setStoredAvatar } from './avatars.js';

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
window.addToComparison = addToComparison;
window.removeFromComparison = removeFromComparison;
window.sendChatMessage = sendChatMessage;
window.clearChat = clearChat;
window.saveProfile = saveProfile;
window.clearHistory = clearHistory;
window.exportResults = exportResults;
window.toggleDarkMode = toggleDarkMode;
window.stopGenerating = stopGenerating;
window.setChatFeedback = setChatFeedback;
window.selectAvatar = selectAvatar;
window.startTour = (force) => startTour(force ?? true);

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
    updateHeaderAvatar();
    loadPage('home');
    if (shouldShowOnLogin()) {
        setTimeout(() => startTour(), 500);
    }
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
    const navIndices = { home: 0, search: 1, chat: 2, compare: 3, recommendations: 4 };
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
    const container = document.getElementById('authContainer');
    if (!container) return;

    // Modo overlay: al activar "register" desplazamos el panel azul
    if (tab === 'register') {
        container.classList.add('active');
    } else {
        container.classList.remove('active');
    }
}

function toggleProfileMenu() {
    document.getElementById('profileMenu').classList.toggle('show');
}

async function loadHome() {
    const grid = document.getElementById('statsGrid');
    const lists = document.getElementById('infoLists');
    showLoading(grid);

    try {
        const [stats, rankingData] = await Promise.all([
            api.stats(),
            api.search.ranking().catch(() => [])
        ]);
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

        // Dashboard unificado: gráficos + listas en una sola tarjeta
        const tiposData = stats.tipos_produccion || {};
        const categoriasData = stats.categorias_populares || {};
        const tiposEntries = Object.entries(tiposData).slice(0, 8);
        const categoriasEntries = Object.entries(categoriasData).slice(0, 8);

        lists.innerHTML = `
            <div class="dashboard-overview-card">
                <div class="dashboard-charts-row">
                    <div class="dashboard-chart-item">
                        <div class="chart-container" style="height:220px;"><canvas id="yearChart"></canvas></div>
                    </div>
                    <div class="dashboard-chart-item">
                        <div class="chart-container" style="height:220px;"><canvas id="categoriesChart"></canvas></div>
                    </div>
                </div>
                <div class="dashboard-lists-row">
                    <div class="dashboard-list-item">
                        <h4 class="dashboard-list-title">📊 Producción por tipo</h4>
                        <ul class="dashboard-list">
                            ${tiposEntries.length ? tiposEntries.map(([k, v]) =>
                                `<li><span>${k}</span><strong>${v}</strong></li>`
                            ).join('') : '<li class="empty">Sin datos</li>'}
                        </ul>
                    </div>
                    <div class="dashboard-list-item">
                        <h4 class="dashboard-list-title">🏷️ Categorías populares</h4>
                        <ul class="dashboard-list">
                            ${categoriasEntries.length ? categoriasEntries.map(([k, v]) =>
                                `<li><span>${k.length > 35 ? k.slice(0, 32) + '…' : k}</span><strong>${v}</strong></li>`
                            ).join('') : '<li class="empty">Sin datos</li>'}
                        </ul>
                    </div>
                </div>
                ${Array.isArray(rankingData) && rankingData.length > 0 ? `
                <div class="dashboard-ranking-row">
                    <h4 class="dashboard-list-title">📈 Ranking de disponibilidad</h4>
                    <p class="dashboard-ranking-hint">Estimación según publicaciones recientes. Alta = mayor disponibilidad estimada.</p>
                    <div class="ranking-list">
                        ${rankingData.slice(0, 10).map((p, i) => `
                            <div class="ranking-item availability-${(p.availability_label || '').toLowerCase()}">
                                <span class="ranking-pos">${i + 1}</span>
                                <span class="ranking-name">${escapeHtml(p.profesor)}</span>
                                <span class="ranking-badge">${p.availability_label || 'N/A'}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
                <div class="dashboard-actions">
                    <button class="btn-primary" onclick="loadPage('recommendations')">💡 Ver Recomendaciones</button>
                </div>
            </div>
        `;

        // Render charts after DOM update
        setTimeout(() => {
            renderPublicationsByYear('yearChart', stats);
            renderCategoriesPie('categoriesChart', stats);
        }, 100);

    } catch (error) {
        grid.innerHTML = '<p class="error">Error cargando estadísticas</p>';
        lists.innerHTML = '';
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
                    <button class="btn-primary" onclick="viewProfessorDetail('${profile.profesor}')">👤 Ver Profesor</button>
                    <button class="btn-secondary" onclick="addToComparison('${profile.profesor}')">📊 Comparar</button>
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
    const email = search.getProfessorEmail(name);
    const emailHtml = email
        ? `<p class="professor-email">📧 <a href="mailto:${email}?subject=Consulta TFG">${email}</a></p>`
        : '';

    content.innerHTML = `
        <h2 style="color: var(--urjc-granate);">${profile.profesor}</h2>
        <div class="professor-stats">
            <div class="stat-item"><div class="stat-item-value">${stats.total_trabajos}</div>Trabajos</div>
            <div class="stat-item"><div class="stat-item-value">${stats.años_activo.length}</div>Años</div>
            <div class="stat-item"><div class="stat-item-value">${stats.categorias.length}</div>Categorías</div>
        </div>
        ${emailHtml}
        <div style="margin-top: 1.5rem;">
            <h3>📚 Trabajos Recientes</h3>
            ${stats.trabajos_recientes.slice(0, 5).map(w => `
                <div style="padding: 0.5rem; border-bottom: 1px solid #eee;">
                    <strong>${escapeHtml(w.titulo)}</strong> (${w.fecha})
                </div>
            `).join('')}
        </div>
    `;
    modal.classList.add('show');
}

function closeProfessorModal() {
    document.getElementById('professorModal').classList.remove('show');
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
        el.innerHTML = state.chatHistory.map((m, idx) => {
            const isLastAssistant = m.type === 'assistant' && idx === state.chatHistory.length - 1;
            const showFeedback = isLastAssistant && m.feedback === undefined && m.content;
            return `
                <div class="chat-msg-wrapper" data-msg-idx="${idx}">
                    <div class="chat-message ${m.type}">${escapeHtml(m.content)}</div>
                    ${showFeedback ? `
                        <div class="chat-feedback">
                            <span class="chat-feedback-label">¿Te fue útil esta recomendación?</span>
                            <div class="chat-feedback-btns">
                                <button class="chat-feedback-btn yes" onclick="setChatFeedback(${idx}, true)">👍 Sí</button>
                                <button class="chat-feedback-btn no" onclick="setChatFeedback(${idx}, false)">👎 No</button>
                                <button class="chat-feedback-btn skip" onclick="setChatFeedback(${idx}, null)">Prefiero no responder</button>
                            </div>
                        </div>
                    ` : (isLastAssistant && m.feedback !== undefined ? `
                        <div class="chat-feedback-done">${m.feedback === true ? '✓ Gracias por tu feedback' : m.feedback === false ? '✓ Entendido, adaptaré mis recomendaciones' : ''}</div>
                    ` : '')}
                </div>
            `;
        }).join('');
    }
    el.scrollTop = el.scrollHeight;
}

function setChatFeedback(msgIdx, value) {
    if (state.chatHistory[msgIdx] && state.chatHistory[msgIdx].type === 'assistant') {
        state.chatHistory[msgIdx].feedback = value;
        loadChatUI();
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    // Evitar que se lancen varias peticiones de chat en paralelo
    if (state.isChatStreaming) {
        showNotification('⚠️ Espera a que termine la respuesta actual o pulsa "Stop"', 'info');
        return;
    }

    state.chatHistory.push({ type: 'user', content: msg });
    loadChatUI();
    input.value = '';

    const container = document.getElementById('chatContainer');
    // Creamos un mensaje del asistente que iremos rellenando progresivamente
    const assistantMsgEl = document.createElement('div');
    assistantMsgEl.className = 'chat-message assistant';
    assistantMsgEl.textContent = '...';
    container.appendChild(assistantMsgEl);
    container.scrollTop = container.scrollHeight;

    // Actualizamos estado de botones (enviar / stop)
    const sendBtn = document.getElementById('chatSendBtn');
    const stopBtn = document.getElementById('stopGeneratingBtn');
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.textContent = 'Generando...';
    }
    if (stopBtn) {
        stopBtn.style.display = 'inline-flex';
    }

    let accumulated = '';

    const lastAssistantFeedback = (() => {
        for (let i = state.chatHistory.length - 2; i >= 0; i--) {
            if (state.chatHistory[i].type === 'assistant') {
                return state.chatHistory[i].feedback;
            }
        }
        return undefined;
    })();

    await chat.startChatStreaming(msg, {
        lastFeedbackPositive: lastAssistantFeedback === true ? true : lastAssistantFeedback === false ? false : undefined,
        onChunk: (_chunk, fullText) => {
            accumulated = fullText;
            assistantMsgEl.textContent = fullText;
            container.scrollTop = container.scrollHeight;
        },
        onComplete: (fullText, { aborted }) => {
            if (fullText) {
                state.chatHistory.push({ type: 'assistant', content: fullText });
            }
            if (aborted && fullText) {
                assistantMsgEl.textContent = fullText + '\n\n[Respuesta interrumpida por el usuario]';
            }
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.textContent = 'Enviar';
            }
            if (stopBtn) {
                stopBtn.style.display = 'none';
            }
            loadChatUI();
        }
    });
}

function clearChat() {
    state.chatHistory = [];
    loadChatUI();
}

function stopGenerating() {
    if (!state.isChatStreaming) return;
    chat.stopChatStreaming();
}

// PROFILE
function renderProfileAvatar(avatarEl, emoji) {
    if (!avatarEl) return;
    avatarEl.textContent = emoji || DEFAULT_AVATAR;
    avatarEl.className = 'avatar avatar-emoji';
}

function renderAvatarOptions(containerEl, selectedEmoji, userId) {
    if (!containerEl) return;
    containerEl.innerHTML = AVATAR_OPTIONS.map(emoji => `
        <button type="button" class="avatar-option ${emoji === selectedEmoji ? 'selected' : ''}" 
                data-avatar="${emoji}" 
                onclick="selectAvatar('${emoji}')"
                aria-label="Seleccionar ${emoji}"
                title="Seleccionar avatar">
            ${emoji}
        </button>
    `).join('');
}

function selectAvatar(emoji) {
    if (!state.currentUser) return;
    setStoredAvatar(state.currentUser.id, emoji);
    const avatarEl = document.getElementById('profileAvatar');
    const options = document.querySelectorAll('.avatar-option');
    renderProfileAvatar(avatarEl, emoji);
    options.forEach(btn => {
        btn.classList.toggle('selected', btn.dataset.avatar === emoji);
    });
    updateHeaderAvatar();
}

function updateHeaderAvatar() {
    if (!state.currentUser) return;
    const avatar = getStoredAvatar(state.currentUser.id);
    const span = document.getElementById('headerAvatar');
    const usernameSpan = document.getElementById('usernameDisplay');
    if (span) span.textContent = avatar;
    if (usernameSpan) usernameSpan.textContent = state.currentUser.username;
}

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

        const avatar = getStoredAvatar(state.currentUser.id);
        renderProfileAvatar(document.getElementById('profileAvatar'), avatar);
        renderAvatarOptions(document.getElementById('avatarOptions'), avatar, state.currentUser.id);

        const showTutorialCb = document.getElementById('profileShowTutorialOnLogin');
        if (showTutorialCb) {
            showTutorialCb.checked = shouldShowOnLogin();
            showTutorialCb.onchange = () => setShowOnLogin(showTutorialCb.checked);
        }

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
