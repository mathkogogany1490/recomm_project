import {
    useQuery,
} from "@tanstack/react-query";

import {
    getTransformerKpi,
    getTransformerRecommendations,
} from "../api/transformerApi";


export function useTransformerKpi() {
    return useQuery({
        queryKey: [
            "transformer",
            "kpi",
        ],
        queryFn: getTransformerKpi,
        staleTime: 60 * 1000,
        retry: false,
    });
}


export function useTransformerRecommendations(
    userId
) {
    return useQuery({
        queryKey: [
            "transformer",
            "recommendations",
            userId,
        ],
        queryFn: () =>
            getTransformerRecommendations(
                userId
            ),
        enabled:
            Number.isInteger(userId) &&
            userId > 0,
        retry: false,
    });
}