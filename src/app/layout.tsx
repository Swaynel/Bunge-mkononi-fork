import type { Metadata } from 'next';
import { IBM_Plex_Serif, Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains-mono',
});

const ibmPlexSerif = IBM_Plex_Serif({
  subsets: ['latin'],
  variable: '--font-ibm-plex-serif',
  weight: ['400', '500', '600'],
});

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
      <body className={`${inter.variable} ${jetbrainsMono.variable} ${ibmPlexSerif.variable} min-h-full text-foreground`}>
        {children}
      </body>
    </html>
  );
}
