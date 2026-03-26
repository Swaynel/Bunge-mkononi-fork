import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Bunge Mkononi',
    template: '%s | Bunge Mkononi',
  },
  description: 'Track Kenyan Parliament bills, votes, and citizen participation in one place.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full text-foreground">{children}</body>
    </html>
  );
}
