export const state = {
    currentUser: null,
    chatHistory: [],
    comparisonList: [],
    API_BASE: '/api'
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
