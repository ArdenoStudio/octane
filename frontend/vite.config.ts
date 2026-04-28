import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ["react", "react-dom"],
  },
  server: {
    port: Number(process.env.PORT) || 5173,
    host: true,
    strictPort: false,
  },
});
