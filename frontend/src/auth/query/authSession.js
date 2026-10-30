
import { useSyncExternalStore } from "react";
import { tokenStore } from "../../shared/api/http";

function subscribe(callback) {
    window.addEventListener(
        "auth-token-changed",
        callback
    );

    window.addEventListener(
        "storage",
        callback
    );

    return () => {
        window.removeEventListener(
            "auth-token-changed",
            callback
        );

        window.removeEventListener(
            "storage",
            callback
        );
    };
}

export function useAuthToken() {
    return useSyncExternalStore(
        subscribe,
        tokenStore.get,
        () => null
    );
}
