
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_TARGET = "http://localhost:8000";

export default defineConfig({
    plugins: [react()],

    server: {
        host: "localhost",
        port: 5173,
        strictPort: true,

        proxy: {
            "/api": {
                target: API_TARGET,
                changeOrigin: true,
                rewrite: (path) =>
                    path.replace(/^\/api(?=\/|$)/, ""),
            },
        },
    },
});
