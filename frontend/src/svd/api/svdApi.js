
import { http } from "../../shared/api/http";

export const svdApi = {
    async getKpi() {
        const response = await http.get(
            "/svd/kpi"
        );

        return response.data;
    },

    async getRecommendations(userId) {
        const response = await http.get(
            "/svd/recommendations",
            {
                params: {
                    user_id: userId,
                },
            }
        );

        return response.data;
    },
};
