/**
 * ConfirmDialog component.
 *
 * Reusable modal for confirming destructive or critical actions.
 */

import React, { useState } from 'react';

export interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'default';
  isLoading?: boolean;
  reasonLabel?: string;
  reasonPlaceholder?: string;
  onConfirm: (reason?: string) => void;
  onCancel: () => void;
}

const variantStyles = {
  danger: {
    icon: 'text-red-400',
    iconBg: 'bg-red-100',
    button: 'btn-danger',
  },
  warning: {
    icon: 'text-amber-400',
    iconBg: 'bg-amber-100',
    button: 'btn-warning',
  },
  default: {
    icon: 'text-primary-400',
    iconBg: 'bg-primary-100',
    button: 'btn-primary',
  },
};

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  isLoading = false,
  reasonLabel,
  reasonPlaceholder,
  onConfirm,
  onCancel,
}) => {
  const [reason, setReason] = useState('');

  if (!isOpen) return null;

  const styles = variantStyles[variant];

  const handleConfirm = () => {
    onConfirm(reasonLabel ? reason : undefined);
    setReason('');
  };

  const handleCancel = () => {
    setReason('');
    onCancel();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div className="modal-backdrop" onClick={handleCancel} />

      {/* Dialog */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="modal-panel relative max-w-md p-0">
          <div className="px-6 py-5">
            <div className="flex items-start gap-4">
              {/* Icon */}
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${styles.iconBg}`}>
                <svg className={`h-6 w-6 ${styles.icon}`} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                  />
                </svg>
              </div>

              {/* Content */}
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
                <p className="mt-2 text-sm text-gray-600">{message}</p>

                {reasonLabel && (
                  <div className="mt-4">
                    <label htmlFor="confirm-reason" className="block text-sm font-medium text-gray-700">
                      {reasonLabel}
                    </label>
                    <textarea
                      id="confirm-reason"
                      rows={2}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                      placeholder={reasonPlaceholder}
                      value={reason}
                      onChange={e => setReason(e.target.value)}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
            <button
              type="button"
              onClick={handleCancel}
              disabled={isLoading}
              className="btn-secondary"
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={isLoading}
              className={styles.button}
            >
              {isLoading ? (
                <span className="flex items-center">
                  <span className="spinner-sm mr-2" />
                  Processing...
                </span>
              ) : (
                confirmLabel
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
