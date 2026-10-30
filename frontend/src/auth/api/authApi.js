
import { http } from "../../shared/api/http";

export const authApi = {
    async register(data) {
        const response = await http.post("/users", data);
        return response.data;
    },

    async verifyEmail(data) {
        const response = await http.post(
            "/auth/verify-email",
            data
        );
        return response.data;
    },

    async resendCode(email) {
        const response = await http.post(
            "/auth/resend-code",
            { email }
        );
        return response.data;
    },

    async login(data) {
        const response = await http.post(
            "/auth/login",
            data
        );
        return response.data;
    },

    async getMe() {
        const response = await http.get("/users/me");
        return response.data;
    },
};
