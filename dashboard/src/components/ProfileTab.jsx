import React, { useState, useEffect } from 'react';
import { taskService } from '../services/taskService';
import { User, FileText, Save, RefreshCw, AlertCircle } from 'lucide-react';

const ProfileTab = () => {
  const [resume, setResume] = useState('');
  const [context, setContext] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  // טעינת הנתונים הקיימים
  useEffect(() => {
    fetchProfileData();
  }, []);

  const fetchProfileData = async () => {
    try {
      setLoading(true);
      const [resumeData, contextData] = await Promise.all([
        taskService.getResume(),
        taskService.getContext()
      ]);
      setResume(resumeData.content || '');
      setContext(contextData.content || '');
    } catch (error) {
      console.error('Error loading profile:', error);
      setMessage({ type: 'error', text: 'שגיאה בטעינת הנתונים' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await Promise.all([
        taskService.saveResume(resume),
        taskService.saveContext(context)
      ]);
      setMessage({ type: 'success', text: '✅ השינויים נשמרו בהצלחה!' });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      console.error('Error saving profile:', error);
      setMessage({ type: 'error', text: '❌ שגיאה בשמירת הנתונים' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-3 rounded-lg">
            <User className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-800">ניהול פרופיל</h2>
            <p className="text-gray-500 text-sm">ערוך את קורות החיים והקשר האישי שלך</p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-green-600 hover:bg-green-700 text-white px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
        >
          {saving ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              שומר...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              שמור שינויים
            </>
          )}
        </button>
      </div>

      {/* Message */}
      {message && (
        <div className={`p-4 rounded-lg flex items-center gap-2 ${
          message.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          <AlertCircle className="w-5 h-5" />
          {message.text}
        </div>
      )}

      {/* Resume Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4 pb-3 border-b">
          <FileText className="w-5 h-5 text-blue-600" />
          <h3 className="font-bold text-lg text-gray-800">קורות חיים (Resume)</h3>
        </div>
        <textarea
          value={resume}
          onChange={(e) => setResume(e.target.value)}
          className="w-full h-96 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm resize-none"
          placeholder="הדבק כאן את קורות החיים שלך..."
          dir="ltr"
        />
        <p className="text-xs text-gray-500 mt-2">
          💡 טיפ: קורות החיים משמשים את ה-AI לניתוח התאמה למשרות. כלול כישורים, ניסיון והשכלה.
        </p>
      </div>

      {/* Context Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4 pb-3 border-b">
          <FileText className="w-5 h-5 text-purple-600" />
          <h3 className="font-bold text-lg text-gray-800">הקשר אישי (Personal Context)</h3>
        </div>
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          className="w-full h-64 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 font-mono text-sm resize-none"
          placeholder="הוסף הקשר נוסף: מטרות קריירה, העדפות, אסטרטגיה..."
          dir="ltr"
        />
        <p className="text-xs text-gray-500 mt-2">
          💡 טיפ: הקשר אישי עוזר ל-AI להבין את המטרות שלך ולהתאים את ההמלצות בהתאם.
        </p>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-bold text-blue-900 mb-2">📌 חשוב לדעת:</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• השינויים ישפיעו על כל הניתוחים החדשים שיתבצעו מעכשיו</li>
          <li>• משרות שכבר נותחו לא יעודכנו אוטומטית</li>
          <li>• הקבצים נשמרים בתיקיית data/ בשרת</li>
        </ul>
      </div>
    </div>
  );
};

export default ProfileTab;
