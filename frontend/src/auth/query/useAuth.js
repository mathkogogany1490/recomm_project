
import {
    useMutation,
    useQuery,
    useQueryClient,
} from "@tanstack/react-query";

import { authApi } from "../api/authApi";
import { tokenStore } from "../../shared/api/http";
import { useAuthToken } from "./authSession";

const ME_QUERY_KEY = ["auth", "me"];

export function useAuth() {
    const queryClient = useQueryClient();
    const token = useAuthToken();

    const meQuery = useQuery({
        queryKey: [...ME_QUERY_KEY, token],
        queryFn: authApi.getMe,
        enabled: Boolean(token),
        staleTime: 60 * 1000,
    });

    function logout() {
        queryClient.removeQueries({
            queryKey: ME_QUERY_KEY,
        });

        tokenStore.clear();
    }

    const loginMutation = useMutation({
        mutationFn: authApi.login,

        onSuccess: (data) => {
            tokenStore.set(data.access_token);
            queryClient.setQueryData(
                [...ME_QUERY_KEY, data.access_token],
                null
            );

            queryClient.invalidateQueries({
                queryKey: ME_QUERY_KEY,
            });
        },
    });

    const registerMutation = useMutation({
        mutationFn: authApi.register,
    });

    const verifyMutation = useMutation({
        mutationFn: authApi.verifyEmail,
    });

    const resendMutation = useMutation({
        mutationFn: authApi.resendCode,
    });

    return {
        user: token ? meQuery.data ?? null : null,
        isLoading: Boolean(token) && meQuery.isPending,
        isAuthenticated: Boolean(token && meQuery.data),
        meQuery,
        loginMutation,
        registerMutation,
        verifyMutation,
        resendMutation,
        logout,
    };
}
