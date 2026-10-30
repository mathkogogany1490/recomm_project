
export default function MfRecommendations({ data }) {
    if (!data) return null;

    if (data.recommendations.length === 0) {
        return <p>추천 가능한 영화가 없습니다.</p>;
    }

    return (
        <div style={{ overflowX: "auto" }}>
            <h3>고객 {data.user_id} 추천 영화 TOP 5</h3>

            <table
                style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    background: "#ffffff",
                }}
            >
                <thead>
                <tr style={{ background: "#f1f5f9" }}>
                    {[
                        "순위",
                        "영화 ID",
                        "영화 제목",
                        "장르",
                        "예측 평점",
                    ].map((name) => (
                        <th
                            key={name}
                            style={{
                                padding: 14,
                                textAlign: "left",
                                borderBottom: "1px solid #ddd",
                            }}
                        >
                            {name}
                        </th>
                    ))}
                </tr>
                </thead>

                <tbody>
                {data.recommendations.map((movie) => (
                    <tr key={movie.movie_id}>
                        <td style={{ padding: 14 }}>{movie.rank}위</td>
                        <td style={{ padding: 14 }}>{movie.movie_id}</td>
                        <td style={{ padding: 14 }}>{movie.title}</td>
                        <td style={{ padding: 14 }}>{movie.genres}</td>
                        <td style={{ padding: 14 }}>
                            {movie.predicted_rating.toFixed(4)}
                        </td>
                    </tr>
                ))}
                </tbody>
            </table>
        </div>
    );
}
