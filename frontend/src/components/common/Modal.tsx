import { useEffect, useId, useRef, type ReactNode } from "react";
import { motion } from "motion/react";
import { X } from "lucide-react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** "dialog" (centered) or "drawer" (slides from the left, for the mobile menu). */
  variant?: "dialog" | "drawer";
  footer?: ReactNode;
  size?: "md" | "lg";
}

/**
 * Accessible modal: role="dialog" + aria-modal, labelled by its title, focus
 * moves inside and is trapped (Tab / Shift+Tab wrap), Esc closes, and focus
 * returns to the element that opened it.
 */
export function Modal({ title, onClose, children, variant = "dialog", footer, size = "md" }: ModalProps) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const first = panel.current?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? panel.current)?.focus();

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCloseRef.current();
        return;
      }

      if (event.key !== "Tab" || !panel.current) return;

      const items = Array.from(panel.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (items.length === 0) return;

      const firstItem = items[0];
      const lastItem = items[items.length - 1];

      if (event.shiftKey && document.activeElement === firstItem) {
        event.preventDefault();
        lastItem.focus();
      } else if (!event.shiftKey && document.activeElement === lastItem) {
        event.preventDefault();
        firstItem.focus();
      }
    };

    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      opener?.focus?.();
    };
  }, []);

  const layout =
    variant === "drawer"
      ? "fixed inset-y-0 left-0 w-72 max-w-[85vw] rounded-none"
      : `relative mx-4 my-8 w-full ${size === "lg" ? "max-w-3xl" : "max-w-xl"} overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800`;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto">
      <div aria-hidden="true" className="fixed inset-0 bg-slate-950/60 backdrop-blur-md" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={`${layout} flex flex-col bg-white shadow-2xl outline-none dark:bg-slate-900`}
      >
        <div className="flex items-center justify-between gap-4 border-b border-slate-100 bg-slate-50/50 px-5 py-4 dark:border-slate-800/80 dark:bg-slate-950/40">
          <h2
            id={titleId}
            className="truncate pr-4 font-display text-sm font-bold text-slate-800 md:text-base dark:text-slate-100"
          >
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <X aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2.5 border-t border-slate-100 bg-slate-50/50 px-5 py-4 dark:border-slate-800/80 dark:bg-slate-950/40">
            {footer}
          </div>
        )}
      </motion.div>
    </div>
  );
}
