import React from 'react';
import { Building2, MapPin, Info, Target, TrendingUp, Calendar, ChevronDown } from 'lucide-react';
import JobModal from './JobModal';
import { STATUS_CONFIG } from '../../constants/statusConfig';

const JobCard = ({ job, onAction, onDelete, onUpdateStatus, onRetry }) => {
  const [isModalOpen, setIsModalOpen] = React.useState(false);

  const currentStatus = job.application_status || 'pending';
  const statusInfo = STATUS_CONFIG[currentStatus];

  const handleStatusChange = (e) => {
    e.stopPropagation();
    onUpdateStatus(job.url, e.target.value);
  };

  // פונקציה לבחירת צבע טקסט בלבד לפי הציון
  const getScoreColorClass = (score) => {
    if (score >= 85) return 'text-emerald-600';
    if (score >= 70) return 'text-amber-600';
    return 'text-rose-600';
  };

  return (
    <>
      <div
        onClick={() => setIsModalOpen(true)}
        className="group bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md hover:border-blue-400 transition-all duration-300 cursor-pointer flex flex-col shadow-sm h-full min-h-[180px]"
        dir="rtl"
      >
        {/* שורת כותרת וציונים */}
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-lg font-semibold text-slate-800 line-clamp-1 group-hover:text-blue-600 transition-colors">
                {job.job_title || job.url}
              </h3>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-slate-600">
                <Building2 className="w-4 h-4 flex-shrink-0" />
                <span className="text-sm truncate">{job.company}</span>
              </div>
              
              {/* Status Badge */}
              <div 
                className="px-2 py-0.5 rounded text-[10px] font-bold transition-all border shrink-0"
                style={{ 
                  backgroundColor: statusInfo.bg, 
                  color: statusInfo.color,
                  borderColor: statusInfo.border
                }}
              >
                {statusInfo.label}
              </div>
            </div>
          </div>

          {/* ציונים זה ליד זה בצד שמאל */}
          <div className="flex items-center gap-3 mr-4">
            <div className="flex items-center gap-1.5">
              <Target className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span className={`text-base font-bold ${getScoreColorClass(job.suitability_score)}`}>
                {job.suitability_score}%
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-slate-400 flex-shrink-0" />
              <span className={`text-base font-bold ${getScoreColorClass(job.acceptance_probability)}`}>
                {job.acceptance_probability}%
              </span>
            </div>
          </div>
        </div>

        {/* תיאור המשרה - עם ריווח מהכותרת */}
        <div className="flex-1 mb-4 mt-2">
          {job.job_summary_hebrew ? (
            <p className="text-slate-600 text-sm leading-relaxed line-clamp-3">
              {job.job_summary_hebrew}
            </p>
          ) : (
            <p className="text-slate-400 text-sm italic">
              אין תקציר זמין
            </p>
          )}
        </div>

        {/* פוטר - תמיד נצמד לתחתית */}
        <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100 mt-auto">
          <div className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5" />
            <span>{job.location || 'מרחוק'}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5" />
            <span>
              {job.created_at ? new Date(job.created_at).toLocaleDateString('he-IL') : 'היום'}
            </span>
          </div>
        </div>
      </div>

      {isModalOpen && (
        <JobModal
          job={job}
          onClose={() => setIsModalOpen(false)}
          onAction={onAction}
          onDelete={() => onDelete(job)}
          onUpdateStatus={onUpdateStatus}
          onRetry={onRetry}
        />
      )}
    </>
  );
};

export default JobCard;