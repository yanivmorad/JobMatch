import React from 'react';

const VARIANTS = {
  primary: 'bg-ink text-ink-inverse hover:opacity-90 font-semibold',
  accent: 'bg-accent text-ink-inverse hover:opacity-90 font-semibold',
  go: 'bg-go-soft text-go hover:brightness-95 font-semibold',
  secondary: 'bg-surface text-ink border border-line-strong hover:bg-hover font-medium',
  danger: 'bg-surface text-danger border border-line-strong hover:bg-danger-soft font-semibold',
  dangerSolid: 'bg-danger-fill text-white hover:opacity-90 font-semibold',
  ghost: 'bg-transparent text-ink-2 hover:bg-hover hover:text-ink font-medium',
};

const SIZES = {
  sm: 'h-8 px-3 text-[13px] gap-1.5 rounded-md',
  md: 'h-10 px-4 text-sm gap-2 rounded-md max-sm:h-11',
  icon: 'h-10 w-10 justify-center rounded-md max-sm:h-11 max-sm:w-11',
  iconSm: 'h-8 w-8 justify-center rounded-md',
};

// כפתור אחד לכל הדשבורד. href הופך אותו לקישור (נפתח בטאב חדש כשהוא חיצוני).
const Button = React.forwardRef(function Button(
  { variant = 'secondary', size = 'md', href, className = '', children, type = 'button', ...rest },
  ref,
) {
  const cls = `inline-flex items-center whitespace-nowrap select-none transition-[background-color,opacity,filter] duration-100 disabled:opacity-45 disabled:pointer-events-none ${VARIANTS[variant]} ${SIZES[size]} ${className}`;
  if (href) {
    const external = /^https?:/.test(href);
    return (
      <a ref={ref} href={href} className={cls} {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})} {...rest}>
        {children}
      </a>
    );
  }
  return (
    <button ref={ref} type={type} className={cls} {...rest}>
      {children}
    </button>
  );
});

export default Button;
