// Independent local previews can use separate build directories.
const nextConfig = {distDir:process.env.MACROLENS_NEXT_DIST_DIR || '.next',experimental:{cpus:1}};
export default nextConfig;
