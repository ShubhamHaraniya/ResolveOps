import type { NextConfig } from "next";

// Backend (FastAPI) origin used by the dev/production server to proxy /api and /ready.
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
      { source: "/ready", destination: `${BACKEND_URL}/ready` },
    ];
  },
};

export default nextConfig;
