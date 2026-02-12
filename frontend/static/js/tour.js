/**
 * Tour guiado con guía amigable — se muestra al iniciar sesión por defecto
 */
const TOUR_SHOW_ON_LOGIN_KEY = 'tfg_tutorial_show_on_login';
const TOUR_GUIDE_EMOJI = '🎓';

const TOUR_STEPS = [
    {
        title: '¡Hola! Soy tu guía',
        text: 'Te voy a enseñar por dónde moverte en TFG Scraper Pro. ¡Es muy sencillo!',
        target: null,
    },
    {
        title: '🏠 Aquí está Inicio',
        text: 'Aquí verás las estadísticas de la base de datos y el ranking de profesores.',
        target: '.nav-btn:nth-of-type(1)',
    },
    {
        title: '🔍 Y aquí la Búsqueda',
        text: 'Busca tutores por tema o por nombre. Los filtros te ayudan a afinar.',
        target: '.nav-btn:nth-of-type(2)',
    },
    {
        title: '🤖 El Asistente IA',
        text: 'Pregúntale lo que quieras sobre TFG. Conoce tu perfil y te da recomendaciones.',
        target: '.nav-btn:nth-of-type(3)',
    },
    {
        title: '📊 Comparar profesores',
        text: '¿Entre dos tutores? Añádelos desde la búsqueda y compáralos lado a lado.',
        target: '.nav-btn:nth-of-type(4)',
    },
    {
        title: '💡 Recomendaciones',
        text: 'Según tus intereses y habilidades te sugiere los mejores tutores. ¡Completa tu perfil!',
        target: '.nav-btn:nth-of-type(5)',
    },
];

let currentStep = 0;
let tourOverlay = null;

export function shouldShowOnLogin() {
    const v = localStorage.getItem(TOUR_SHOW_ON_LOGIN_KEY);
    if (v === null) return true; // Por defecto: sí
    return v === 'true';
}

export function setShowOnLogin(show) {
    localStorage.setItem(TOUR_SHOW_ON_LOGIN_KEY, String(show));
}

export function startTour(force = false) {
    currentStep = 0;
    createTourUI(force);
    showStep(0);
}

function createTourUI(force) {
    if (tourOverlay && tourOverlay.parentNode) {
        tourOverlay.parentNode.removeChild(tourOverlay);
        tourOverlay = null;
    }

    tourOverlay = document.createElement('div');
    tourOverlay.id = 'tourOverlay';
    tourOverlay.className = 'tour-overlay';
    tourOverlay.innerHTML = `
        <div class="tour-popup">
            <div class="tour-guide">
                <div class="tour-guide-avatar" aria-hidden="true">${TOUR_GUIDE_EMOJI}</div>
                <div class="tour-speech">
                    <h3 class="tour-title" id="tourTitle"></h3>
                    <p class="tour-text" id="tourText"></p>
                </div>
            </div>
            <div class="tour-footer">
                <label class="tour-checkbox">
                    <input type="checkbox" id="tourShowOnLogin" checked>
                    <span>Mostrar tutorial al iniciar sesión</span>
                </label>
            </div>
            <div class="tour-actions">
                <button class="btn-secondary tour-skip" id="tourSkipBtn">Saltar</button>
                <div class="tour-nav">
                    <span class="tour-progress" id="tourProgress"></span>
                    <button class="btn-primary tour-next" id="tourNextBtn">Siguiente</button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(tourOverlay);

    const cb = document.getElementById('tourShowOnLogin');
    if (cb) cb.checked = shouldShowOnLogin();

    document.getElementById('tourNextBtn').addEventListener('click', () => finishStep(false));
    document.getElementById('tourSkipBtn').addEventListener('click', () => finishStep(true));
}

function showStep(idx) {
    currentStep = idx;
    const step = TOUR_STEPS[idx];
    const isLast = idx === TOUR_STEPS.length - 1;

    const titleEl = document.getElementById('tourTitle');
    const textEl = document.getElementById('tourText');
    const progressEl = document.getElementById('tourProgress');
    const nextBtn = document.getElementById('tourNextBtn');

    if (titleEl) titleEl.textContent = step.title;
    if (textEl) textEl.textContent = step.text;
    if (progressEl) progressEl.textContent = `${idx + 1} / ${TOUR_STEPS.length}`;
    if (nextBtn) nextBtn.textContent = isLast ? '¡Listo!' : 'Siguiente';

    document.querySelectorAll('.tour-highlight').forEach(el => el.classList.remove('tour-highlight'));

    if (step.target) {
        const target = document.querySelector(step.target);
        if (target) {
            target.classList.add('tour-highlight');
            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
}

function finishStep(skipped) {
    const cb = document.getElementById('tourShowOnLogin');
    const showOnLogin = cb ? cb.checked : true;
    setShowOnLogin(showOnLogin);

    if (currentStep < TOUR_STEPS.length - 1 && !skipped) {
        showStep(currentStep + 1);
    } else {
        closeTour();
    }
}

export function closeTour() {
    document.querySelectorAll('.tour-highlight').forEach(el => el.classList.remove('tour-highlight'));
    if (tourOverlay && tourOverlay.parentNode) {
        tourOverlay.parentNode.removeChild(tourOverlay);
    }
    tourOverlay = null;
}
