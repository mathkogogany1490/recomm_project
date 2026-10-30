
import axios from "axios";

const TOKEN_KEY = "recommendation_access_token";

export const tokenStore = {
    get() {
        return localStorage.getItem(TOKEN_KEY);
    },

    set(token) {
        localStorage.setItem(TOKEN_KEY, token);
        window.dispatchEvent(new Event("auth-token-changed"));
    },

    clear() {
        localStorage.removeItem(TOKEN_KEY);
        window.dispatchEvent(new Event("auth-token-changed"));
    },
};

export const http = axios.create({
    baseURL: "/api/",
    timeout: 15000,
});

http.interceptors.request.use((config) => {
    const token = tokenStore.get();

    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
});

http.interceptors.response.use(
    (response) => response,
    (error) => {
        if (
            error.response?.status === 401 &&
            tokenStore.get()
        ) {
            tokenStore.clear();
        }

        return Promise.reject(error);
    }
);

export function getApiError(error) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (Array.isArray(detail)) {
        return detail
            .map((item) => item.msg || "입력값 오류")
            .join(", ");
    }

    if (error.response?.status) {
        return `서버 오류 (${error.response.status})`;
    }

    return error.message || "서버에 연결할 수 없습니다.";
}
