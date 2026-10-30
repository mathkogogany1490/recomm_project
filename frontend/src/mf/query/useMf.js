
import { useEffect, useState } from "react";

import {
    fetchMfKpi,
    fetchMfRecommendations,
} from "../api/mfApi";


export function useMfKpi() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let active = true;

        fetchMfKpi()
            .then((result) => {
                if (active) setData(result);
            })
            .catch((err) => {
                if (active) setError(err.message);
            })
            .finally(() => {
                if (active) setLoading(false);
            });

        return () => {
            active = false;
        };
    }, []);

    return { data, loading, error };
}


export function useMfRecommendations() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    async function search(userId) {
        setLoading(true);
        setError("");
        setData(null);

        try {
            const result = await fetchMfRecommendations(userId);
            setData(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    return { data, loading, error, search };
}
