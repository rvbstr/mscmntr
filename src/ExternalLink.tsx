import type { ReactNode } from "react";
const safeExternal = (url: string) => {
  try {
    const p = new URL(url);
    return ["https:", "http:"].includes(p.protocol) &&
      !p.username &&
      !p.password
      ? url
      : "#";
  } catch {
    return "#";
  }
};

export function Ext({
  href,
  children,
  className = "",
  ...props
}: {
  href: string;
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <a
      href={safeExternal(href)}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
      {...props}
    >
      {children}
    </a>
  );
}
