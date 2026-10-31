import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// No proxy on purpose: the browser calls http://localhost:8000 directly,
// so you can see CORS in action (check the OPTIONS preflight in DevTools).
export default defineConfig({
  plugins: [react()],
  // Read .env from the project root (one .env for the whole project).
  // Only VITE_* variables are exposed to the browser code.
  envDir: "..",
  server: {
    port: 5173,
    strictPort: true, // fail instead of silently moving to another port
  },
});
