
import { http } from "../../shared/api/http";

// ==========================================
// Transformer KPI
// ==========================================

export async function getTransformerKpi() {
    const response = await http.get("/transformer/kpi");
    return response.data;
}

// ==========================================
// Transformer 사용자별 영화 추천
// ==========================================

export async function getTransformerRecommendations(userId) {
    const response = await http.get(
        `/transformer/recommendations/${encodeURIComponent(userId)}`
    );

    return response.data;
}
