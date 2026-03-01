/**
 * Skip Navigation - WCAG 2.1 AA "Skip to main content" link
 *
 * Visually hidden until focused via keyboard (Tab key).
 * Allows screen reader and keyboard users to bypass repetitive navigation.
 */

interface SkipNavigationProps {
  /** ID of the target element to skip to (without #) */
  targetId?: string;
  /** Link text shown when focused */
  label?: string;
}

export function SkipNavigation({
  targetId = 'main-content',
  label = 'Skip to main content',
}: SkipNavigationProps) {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.focus();
      target.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <a
      href={`#${targetId}`}
      className="skip-navigation"
      onClick={handleClick}
    >
      {label}
    </a>
  );
}

export default SkipNavigation;
