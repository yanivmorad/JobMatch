import React from 'react';
import { Clock, Download, CheckCircle, Sparkles, AlertCircle, Loader2 } from 'lucide-react';

const StatusBadge = ({ status }) => {
  const config = {
    pending: { 
      style: "bg-gray-100 text-gray-500",
      label: "ממתין לתור",
      icon: Clock
    },
    scraping: { 
      style: "bg-blue-50 text-blue-600",
      label: "סורק תוכן",
      icon: Loader2,
      animate: "animate-spin"
    },
    scraped: { 
      style: "bg-indigo-50 text-indigo-600",
      label: "תוכן נאסף",
      icon: CheckCircle
    },
    analyzing: { 
      style: "bg-purple-50 text-purple-600",
      label: "מנתח AI",
      icon: Sparkles,
      animate: "animate-pulse"
    },
    completed: { 
      style: "bg-emerald-50 text-emerald-600",
      label: "ניתוח הושלם",
      icon: CheckCircle
    },
    failed: { 
      style: "bg-rose-50 text-rose-600",
      label: "שגיאה בסריקה",
      icon: AlertCircle
    },
  };

  const current = config[status] || config.pending;
  const Icon = current.icon;

  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider ${current.style} transition-all duration-300`}>
      <Icon className={`w-3 h-3 ${current.animate || ''}`} />
      <span>{current.label}</span>
    </span>
  );
};

export default StatusBadge;
