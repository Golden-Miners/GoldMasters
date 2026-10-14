import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    GOLDMASTERS_API_BASE_URL: process.env.GOLDMASTERS_API_BASE_URL ?? "http://127.0.0.1:8000",
  },
};

export default nextConfig;
