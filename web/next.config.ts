import type { NextConfig } from "next"

// A static site: every page is built from web/data/*.json, so it can be served from any static host.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
}

export default nextConfig
