import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// No proxy on purpose: the browser calls http://localhost:8000 directly,
// so you can see CORS in action (check the OPTIONS preflight in DevTools).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
