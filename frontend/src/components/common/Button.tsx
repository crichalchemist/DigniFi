/**
 * Button Component - Accessible, trauma-informed button
 *
 * Accessibility features:
 * - Keyboard navigation support
 * - Screen reader announcements for loading/disabled states
 * - High contrast support
 * - Focus indicators
 */

import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'text';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  loadingText?: string;
  icon?: ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  loadingText = 'Loading...',
  icon,
  iconPosition = 'left',
  fullWidth = false,
  disabled,
  type = 'button',
  className = '',
  ...buttonProps
}: ButtonProps) {
  const baseClasses = 'button';
  const variantClasses = `button--${variant}`;
  const sizeClasses = `button--${size}`;
  const widthClasses = fullWidth ? 'button--full-width' : '';
  const loadingClasses = isLoading ? 'button--loading' : '';
  const disabledClasses = disabled ? 'button--disabled' : '';

  const classes = [
    baseClasses,
    variantClasses,
    sizeClasses,
    widthClasses,
    loadingClasses,
    disabledClasses,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      aria-disabled={disabled || isLoading}
      {...buttonProps}
    >
      {isLoading && (
        <span className="button-spinner" aria-hidden="true">
          <svg
            className="spinner"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle
              className="spinner-track"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="spinner-head"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </span>
      )}

      {!isLoading && icon && iconPosition === 'left' && (
        <span className="button-icon button-icon--left" aria-hidden="true">
          {icon}
        </span>
      )}

      <span className="button-content">
        {isLoading ? loadingText : children}
      </span>

      {!isLoading && icon && iconPosition === 'right' && (
        <span className="button-icon button-icon--right" aria-hidden="true">
          {icon}
        </span>
      )}

      {/* Screen reader announcement for loading state */}
      {isLoading && (
        <span className="sr-only" aria-live="polite">
          {loadingText}
        </span>
      )}
    </button>
  );
}

export default Button;
