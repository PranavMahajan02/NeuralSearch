import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

// Disabled buttons stay readable (AA contrast): grey with dark text, not faded colour.
const DISABLED =
  "disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-700 disabled:ring-0 dark:disabled:bg-slate-800 dark:disabled:text-slate-300";

const VARIANT: Record<Variant, string> = {
  primary: "bg-blue-700 text-white hover:bg-blue-800",
  secondary:
    "bg-white text-slate-800 ring-1 ring-slate-300 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-700 dark:hover:bg-slate-800",
  danger: "bg-rose-700 text-white hover:bg-rose-800",
  ghost: "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800",
};

export function Button({
  variant = "secondary",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${VARIANT[variant]} ${DISABLED} ${className}`}
      {...props}
    />
  );
}
