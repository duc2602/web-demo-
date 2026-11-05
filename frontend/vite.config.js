import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import { isIP } from "node:net";
import { resolve } from "node:path";
function isLoopbackHost(host) {
    var normalized = host.replace(/^\[|\]$/g, "").toLowerCase();
    if (normalized === "localhost")
        return true;
    var family = isIP(normalized);
    return family === 4 ? normalized.startsWith("127.") : family === 6 && normalized === "::1";
}
export default defineConfig(function (_a) {
    var mode = _a.mode, command = _a.command;
    var envDir = "../backend";
    var env = loadEnv(mode, envDir, "");
    var host = env.VITE_DEV_HOST;
    var port = Number(env.VITE_DEV_PORT);
    var certFile = env.TLS_CERTFILE;
    var keyFile = env.TLS_KEYFILE;
    if (!host || isNaN(port) || Math.floor(port) !== port || port < 1 || port > 65535 || !env.VITE_API_BASE_URL) {
        throw new Error("Set VITE_DEV_HOST, VITE_DEV_PORT, and VITE_API_BASE_URL in backend/.env.");
    }
    if (Boolean(certFile) !== Boolean(keyFile)) {
        throw new Error("Set both TLS_CERTFILE and TLS_KEYFILE in backend/.env to enable HTTPS for Vite.");
    }
    if (command === "serve" && !certFile && !isLoopbackHost(host)) {
        throw new Error("Vite must bind to localhost unless HTTPS is configured with TLS_CERTFILE and TLS_KEYFILE.");
    }
    return {
        envDir: envDir,
        plugins: [react()],
        server: {
            host: host,
            port: port,
            strictPort: true,
            https: command === "serve" && certFile && keyFile
                ? {
                    cert: readFileSync(resolve(envDir, certFile)),
                    key: readFileSync(resolve(envDir, keyFile)),
                }
                : undefined,
            proxy: {
                "/api": {
                    target: env.VITE_API_BASE_URL,
                    changeOrigin: true,
                },
            },
        },
    };
});
