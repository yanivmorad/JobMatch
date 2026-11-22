import React, { useState } from 'react';
import { Check, Monitor, Moon, Sun } from 'lucide-react';
import { TABS } from '../../constants/navigation';
import { applyTheme, readTheme } from '../../utils/theme';

const Logo = () => (
  <span className="flex items-center gap-2.5">
    <span className="size-7 rounded-lg bg-ink inline-flex items-center justify-center">
      <Check size={16} strokeWidth={3} className="text-page" aria-hidden />
    </span>
    <span className="font-bold text-[17px] tracking-[-0.01em]" dir="ltr">JobMatch</span>
  </span>
);

// בחירת ערכת נושא: מערכת / בהיר / כהה (נשמר בדפדפן הזה בלבד)
const ThemeSwitch = () => {
  const [theme, setTheme] = useState(readTheme);
  const choose = (t) => {
    setTheme(t);
    applyTheme(t);
  };
  const opts = [
    { id: 'light', label: 'בהיר', icon: Sun },
    { id: 'system', label: 'לפי המערכת', icon: Monitor },
    { id: 'dark', label: 'כהה', icon: Moon },
  ];
  return (
    <div role="radiogroup" aria-label="ערכת נושא" className="flex items-center gap-0.5 p-0.5 rounded-md bg-sunken w-fit">
      {opts.map((o) => (
        <button
          key={o.id}
          type="button"
          role="radio"
          aria-checked={theme === o.id}
          aria-label={o.label}
          title={o.label}
          onClick={() => choose(o.id)}
          className={`size-8 inline-flex items-center justify-center rounded-[6px] ${theme === o.id ? 'bg-surface text-ink shadow-[0_0_0_1px_var(--line)]' : 'text-ink-3 hover:text-ink'}`}
        >
          <o.icon size={15} aria-hidden />
        </button>
      ))}
    </div>
  );
};

const Badge = ({ badge }) => {
  if (!badge) return null;
  if (badge.tone === 'danger') {
    return <span className="text-xs font-semibold text-danger num">{badge.text}</span>;
  }
  if (badge.tone === 'strong') {
    return <span className="num text-xs font-semibold bg-ink text-ink-inverse rounded-full px-2 leading-5">{badge.text}</span>;
  }
  return <span className="num text-xs text-ink-3">{badge.text}</span>;
};

// סרגל צד (דסקטופ, ≥1024px)
export const Rail = ({ activeTab, onNavigate, badges, footer }) => (
  <nav aria-label="ניווט ראשי" className="hidden lg:flex w-[232px] shrink-0 flex-col gap-1 px-3.5 py-5 border-e border-line h-dvh sticky top-0">
    <button type="button" onClick={() => onNavigate('dashboard')} className="px-2.5 pt-1 pb-5 w-fit rounded-md" aria-label="JobMatch, לסקירה">
      <Logo />
    </button>
    {TABS.map((t) => {
      const active = activeTab === t.id;
      return (
        <button
          key={t.id}
          type="button"
          onClick={() => onNavigate(t.id)}
          aria-current={active ? 'page' : undefined}
          className={`flex items-center gap-2.5 h-10 px-2.5 rounded-md text-start transition-colors ${active ? 'bg-surface text-ink font-semibold shadow-[0_0_0_1px_var(--line)]' : 'text-ink-2 hover:bg-hover hover:text-ink'}`}
        >
          <t.icon size={18} strokeWidth={1.9} aria-hidden />
          <span className="flex-1">{t.label}</span>
          <Badge badge={badges[t.id]} />
        </button>
      );
    })}
    <div className="mt-auto flex flex-col gap-3">
      {footer}
      <ThemeSwitch />
    </div>
  </nav>
);

// סרגל תחתון (נייד וטאבלט)
export const BottomNav = ({ activeTab, onNavigate, badges }) => (
  <nav
    aria-label="ניווט ראשי"
    className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-surface border-t border-line grid grid-cols-6 pb-[env(safe-area-inset-bottom)]"
  >
    {TABS.map((t) => {
      const active = activeTab === t.id;
      const badge = badges[t.id];
      return (
        <button
          key={t.id}
          type="button"
          onClick={() => onNavigate(t.id)}
          aria-current={active ? 'page' : undefined}
          className={`relative h-[60px] flex flex-col items-center justify-center gap-1 text-[11px] ${active ? 'text-ink font-semibold' : 'text-ink-2'}`}
        >
          <span className={`relative inline-flex items-center justify-center h-7 w-11 rounded-full transition-colors ${active ? 'bg-sunken' : ''}`}>
            <t.icon size={19} strokeWidth={active ? 2.2 : 1.8} aria-hidden />
            {badge?.tone === 'danger' && <span className="absolute top-0.5 end-1.5 size-2 rounded-full bg-danger-fill ring-2 ring-surface" aria-hidden />}
          </span>
          {t.label}
          {badge?.tone === 'danger' && <span className="sr-only">{badge.text}</span>}
        </button>
      );
    })}
  </nav>
);

