
import { Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "./shared/layout/AppLayout";
import MemberPage from "./auth/pages/MemberPage";
import SvdPage from "./svd/pages/SvdPage";
import MfPage from "./mf/pages/MfPage";
import TransformerPage from "./transformer/pages/TransformerPage";

export default function App() {
    return (
        <Routes>
            <Route element={<AppLayout />}>
                <Route
                    path="/"
                    element={<Navigate to="/member" replace />}
                />

                <Route
                    path="/member"
                    element={<MemberPage />}
                />

                <Route
                    path="/svd"
                    element={<SvdPage />}
                />

                <Route
                    path="/mf"
                    element={<MfPage />}
                />

                <Route
                    path="/transformer"
                    element={<TransformerPage />}
                />

                <Route
                    path="*"
                    element={<Navigate to="/member" replace />}
                />
            </Route>
        </Routes>
    );
}
