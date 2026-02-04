import React from 'react';
import { 
  Calendar, ExternalLink, Target, AlertCircle, Archive, Building2 
} from 'lucide-react';
import { formatTime } from '../../utils/dateHelpers';
import { getSuitabilityScoreStyle } from '../../utils/jobHelpers';
import StatusDropdown from './StatusDropdown';

const JobTableRow = ({ job, onUpdateStatus, onRowClick }) => {
  return (
    <tr 
      className="hover:bg-slate-50 transition-all duration-200 group cursor-pointer"
      onClick={() => onRowClick?.(job)}
    >
      <td className="px-8 py-7">
        <div className="flex flex-col gap-2">
          <span className="font-black text-slate-900 text-lg group-hover:text-blue-600 transition-colors">
            {job.job_title}
          </span>
          <span className="text-slate-500 text-sm font-medium flex items-center gap-2">
            <Building2 size={14} className="text-slate-400" />
            {job.company}
          </span>
          <a 
            href={job.url} 
            target="_blank" 
            rel="noopener noreferrer" 
            className="flex items-center gap-1.5 text-blue-600 text-xs font-black mt-1 hover:underline w-fit"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink size={12}/>
            צפייה במקור
          </a>
        </div>
      </td>
      <td className="px-8 py-7 text-center">
        <div className="inline-flex items-center gap-2 text-slate-600 text-sm font-medium bg-slate-50 px-3 py-1.5 rounded-full">
          <Calendar size={14} className="text-slate-400"/>
          {formatTime(job.updated_at || job.analyzed_at)}
        </div>
      </td>
      <td className="px-8 py-7 text-center">
        <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-black border ${getSuitabilityScoreStyle(job.suitability_score)}`}>
          <Target size={14} />
          {job.suitability_score}%
        </div>
      </td>
      <td className="px-8 py-7 text-center">
        <StatusDropdown 
          status={job.application_status} 
          onUpdateStatus={onUpdateStatus} 
          jobUrl={job.url} 
        />
      </td>
      <td className="px-8 py-7 text-left">
        <div className="flex items-center justify-end gap-3">
          {job.application_status !== 'rejected' && (
            <button 
              onClick={(e) => {
                e.stopPropagation();
                if (confirm('לסמן משרה זו כנדחה? פעולה זו תעדכן את הסטטוס.')) {
                  onUpdateStatus(job.url, 'rejected');
                }
              }}
              className="flex items-center gap-2 px-4 py-2.5 bg-rose-50 hover:bg-rose-100 text-rose-600 hover:text-rose-700 rounded-xl transition-all font-bold text-sm border border-rose-200"
              title="סמן כדחייה"
            >
              <AlertCircle size={16} />
              <span>דחייה</span>
            </button>
          )}
          <button 
            onClick={(e) => {
              e.stopPropagation();
              if (confirm('להעביר משרה לארכיון? היא תוסר מהרשימה אבל תשמר בהיסטוריה.')) {
                onUpdateStatus(job.url, job.application_status || 'not_relevant', true);
              }
            }}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 hover:bg-slate-100 text-slate-500 hover:text-slate-700 rounded-xl transition-all font-bold text-sm border border-slate-200"
            title="העבר לארכיון"
          >
            <Archive size={16} />
            <span>ארכיון</span>
          </button>
        </div>
      </td>
    </tr>
  );
};

export default React.memo(JobTableRow);
