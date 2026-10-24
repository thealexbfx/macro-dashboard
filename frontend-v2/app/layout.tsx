import './globals.css';
export const metadata = { title: 'MacroLens | Research workspace', description: 'Macroeconomic research workspace with real source observations' };
export default function Layout({ children }: {
    children: React.ReactNode;
}) { return <html lang="en"><body>{children}</body></html>; }
