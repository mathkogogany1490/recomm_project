
export default function TransformerKpi({ data }) {
    const metrics = [
        {
            label: "평균 제곱 오차 (MSE)",
            value: data.mse,
        },
        {
            label: "평균 절대 오차 (MAE)",
            value: data.mae,
        },
        {
            label: "RMSE",
            value: data.rmse,
        },
    ];

    return (
        <div
            style={{
                display: "grid",
                gridTemplateColumns:
                    "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 16,
                marginBottom: 20,
            }}
        >
            {metrics.map((metric) => (
                <div
                    key={metric.label}
                    style={{
                        padding: 20,
                        background: "#fff",
                        border: "1px solid #e2e8f0",
                        borderRadius: 12,
                    }}
                >
                    <div
                        style={{
                            fontSize: 14,
                            color: "#64748b",
                        }}
                    >
                        {metric.label}
                    </div>

                    <div
                        style={{
                            marginTop: 10,
                            fontSize: 28,
                            fontWeight: 700,
                        }}
                    >
                        {Number(metric.value).toFixed(4)}
                    </div>
                </div>
            ))}
        </div>
    );
}
