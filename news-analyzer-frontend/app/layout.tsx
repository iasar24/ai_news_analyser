import './globals.css';
import { ReactNode } from 'react';

export const metadata = {
  title: 'Advanced News Analyzer',
  description: 'AI-powered news aggregation and analysis',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
} 