import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { Poppins } from 'next/font/google'

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const poppins = Poppins({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'], // Add whatever weights you need
  variable: '--font-poppins',
  display: 'swap',
})


const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "iMet - Remember Everyone You Meet",
  description: "A smart way to capture and organize your professional and personal connections",
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon-32x32.png",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body
        className={`${poppins.variable} antialiased`} scroll-smooth
      >
        <header className="border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <Link href="/" className="text-xl font-bold text-blue-600">
                    <img
                      src="/imet-logo-png.png"
                      alt="Imet Logo"
                      className="h-12 w-auto"
                    />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
