
import { useState } from "react";

import {
    useMfKpi,
    useMfRecommendations,
} from "../query/useMf";

import MfKpi from "../components/MfKpi";
import MfRecommendations from "../components/MfRecommendations";


export default function MfPage() {
    const [userId, setUserId] = useState("1");

    const kpi = useMfKpi();
    const recommendations = useMfRecommendations();

    function handleSearch(event) {
        event.preventDefault();

        const id = Number(userId);

        if (!Number.isSafeInteger(id) || id < 1) {
            return;
        }

        recommendations.search(id);
    }

    return (
        <div
            style={{
                maxWidth: 1100,
                margin: "40px auto",
                padding: 24,
                fontFamily: "Arial, sans-serif",
                color: "#0f172a",
            }}
        >
            <h1>MF 딥러닝 영화 추천</h1>

            <p style={{ color: "#64748b" }}>
                Matrix Factorization · Embedding 30차원
            </p>

            {kpi.loading && <p>KPI 불러오는 중...</p>}

            {kpi.error && (
                <p role="alert" style={{ color: "#dc2626" }}>
                    서버 오류: {kpi.error}
                </p>
            )}

            {kpi.data && (
                <>
                    <MfKpi data={kpi.data} />

                    <p style={{ color: "#64748b", fontSize: 14 }}>
                        고객 {kpi.data.user_count.toLocaleString()}명 ·
                        영화 {kpi.data.movie_count.toLocaleString()}편 ·
                        평점 {kpi.data.rating_count.toLocaleString()}건
                        · 검증 데이터 기준
                    </p>
                </>
            )}

            <form
                onSubmit={handleSearch}
                style={{
                    display: "flex",
                    gap: 12,
                    marginTop: 32,
                    marginBottom: 24,
                }}
            >
                <input
                    type="number"
                    min="1"
                    step="1"
                    value={userId}
                    onChange={(event) => setUserId(event.target.value)}
                    placeholder="고객 ID"
                    required
                    style={{
                        padding: 12,
                        border: "1px solid #cbd5e1",
                        borderRadius: 8,
                        width: 200,
                    }}
                />

                <button
                    type="submit"
                    disabled={recommendations.loading}
                    style={{
                        padding: "12px 24px",
                        background: "#2563eb",
                        color: "white",
                        border: 0,
                        borderRadius: 8,
                        cursor: "pointer",
                    }}
                >
                    {recommendations.loading ? "추천 중..." : "영화 추천"}
                </button>
            </form>

            {recommendations.error && (
                <p role="alert" style={{ color: "#dc2626" }}>
                    서버 오류: {recommendations.error}
                </p>
            )}

            <MfRecommendations data={recommendations.data} />
        </div>
    );
}
