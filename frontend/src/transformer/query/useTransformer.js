import { useQuery } from "@tanstack/react-query";

import {
    getTransformerKpi,
    getTransformerRecommendations,
} from "../api/transformerApi";

export function useTransformerKpi() {
    return useQuery({
        queryKey: ["transformer", "kpi"],
        queryFn: getTransformerKpi,
        staleTime: 60000,
        retry: 1,
    });
}

export function useTransformerRecommendations(userId) {
    return useQuery({
        queryKey: [
            "transformer",
            "recommendations",
            userId,
        ],
        queryFn: () =>
            getTransformerRecommendations(userId),
        enabled:
            userId !== null &&
            userId !== undefined &&
            String(userId).trim() !== "",
        staleTime: 60000,
        retry: 1,
    });
}