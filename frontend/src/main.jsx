
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import koKR from "antd/locale/ko_KR";

import App from "./App";

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: false,
            refetchOnWindowFocus: false,
        },
    },
});

ReactDOM.createRoot(
    document.getElementById("root")
).render(
    <React.StrictMode>
        <ConfigProvider locale={koKR}>
            <QueryClientProvider client={queryClient}>
                <BrowserRouter>
                    <App />
                </BrowserRouter>
            </QueryClientProvider>
        </ConfigProvider>
    </React.StrictMode>
);
