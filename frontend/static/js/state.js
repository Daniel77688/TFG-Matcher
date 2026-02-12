export const state = {
    currentUser: null,
    chatHistory: [],
    comparisonList: [],
    API_BASE: '/api',
    // Estado del chat en streaming
    isChatStreaming: false
};

export function setCurrentUser(user) {
    state.currentUser = user;
}

export function setChatHistory(history) {
    state.chatHistory = history;
}

export function setComparisonList(list) {
    state.comparisonList = list;
}
