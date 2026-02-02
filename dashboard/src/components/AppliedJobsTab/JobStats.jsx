import React from 'react';
import { Briefcase } from 'lucide-react';

const JobStats = ({ stats }) => {
  return (
    <div className="bg-gradient-to-br from-amber-50/50 via-orange-50/30 to-rose-50/20 rounded-[2.5rem] border border-amber-200/50 p-8 shadow-[0_12px_40px_-15px_rgba(251,146,60,0.15)] mb-8">
      <div className="flex justify-between items-start">
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-amber-400 to-orange-500 rounded-3xl flex items-center justify-center shadow-lg shadow-amber-100">
              <Briefcase size={24} className="text-white" />
            </div>
            <div>
              <h2 className="text-3xl font-black text-slate-800 tracking-tight">
                משרות בתהליך
              </h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-orange-600 font-black text-xl">{stats.total}</span>
                <span className="text-slate-500 text-sm">משרות פעילות</span>
              </div>
            </div>
          </div>
          
          <div className="bg-white/60 rounded-2xl p-4 border border-amber-100 backdrop-blur-sm">
            <p className="text-slate-700 font-medium leading-relaxed">
              <span className="text-orange-500">💡</span> טיפ: עקוב אחרי ההתקדמות שלך ועדכן את הסטטוס של כל משרה
            </p>
          </div>
        </div>
        
        {/* אלמנט דקורטיבי */}
        <div className="hidden lg:flex items-center gap-3">
          <div className="w-3 h-3 bg-amber-400 rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-orange-400 rounded-full animate-pulse delay-75"></div>
          <div className="w-3 h-3 bg-rose-400 rounded-full animate-pulse delay-150"></div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(JobStats);
