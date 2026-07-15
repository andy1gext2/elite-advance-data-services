/** @type {import('next').NextConfig} */

// The browser only ever talks to the Next origin. All /api/* calls are proxied
// server-side to the FastAPI backend, so there is no cross-origin request and
// no CORS to configure. Point at a different backend with API_PROXY_TARGET.
const API_TARGET = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_TARGET}/api/:path*` },
      { source: "/health", destination: `${API_TARGET}/health` },
      { source: "/media/:path*", destination: `${API_TARGET}/media/:path*` },
    ];
  },
};

export default nextConfig;
