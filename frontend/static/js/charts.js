/**
 * Charts — Visualización de datos con Chart.js
 */

const CHART_COLORS = {
    primary: 'rgba(106, 17, 53, 0.8)',
    primaryLight: 'rgba(106, 17, 53, 0.3)',
    palette: [
        'rgba(106, 17, 53, 0.8)',
        'rgba(54, 162, 235, 0.8)',
        'rgba(255, 206, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)',
        'rgba(255, 159, 64, 0.8)',
        'rgba(199, 199, 199, 0.8)',
        'rgba(83, 102, 120, 0.8)',
        'rgba(255, 99, 132, 0.8)',
        'rgba(46, 204, 113, 0.8)',
    ],
};

// Almacenar instancias de charts para destruirlas antes de recrear
const chartInstances = {};

function destroyChart(canvasId) {
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
        delete chartInstances[canvasId];
    }
}

/**
 * Gráfico de barras: publicaciones por año
 */
export function renderPublicationsByYear(canvasId, stats) {
    destroyChart(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas || !stats?.años_publicacion) return;

    const years = Object.keys(stats.años_publicacion).sort();
    const counts = years.map(y => stats.años_publicacion[y]);

    chartInstances[canvasId] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: years,
            datasets: [{
                label: 'Publicaciones',
                data: counts,
                backgroundColor: CHART_COLORS.primary,
                borderColor: CHART_COLORS.primary,
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: '📅 Publicaciones por Año',
                    font: { size: 14, weight: 'bold' },
                }
            },
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } },
            }
        }
    });
}

/**
 * Gráfico de tarta: categorías populares
 */
export function renderCategoriesPie(canvasId, stats) {
    destroyChart(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas || !stats?.categorias_populares) return;

    const entries = Object.entries(stats.categorias_populares).slice(0, 8);
    const labels = entries.map(([k]) => k.length > 25 ? k.slice(0, 22) + '...' : k);
    const data = entries.map(([, v]) => v);

    chartInstances[canvasId] = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data,
                backgroundColor: CHART_COLORS.palette.slice(0, entries.length),
                borderWidth: 2,
                borderColor: 'var(--urjc-white, #fff)',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '📊 Categorías Populares',
                    font: { size: 14, weight: 'bold' },
                },
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, font: { size: 11 } },
                }
            }
        }
    });
}

/**
 * Gráfico de radar: perfil completo de un profesor
 */
export function renderProfessorRadar(canvasId, professorData) {
    destroyChart(canvasId);
    const canvas = document.getElementById(canvasId);
    if (!canvas || !professorData?.estadisticas) return;

    const stats = professorData.estadisticas;
    const tipos = stats.tipos_produccion || {};
    const labels = Object.keys(tipos).map(k => k.length > 20 ? k.slice(0, 17) + '...' : k);
    const data = Object.values(tipos);

    if (labels.length < 3) return; // radar necesita mínimo 3 puntos

    chartInstances[canvasId] = new Chart(canvas, {
        type: 'radar',
        data: {
            labels,
            datasets: [{
                label: professorData.profesor,
                data,
                backgroundColor: CHART_COLORS.primaryLight,
                borderColor: CHART_COLORS.primary,
                borderWidth: 2,
                pointBackgroundColor: CHART_COLORS.primary,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `📈 Perfil de ${professorData.profesor}`,
                    font: { size: 14, weight: 'bold' },
                },
                legend: { display: false },
            },
            scales: {
                r: {
                    beginAtZero: true,
                    ticks: { precision: 0 },
                }
            }
        }
    });
}
