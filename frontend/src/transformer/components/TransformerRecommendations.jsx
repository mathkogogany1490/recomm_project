
export default function TransformerRecommendations({ data }) {
    if (!data) return null;

    if (data.recommendations.length === 0) {
        return <p>추천 가능한 영화가 없습니다.</p>;
    }

    const cellStyle = {
        padding: 14,
        borderBottom: "1px solid #e2e8f0",
        textAlign: "left",
    };

    return (
        <div style={{ overflowX: "auto" }}>
            <h3>
                고객 {data.user_id} 추천 영화 TOP 5
            </h3>

            <table
                style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    background: "#fff",
                }}
            >
                <thead style={{ background: "#f1f5f9" }}>
                <tr>
                    <th style={cellStyle}>순위</th>
                    <th style={cellStyle}>영화 ID</th>
                    <th style={cellStyle}>영화 제목</th>
                    <th style={cellStyle}>장르</th>
                    <th style={cellStyle}>예측 평점</th>
                </tr>
                </thead>

                <tbody>
                {data.recommendations.map((movie) => (
                    <tr key={movie.movie_id}>
                        <td style={cellStyle}>{movie.rank}위</td>
                        <td style={cellStyle}>{movie.movie_id}</td>
                        <td style={cellStyle}>{movie.title}</td>
                        <td style={cellStyle}>{movie.genres}</td>
                        <td style={cellStyle}>
                            {Number(movie.predicted_rating).toFixed(4)}
                        </td>
                    </tr>
                ))}
                </tbody>
            </table>
        </div>
    );
}
