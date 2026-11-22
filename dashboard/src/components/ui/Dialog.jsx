import React, { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';
import { createPortal } from 'react-dom';

const FOCUSABLE = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

// דיאלוג נגיש: role=dialog, Esc סוגר, פוקוס כלוא ומוחזר לכפתור שפתח.
// variant="sheet": בנייד מסך מלא (גיליון), בדסקטופ פאנל צד. "center": חלון קטן במרכז.
const Dialog = ({ open, onClose, title, hideTitle = false, variant = 'center', children, footer, size = 'md', initialFocusRef }) => {
  const panelRef = useRef(null);
  const titleId = useId();
  const onCloseRef = useRef(onClose);
  useEffect(() => { onCloseRef.current = onClose; });

  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    const panel = panelRef.current;
    const target = initialFocusRef?.current || panel?.querySelector('[data-autofocus]') || panel;
    target?.focus({ preventScroll: true });
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onCloseRef.current?.();
        return;
      }
      if (e.key !== 'Tab' || !panel) return;
      const items = [...panel.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null);
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey, true);
    return () => {
      document.removeEventListener('keydown', onKey, true);
      document.body.style.overflow = prevOverflow;
      if (previous && previous.focus) previous.focus({ preventScroll: true });
    };
  }, [open, initialFocusRef]);

  if (!open) return null;

  const widths = { sm: 'sm:max-w-md', md: 'sm:max-w-xl', lg: 'sm:max-w-3xl', xl: 'sm:max-w-4xl' };
  const panelCls = variant === 'sheet'
    ? `fixed inset-0 sm:inset-y-0 sm:start-auto sm:end-0 w-full ${widths[size]} sm:w-[min(100%,56rem)] bg-surface flex flex-col sheet-in sm:shadow-overlay`
    : `relative w-full ${widths[size]} max-h-[min(90dvh,760px)] bg-surface rounded-lg shadow-overlay flex flex-col pop-in`;

  return createPortal(
    <div className={`fixed inset-0 z-[100] ${variant === 'center' ? 'flex items-end sm:items-center justify-center p-0 sm:p-6' : ''}`} dir="rtl">
      <div className="absolute inset-0 bg-[var(--scrim)]" onClick={onClose} aria-hidden />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={`${panelCls} outline-none ${variant === 'center' ? 'max-sm:rounded-b-none max-sm:max-h-[92dvh]' : ''}`}
      >
        <div className={`flex items-center gap-2 shrink-0 px-5 max-sm:px-4 ${hideTitle ? 'h-14 border-b border-line' : 'pt-5 pb-3'}`}>
          <h2 id={titleId} className={hideTitle ? 'sr-only' : 'text-[17px] font-bold flex-1'}>{title}</h2>
          {hideTitle && <span className="flex-1" />}
          <button type="button" onClick={onClose} aria-label="סגירה" className="size-10 -me-2 inline-flex items-center justify-center rounded-md text-ink-2 hover:bg-hover hover:text-ink">
            <X size={20} aria-hidden />
          </button>
        </div>
        <div className="flex-1 min-h-0 scroll-area">{children}</div>
        {footer && <div className="shrink-0 border-t border-line px-5 max-sm:px-4 py-3 pb-[max(12px,env(safe-area-inset-bottom))] flex flex-wrap gap-2 items-center">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
};

export default Dialog;
