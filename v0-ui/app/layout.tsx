export const metadata = {
  title: 'Vinted Notifications Bot',
  description: 'Modern UI for Vinted monitoring',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  )
}