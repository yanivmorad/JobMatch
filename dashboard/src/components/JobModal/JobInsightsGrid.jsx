import React from 'react';
import { AlertCircle, TrendingUp } from 'lucide-react';

const JobInsightsGrid = ({ job }) => {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="bg-gradient-to-br from-rose-50 to-white rounded-3xl p-6 border border-rose-100 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <AlertCircle size={18} className="text-rose-600" />
          <h3 className="font-black text-base text-slate-900">נקודות תורפה</h3>
        </div>
        <ul className="space-y-2.5">
          {job.showstoppers?.map((item, i) => (
            <li key={i} className="flex gap-2 items-start text-sm text-slate-700 leading-relaxed">
              <span className="text-rose-500 font-bold">•</span> {item}
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-gradient-to-br from-indigo-50 to-white rounded-3xl p-6 border border-indigo-100 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <TrendingUp size={18} className="text-indigo-600" />
          <h3 className="font-black text-base text-slate-900">פערי ידע</h3>
        </div>
        <ul className="space-y-2.5">
          {job.gap_analysis?.map((item, i) => (
            <li key={i} className="flex gap-2 items-start text-sm text-slate-700 leading-relaxed">
              <span className="text-indigo-500 font-bold">•</span> {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default JobInsightsGrid;
