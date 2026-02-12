/**
 * Avatares de perfil: animales y monstruos amigables (emojis)
 */
export const AVATAR_OPTIONS = ['🐱', '🐶', '🐰', '🦊', '🐻', '🐼', '🐸', '🦉', '🐙', '🦋', '👾', '🐢', '🐿️', '🦔'];
export const DEFAULT_AVATAR = '🐱';

const STORAGE_KEY = 'tfg_profile_avatar';

export function getStoredAvatar(userId) {
    try {
        const key = userId ? `${STORAGE_KEY}_${userId}` : STORAGE_KEY;
        return localStorage.getItem(key) || DEFAULT_AVATAR;
    } catch {
        return DEFAULT_AVATAR;
    }
}

export function setStoredAvatar(userId, emoji) {
    try {
        const key = userId ? `${STORAGE_KEY}_${userId}` : STORAGE_KEY;
        if (AVATAR_OPTIONS.includes(emoji)) {
            localStorage.setItem(key, emoji);
        }
    } catch {}
}
