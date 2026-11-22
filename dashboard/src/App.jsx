import React, { useEffect, useState } from 'react';
import { KeyRound } from 'lucide-react';
import JobDashboard from './components/JobDashboard';
import { UNAUTHORIZED_EVENT, getApiToken, setApiToken } from './services/taskService';

// השרת דורש API_TOKEN והטוקן חסר / שגוי: מבקשים אותו פעם אחת ושומרים בדפדפן
const TokenPrompt = ({ hadToken }) => {
  const [value, setValue] = useState('');
  const save = (e) => {
    e.preventDefault();
    if (!value.trim()) return;
    setApiToken(value.trim());
    window.location.reload();
  };
  return (
    <div className="min-h-dvh flex items-center justify-center bg-page text-ink p-4" dir="rtl">
      <form onSubmit={save} className="bg-surface rounded-lg shadow-[0_0_0_1px_var(--line)] p-7 max-sm:p-5 w-full max-w-md flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <span className="size-9 rounded-lg bg-ink text-page inline-flex items-center justify-center"><KeyRound size={18} aria-hidden /></span>
          <h1 className="text-xl font-bold">כניסה ל-JobMatch</h1>
        </div>
        {hadToken && (
          <p role="alert" className="text-[13px] px-3 py-2 rounded-md bg-danger-soft">הטוקן השמור נדחה על ידי השרת. הזן אותו מחדש.</p>
        )}
        <label htmlFor="api-token" className="flex flex-col gap-1.5 text-[13px] text-ink-2">
          ה-API_TOKEN שהוגדר בשרת. הוא נשמר רק בדפדפן הזה.
          <input
            id="api-token"
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="w-full h-11 rounded-md border border-line-strong bg-surface px-3.5 text-ink focus:outline-2 focus:outline-accent focus:outline-offset-1"
            placeholder="API token"
            autoComplete="current-password"
            autoFocus
            dir="ltr"
          />
        </label>
        <button type="submit" className="h-11 rounded-md font-semibold bg-ink text-ink-inverse hover:opacity-90 disabled:opacity-45" disabled={!value.trim()}>
          כניסה
        </button>
      </form>
    </div>
  );
};

function App() {
  const [unauthorized, setUnauthorized] = useState(false);

  useEffect(() => {
    const onUnauthorized = () => setUnauthorized(true);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  if (unauthorized) return <TokenPrompt hadToken={Boolean(getApiToken())} />;
  return <JobDashboard />;
}

export default App;
