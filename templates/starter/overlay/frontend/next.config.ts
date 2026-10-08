import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 빌드 폴더. scripts/e2e.sh가 격리 실행에 다른 폴더(.next-e2e)를 써서, make serve로 떠 있는 빌드를 덮지 않는다
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
