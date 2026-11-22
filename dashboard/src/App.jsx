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
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6" dir="rtl">
      <form onSubmit={save} className="bg-white rounded-3xl shadow-xl border border-slate-100 p-8 w-full max-w-md flex flex-col gap-4">
        <div className="flex items-center gap-3 text-slate-800">
          <KeyRound className="text-blue-600" />
          <h1 className="text-xl font-black">כניסה ל-JobMatch</h1>
        </div>
        <p className="text-slate-500 text-sm">
          {hadToken ? 'הטוקן השמור נדחה על ידי השרת. ' : ''}
          הזן את ה-API_TOKEN שהוגדר בשרת. הוא נשמר רק בדפדפן הזה.
        </p>
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500/20"
          placeholder="API token"
          autoFocus
          dir="ltr"
        />
        <button type="submit" className="py-3 rounded-xl font-bold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50" disabled={!value.trim()}>
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
