
async function request(url) {
    let response;

    try {
        response = await fetch(url);
    } catch {
        throw new Error("백엔드 서버에 연결할 수 없습니다.");
    }

    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error(
            `서버 응답 오류 (HTTP ${response.status})`
        );
    }

    if (!response.ok) {
        let message = data.detail || "서버 오류";

        if (Array.isArray(message)) {
            message = message
                .map((item) => item.msg || JSON.stringify(item))
                .join(", ");
        }

        throw new Error(String(message));
    }

    return data;
}


export function fetchMfKpi() {
    return request("/mf/kpi");
}


export function fetchMfRecommendations(userId) {
    return request(
        `/mf/recommendations?user_id=${encodeURIComponent(userId)}`
    );
}
