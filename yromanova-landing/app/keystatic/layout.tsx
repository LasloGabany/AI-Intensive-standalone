// Keystatic admin owns its full-page shell; bypass the marketing layout chrome.
export default function KeystaticLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
