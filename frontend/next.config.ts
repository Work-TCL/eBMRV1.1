import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next's dev server blocks cross-origin requests for _next/static assets by default (anti
  // DNS-rebinding). This box is reached over its public IP, not just localhost, so the dev
  // origin needs to be allowlisted explicitly or every asset request 403s. Dev-only setting —
  // irrelevant to a production build.
  allowedDevOrigins: ["localhost", "127.0.0.1", "88.99.15.183"],
};

export default nextConfig;
