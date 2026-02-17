import React from 'react';
import { Clock, Download, CheckCircle, Sparkles, AlertCircle, Loader2 } from 'lucide-react';

const StatusBadge = ({ status }) => {
  const config = {
    NEW: { 
      style: "bg-gray-100 text-gray-500",
      label: "בתור",
      icon: Clock
    },
    PENDING_RESOLVE: { 
      style: "bg-amber-50 text-amber-600",
      label: "מפענח קישור",
      icon: Clock
    },
    RESOLVING: { 
      style: "bg-amber-100 text-amber-700",
      label: "בבדיקת כתובת",
      icon: Loader2,
      animate: "animate-pulse"
    },
    WAITING_FOR_SCRAPE: { 
      style: "bg-blue-50 text-blue-500",
      label: "ממתין לסריקה",
      icon: Clock
    },
    SCRAPING: { 
      style: "bg-blue-100 text-blue-600",
      label: "סורק תוכן",
      icon: Loader2,
      animate: "animate-pulse"
    },
    WAITING_FOR_AI: { 
      style: "bg-indigo-50 text-indigo-600",
      label: "ממתין ל-AI",
      icon: Sparkles
    },
    ANALYZING: { 
      style: "bg-purple-50 text-purple-600",
      label: "מנתח משרה",
      icon: Sparkles,
      animate: "animate-pulse"
    },
    COMPLETED: { 
      style: "bg-emerald-50 text-emerald-600",
      label: "ניתוח מושלם",
      icon: CheckCircle
    },
    FAILED_RESOLVE: { 
      style: "bg-rose-50 text-rose-600",
      label: "שגיאת זיהוי",
      icon: AlertCircle
    },
    FAILED_SCRAPE: { 
      style: "bg-rose-50 text-rose-600",
      label: "שגיאת סריקה",
      icon: AlertCircle
    },
    FAILED_ANALYSIS: { 
      style: "bg-rose-50 text-rose-600",
      label: "שגיאת ניתוח",
      icon: AlertCircle
    },
    NO_DATA: { 
      style: "bg-amber-50 text-amber-600",
      label: "אין מידע",
      icon: AlertCircle
    },
    DUPLICATE: { 
      style: "bg-amber-100 text-amber-700",
      label: "משרה כפולה (כבר קיימת במערכת)",
      icon: AlertCircle
    },
  };

  const current = config[status] || config.NEW;
  const Icon = current.icon;

  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider ${current.style} transition-all duration-300`}>
      <Icon className={`w-3 h-3 ${current.animate || ''}`} />
      <span>{current.label}</span>
    </span>
  );
};

export default StatusBadge;
