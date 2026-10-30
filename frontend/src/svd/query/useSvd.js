
import {
    useQuery,
} from "@tanstack/react-query";

import { svdApi } from "../api/svdApi";


export function useSvdKpi() {
    return useQuery({
        queryKey: [
            "svd",
            "kpi",
        ],
        queryFn: svdApi.getKpi,
        staleTime: 60 * 1000,
        retry: false,
    });
}


export function useSvdRecommendations(
    userId
) {
    return useQuery({
        queryKey: [
            "svd",
            "recommendations",
            userId,
        ],
        queryFn: () =>
            svdApi.getRecommendations(
                userId
            ),
        enabled:
            Number.isInteger(userId) &&
            userId > 0,
        retry: false,
    });
}
