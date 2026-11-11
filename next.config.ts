import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "trycloudflare.com",
    "*.trycloudflare.com",
  ],
  devIndicators: false,
  typescript: {
    ignoreBuildErrors: true,
  },
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "same-origin" },
          // Voice features need the microphone; everything else is switched off.
          { key: "Permissions-Policy", value: "microphone=(self), camera=(), geolocation=(), payment=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
