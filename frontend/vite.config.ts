import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "og-image.svg", "octane-o.svg"],
      manifest: {
        name: "Octane — Live Sri Lanka Fuel Prices",
        short_name: "Octane",
        description:
          "Live Sri Lanka fuel prices, history, world comparison, trip cost calculator, and free public API.",
        theme_color: "#f59e0b",
        background_color: "#ffffff",
        display: "standalone",
        orientation: "portrait-primary",
        start_url: "/",
        scope: "/",
        icons: [
          {
            src: "/favicon.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any maskable",
          },
        ],
        shortcuts: [
          {
            name: "Live Prices",
            url: "/#prices",
            description: "Jump to current CPC fuel prices",
          },
          {
            name: "Price History",
            url: "/#history",
            description: "View historical price chart",
          },
          {
            name: "Trip Calculator",
            url: "/#calc",
            description: "Calculate trip fuel cost",
          },
        ],
      },
      workbox: {
        // Cache the shell and static assets; network-first for API calls
        globPatterns: ["**/*.{js,css,html,svg,png,ico,woff2}"],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\.octane\.lk\/v1\//,
            handler: "NetworkFirst",
            options: {
              cacheName: "octane-api",
              expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 }, // 1 hour
              networkTimeoutSeconds: 5,
            },
          },
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\//,
            handler: "StaleWhileRevalidate",
            options: { cacheName: "google-fonts-stylesheets" },
          },
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\//,
            handler: "CacheFirst",
            options: {
              cacheName: "google-fonts-webfonts",
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    dedupe: ["react", "react-dom"],
  },
  server: {
    port: Number(process.env.PORT) || 5173,
    host: true,
    strictPort: false,
  },
});
