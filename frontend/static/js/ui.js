export function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideIn 0.3s;
        max-width: 400px;
        ${type === 'error' ? 'background: #FEE2E2; color: #991B1B; border-left: 4px solid #DC2626;' : ''}
        ${type === 'success' ? 'background: #D1FAE5; color: #065F46; border-left: 4px solid #10B981;' : ''}
        ${type === 'info' ? 'background: #DBEAFE; color: #1E40AF; border-left: 4px solid #3B82F6;' : ''}
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

export function showLoading(container, message = 'Cargando...') {
    container.innerHTML = `<p class="loading">${message}</p>`;
}
