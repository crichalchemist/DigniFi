/**
 * Form Field - Trauma-informed form input component
 *
 * Design principles:
 * - Dignity-preserving error messages (never shame/blame)
 * - Clear, helpful guidance
 * - Accessibility-first (ARIA labels, error announcements)
 * - Plain language (6th-8th grade reading level)
 */

import { InputHTMLAttributes, ReactNode } from 'react';

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  name: string;
  error?: string;
  helpText?: string;
  required?: boolean;
  icon?: ReactNode;
}

export function FormField({
  label,
  name,
  error,
  helpText,
  required = false,
  icon,
  ...inputProps
}: FormFieldProps) {
  const inputId = `field-${name}`;
  const helpTextId = `${inputId}-help`;
  const errorId = `${inputId}-error`;

  return (
    <div className={`form-field ${error ? 'has-error' : ''}`}>
      <label htmlFor={inputId} className="form-label">
        {label}
        {required && (
          <span className="required-indicator" aria-label="required">
            *
          </span>
        )}
      </label>

      {helpText && (
        <p id={helpTextId} className="form-help-text">
          {helpText}
        </p>
      )}

      <div className="form-input-wrapper">
        {icon && <div className="form-input-icon">{icon}</div>}
        <input
          id={inputId}
          name={name}
          className={`form-input ${icon ? 'with-icon' : ''}`}
          aria-describedby={
            error
              ? `${errorId} ${helpText ? helpTextId : ''}`
              : helpText
              ? helpTextId
              : undefined
          }
          aria-invalid={error ? 'true' : 'false'}
          aria-required={required}
          {...inputProps}
        />
      </div>

      {error && (
        <p
          id={errorId}
          className="form-error"
          role="alert"
          aria-live="assertive"
        >
          {error}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// Textarea variant
// ============================================================================

interface FormTextareaProps
  extends InputHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  name: string;
  error?: string;
  helpText?: string;
  required?: boolean;
  rows?: number;
}

export function FormTextarea({
  label,
  name,
  error,
  helpText,
  required = false,
  rows = 4,
  ...textareaProps
}: FormTextareaProps) {
  const inputId = `field-${name}`;
  const helpTextId = `${inputId}-help`;
  const errorId = `${inputId}-error`;

  return (
    <div className={`form-field ${error ? 'has-error' : ''}`}>
      <label htmlFor={inputId} className="form-label">
        {label}
        {required && (
          <span className="required-indicator" aria-label="required">
            *
          </span>
        )}
      </label>

      {helpText && (
        <p id={helpTextId} className="form-help-text">
          {helpText}
        </p>
      )}

      <textarea
        id={inputId}
        name={name}
        rows={rows}
        className="form-input"
        aria-describedby={
          error
            ? `${errorId} ${helpText ? helpTextId : ''}`
            : helpText
            ? helpTextId
            : undefined
        }
        aria-invalid={error ? 'true' : 'false'}
        aria-required={required}
        {...(textareaProps as any)}
      />

      {error && (
        <p
          id={errorId}
          className="form-error"
          role="alert"
          aria-live="assertive"
        >
          {error}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// Select variant
// ============================================================================

interface SelectOption {
  value: string;
  label: string;
}

interface FormSelectProps {
  label: string;
  name: string;
  options: SelectOption[];
  error?: string;
  helpText?: string;
  required?: boolean;
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
}

export function FormSelect({
  label,
  name,
  options,
  error,
  helpText,
  required = false,
  value,
  onChange,
  placeholder = 'Please select...',
}: FormSelectProps) {
  const inputId = `field-${name}`;
  const helpTextId = `${inputId}-help`;
  const errorId = `${inputId}-error`;

  return (
    <div className={`form-field ${error ? 'has-error' : ''}`}>
      <label htmlFor={inputId} className="form-label">
        {label}
        {required && (
          <span className="required-indicator" aria-label="required">
            *
          </span>
        )}
      </label>

      {helpText && (
        <p id={helpTextId} className="form-help-text">
          {helpText}
        </p>
      )}

      <select
        id={inputId}
        name={name}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        className="form-input"
        aria-describedby={
          error
            ? `${errorId} ${helpText ? helpTextId : ''}`
            : helpText
            ? helpTextId
            : undefined
        }
        aria-invalid={error ? 'true' : 'false'}
        aria-required={required}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      {error && (
        <p
          id={errorId}
          className="form-error"
          role="alert"
          aria-live="assertive"
        >
          {error}
        </p>
      )}
    </div>
  );
}

export default FormField;
