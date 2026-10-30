import { useState } from "react";

import {
    useTransformerKpi,
    useTransformerRecommendations,
} from "../query/useTransformer";

export default function TransformerPage() {
    const [inputUserId, setInputUserId] = useState("1");
    const [selectedUserId, setSelectedUserId] = useState("1");

    const {
        data: kpi,
        isLoading: kpiLoading,
        error: kpiError,
    } = useTransformerKpi();

    const {
        data: recommendationData,
        isLoading: recommendationLoading,
        error: recommendationError,
    } = useTransformerRecommendations(selectedUserId);

    const recommendations = Array.isArray(recommendationData)
        ? recommendationData
        : recommendationData?.recommendations ?? [];

    const handleSearch = (event) => {
        event.preventDefault();

        const value = inputUserId.trim();

        if (value) {
            setSelectedUserId(value);
        }
    };

    return (
        <main style={{ padding: "24px" }}>
            <h2>Transformer 영화 추천 시스템</h2>

            <section style={{ marginBottom: "30px" }}>
                <h3>Transformer 모델 KPI</h3>

                {kpiLoading && <p>모델 정보를 불러오는 중...</p>}

                {kpiError && (
                    <p style={{ color: "red" }}>
                        {kpiError.message}
                    </p>
                )}

                {kpi && (
                    <pre
                        style={{
                            background: "#f5f5f5",
                            padding: "16px",
                            borderRadius: "8px",
                            overflowX: "auto",
                        }}
                    >
                        {JSON.stringify(kpi, null, 2)}
                    </pre>
                )}
            </section>

            <section>
                <h3>사용자별 영화 추천</h3>

                <form
                    onSubmit={handleSearch}
                    style={{
                        display: "flex",
                        gap: "10px",
                        marginBottom: "20px",
                    }}
                >
                    <input
                        type="number"
                        min="1"
                        value={inputUserId}
                        onChange={(event) =>
                            setInputUserId(event.target.value)
                        }
                        placeholder="사용자 ID"
                        style={{ padding: "8px" }}
                    />

                    <button type="submit">
                        추천 조회
                    </button>
                </form>

                {recommendationLoading && (
                    <p>추천 영화를 불러오는 중...</p>
                )}

                {recommendationError && (
                    <p style={{ color: "red" }}>
                        {recommendationError.message}
                    </p>
                )}

                {!recommendationLoading &&
                    !recommendationError &&
                    recommendations.length === 0 && (
                        <p>추천 결과가 없습니다.</p>
                    )}

                {recommendations.length > 0 && (
                    <table
                        style={{
                            width: "100%",
                            borderCollapse: "collapse",
                            textAlign: "left",
                        }}
                    >
                        <thead>
                            <tr>
                                {[
                                    "순위",
                                    "영화 ID",
                                    "영화 제목",
                                    "장르",
                                    "추천 점수",
                                ].map((title) => (
                                    <th
                                        key={title}
                                        style={{
                                            padding: "12px",
                                            borderBottom: "2px solid #ddd",
                                        }}
                                    >
                                        {title}
                                    </th>
                                ))}
                            </tr>
                        </thead>

                        <tbody>
                            {recommendations.slice(0, 5).map(
                                (movie, index) => (
                                    <tr
                                        key={
                                            movie.movie_id ??
                                            movie.movieID ??
                                            index
                                        }
                                    >
                                        <td style={{ padding: "12px" }}>
                                            {index + 1}
                                        </td>

                                        <td style={{ padding: "12px" }}>
                                            {movie.movie_id ??
                                                movie.movieID ??
                                                "-"}
                                        </td>

                                        <td style={{ padding: "12px" }}>
                                            {movie.title ?? "-"}
                                        </td>

                                        <td style={{ padding: "12px" }}>
                                            {Array.isArray(movie.genres)
                                                ? movie.genres.join(", ")
                                                : movie.genres ?? "-"}
                                        </td>

                                        <td style={{ padding: "12px" }}>
                                            {movie.score ??
                                                movie.predicted_rating ??
                                                "-"}
                                        </td>
                                    </tr>
                                )
                            )}
                        </tbody>
                    </table>
                )}
            </section>
        </main>
    );
}