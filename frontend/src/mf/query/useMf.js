import {
    useQuery,
} from "@tanstack/react-query";

import {
    fetchMfKpi,
    fetchMfRecommendations,
} from "../api/mfApi";


export function useMfKpi() {
    return useQuery({
        queryKey: [
            "mf",
            "kpi",
        ],
        queryFn: fetchMfKpi,
        staleTime: 60 * 1000,
        retry: false,
    });
}


export function useMfRecommendations(
    userId
) {
    return useQuery({
        queryKey: [
            "mf",
            "recommendations",
            userId,
        ],
        queryFn: () =>
            fetchMfRecommendations(
                userId
            ),
        enabled:
            Number.isInteger(userId) &&
            userId > 0,
        retry: false,
    });
}