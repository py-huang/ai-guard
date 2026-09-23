import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "trycloudflare.com",
    "*.trycloudflare.com",
  ],
};

export default nextConfig;
