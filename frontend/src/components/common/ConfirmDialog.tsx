import { useState, type ReactNode } from "react";

import { Button } from "./Button";
import { Modal } from "./Modal";

interface ConfirmDialogProps {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  /** Optional checkbox (e.g. "also remove the indexed files"); its value is passed to onConfirm. */
  option?: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: (optionChecked: boolean) => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  option,
  danger,
  busy,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const [checked, setChecked] = useState(false);

  return (
    <Modal
      title={title}
      onClose={onCancel}
      footer={
        <>
          <Button onClick={onCancel}>Cancel</Button>
          <Button variant={danger ? "danger" : "primary"} disabled={busy} onClick={() => onConfirm(checked)}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="space-y-4 text-sm text-slate-700 dark:text-slate-200">
        {children}
        {option && (
          <label className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={checked}
              onChange={(event) => setChecked(event.target.checked)}
              className="mt-0.5 h-4 w-4"
            />
            <span>{option}</span>
          </label>
        )}
      </div>
    </Modal>
  );
}
