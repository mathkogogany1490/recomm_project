
export default function MfKpi({ data }) {
    const items = [
        { label: "평균 제곱 오차 (MSE)", value: data.mse },
        { label: "평균 절대 오차 (MAE)", value: data.mae },
        { label: "RMSE", value: data.rmse },
    ];

    return (
        <div
            style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: 16,
                marginBottom: 24,
            }}
        >
            {items.map((item) => (
                <div
                    key={item.label}
                    style={{
                        border: "1px solid #e5e7eb",
                        borderRadius: 12,
                        padding: 20,
                        background: "#ffffff",
                    }}
                >
                    <div style={{ color: "#64748b", fontSize: 14 }}>
                        {item.label}
                    </div>

                    <div
                        style={{
                            fontSize: 28,
                            fontWeight: 700,
                            marginTop: 10,
                        }}
                    >
                        {Number(item.value).toFixed(4)}
                    </div>
                </div>
            ))}
        </div>
    );
}
