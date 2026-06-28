import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://backend:8000/api/:path*",
      },
      {
        source: "/ws/:path*",
        destination: "ws://backend:8000/ws/:path*",
      },
    ];
  },
};

export default nextConfig;
