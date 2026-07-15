import { Card } from "./ui";
import { ThemeToggle } from "./ThemeToggle";
import { LogoLockup } from "./Logo";

export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <div className="mb-8">
        <LogoLockup className="h-24" />
      </div>
      <Card className="w-full max-w-sm">
        <h1 className="text-xl font-semibold">{title}</h1>
        <p className="mb-6 mt-1 text-sm text-muted">{subtitle}</p>
        {children}
      </Card>
    </div>
  );
}
