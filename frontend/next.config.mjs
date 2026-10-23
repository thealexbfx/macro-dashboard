/** @type {import('next').NextConfig} */
const nextConfig = { output: process.env.MACROLENS_LOCAL_BUILD === '1' ? undefined : 'standalone' };
export default nextConfig;
