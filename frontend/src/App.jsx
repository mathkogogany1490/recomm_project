import { useEffect, useRef } from "react";
import { Route, Routes, useLocation, useNavigate } from "react-router-dom";

import AppLayout from "./shared/layout/AppLayout";
import MemberPage from "./auth/pages/MemberPage";
import SvdPage from "./svd/pages/SvdPage";
import MfPage from "./mf/pages/MfPage";
import TransformerPage from "./transformer/pages/TransformerPage";

const PAGES = [
    ["/member", MemberPage],
    ["/svd", SvdPage],
    ["/mf", MfPage],
    ["/transformer", TransformerPage],
];

function KeptPages() {
    const location = useLocation();
    const navigate = useNavigate();
    const visited = useRef(new Set());
    const path = location.pathname;
    const known = PAGES.some(([page]) => page === path);

    if (known) {
        visited.current.add(path);
    }

    useEffect(() => {
        if (!known) {
            navigate("/member", { replace: true });
        }
    }, [known, navigate]);

    return (
        <>
            {PAGES.map(([page, Page]) =>
                visited.current.has(page) ? (
                    <div
                        key={page}
                        style={{
                            display: path === page ? "block" : "none",
                        }}
                    >
                        <Page />
                    </div>
                ) : null
            )}
        </>
    );
}

export default function App() {
    return (
        <Routes>
            <Route element={<AppLayout />}>
                <Route path="*" element={<KeptPages />} />
            </Route>
        </Routes>
    );
}