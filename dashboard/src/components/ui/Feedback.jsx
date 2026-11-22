import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ToastContext } from '../../hooks/useToast';
import { AlertCircle, Check, Info, PauseCircle } from 'lucide-react';

// ---------- Toast: אישור שקט לפעולות (במקום alert) ----------

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);
  const seq = useRef(0);
  const push = useCallback((text, tone = 'neutral') => {
    seq.current += 1;
    const id = seq.current;
    setToasts((prev) => [...prev.slice(-2), { id, text, tone }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), tone === 'danger' ? 6000 : 3200);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div
        aria-live="polite"
        className="fixed z-[120] bottom-[calc(76px+env(safe-area-inset-bottom))] lg:bottom-6 inset-x-0 flex flex-col items-center gap-2 pointer-events-none px-4"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pop-in pointer-events-auto max-w-md flex items-center gap-2.5 rounded-md px-4 py-2.5 text-sm shadow-overlay ${t.tone === 'danger' ? 'bg-danger-soft text-ink' : 'bg-ink text-ink-inverse'}`}
          >
            {t.tone === 'danger' ? <AlertCircle size={16} className="text-danger shrink-0" aria-hidden /> : <Check size={16} className="shrink-0" aria-hidden />}
            <span>{t.text}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

// ---------- Notice: הודעת מערכת רגועה מתחת לסרגל העליון ----------
const NOTICE_TONES = {
  info: { cls: 'bg-accent-soft', icon: Info, iconCls: 'text-accent' },
  warn: { cls: 'bg-warn-soft', icon: PauseCircle, iconCls: 'text-warn' },
  danger: { cls: 'bg-danger-soft', icon: AlertCircle, iconCls: 'text-danger' },
};
export const Notice = ({ tone = 'info', children, action, role = 'status' }) => {
  const t = NOTICE_TONES[tone];
  const Icon = t.icon;
  return (
    <div role={role} className={`state-fade flex items-start sm:items-center gap-2.5 px-4 sm:px-7 py-2.5 text-[13px] ${t.cls}`}>
      <Icon size={16} className={`${t.iconCls} shrink-0 mt-0.5 sm:mt-0`} aria-hidden />
      <span className="flex-1 min-w-0">{children}</span>
      {action}
    </div>
  );
};

// ---------- EmptyState ----------
export const EmptyState = ({ icon: Icon, tone = 'neutral', title, children, action, className = '' }) => (
  <div className={`flex flex-col items-center justify-center text-center gap-3 px-6 py-12 ${className}`}>
    {Icon && (
      <span className={`size-12 rounded-full inline-flex items-center justify-center ${tone === 'go' ? 'bg-go-soft text-go' : 'bg-sunken text-ink-2'}`}>
        <Icon size={22} aria-hidden />
      </span>
    )}
    <h3 className="text-[17px] font-bold">{title}</h3>
    {children && <p className="text-ink-2 max-w-[38ch] leading-relaxed">{children}</p>}
    {action}
  </div>
);

// ---------- Menu: תפריט נפתח קטן, נסגר ב-Esc / קליק בחוץ ----------
export const Menu = ({ label, trigger, children, align = 'end', placement = 'down', triggerClassName = '' }) => {
  const [open, setOpen] = useState(false);
  const root = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (!root.current?.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', onDown);
    document.addEventListener('keydown', onKey);
    const first = root.current?.querySelector('[role="menuitem"]');
    first?.focus();
    return () => {
      document.removeEventListener('pointerdown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);
  const onMenuKey = (e) => {
    if (!['ArrowDown', 'ArrowUp'].includes(e.key)) return;
    e.preventDefault();
    const items = [...root.current.querySelectorAll('[role="menuitem"]')];
    const i = items.indexOf(document.activeElement);
    const next = e.key === 'ArrowDown' ? (i + 1) % items.length : (i - 1 + items.length) % items.length;
    items[next]?.focus();
  };
  return (
    <div ref={root} className="relative" onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={label}
        onClick={() => setOpen((o) => !o)}
        className={triggerClassName}
      >
        {trigger}
      </button>
      {open && (
        <div
          role="menu"
          aria-label={label}
          onKeyDown={onMenuKey}
          className={`pop-in absolute z-50 ${placement === 'up' ? 'bottom-full mb-1.5' : 'top-full mt-1.5'} min-w-56 bg-surface rounded-[10px] shadow-overlay py-1 ${align === 'end' ? 'end-0' : 'start-0'}`}
        >
          {typeof children === 'function' ? children(() => setOpen(false)) : children}
        </div>
      )}
    </div>
  );
};

export const MenuItem = ({ onSelect, close, children, hint, tone, icon: Icon, current = false }) => (
  <button
    type="button"
    role="menuitem"
    onClick={() => { close?.(); onSelect?.(); }}
    className={`w-full text-start px-3.5 py-2 flex items-start gap-2.5 hover:bg-hover focus:bg-hover outline-none ${current ? 'bg-accent-soft' : ''}`}
  >
    {Icon && <Icon size={16} className={`mt-0.5 shrink-0 ${tone === 'danger' ? 'text-danger' : 'text-ink-2'}`} aria-hidden />}
    <span className="flex flex-col">
      <span className={`font-medium ${tone === 'danger' ? 'text-danger' : current ? 'text-accent' : 'text-ink'}`}>{children}</span>
      {hint && <span className="text-xs text-ink-3">{hint}</span>}
    </span>
  </button>
);
