import React, { useState, useMemo } from 'react';
import { Briefcase } from 'lucide-react';
import JobModal from '../JobCard/JobModal';
import JobStats from './JobStats';
import JobTableRow from './JobTableRow';

export const AppliedJobsTable = ({ jobs, onUpdateStatus, onRowClick }) => {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-right border-collapse">
          <thead>
            <tr className="bg-slate-50/70 text-slate-500 font-black text-xs uppercase tracking-wider border-b border-slate-200">
              <th className="px-8 py-6 text-right">פרטי המשרה</th>
              <th className="px-8 py-6 text-center">תאריך הגשה</th>
              <th className="px-8 py-6 text-center">ציון התאמה</th>
              <th className="px-8 py-6 text-center">סטטוס נוכחי</th>
              <th className="px-8 py-6 text-left">ניהול פעולות</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {jobs.map((job) => (
              <JobTableRow 
                key={job.url} 
                job={job} 
                onUpdateStatus={onUpdateStatus} 
                onRowClick={onRowClick} 
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const AppliedJobsTab = ({ jobs, onRemove, onUpdateStatus, onRetry }) => {
  const [selectedJob, setSelectedJob] = useState(null);
  
  // נתונים סטטיסטיים לראש העמוד
  const stats = useMemo(() => ({
    total: jobs.length,
    applied: jobs.filter(j => j.application_status === 'applied').length,
    rejected: jobs.filter(j => j.application_status === 'rejected').length,
  }), [jobs]);

  if (jobs.length === 0) {
    return (
      <div className="text-center py-24 bg-white rounded-3xl border-2 border-dashed border-slate-200 animate-in fade-in duration-500">
        <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6">
          <Briefcase className="w-10 h-10 text-slate-200" />
        </div>
        <h3 className="text-2xl font-black text-slate-800 mb-2">עדיין לא נשלחו משרות</h3>
        <p className="text-slate-500 max-w-md mx-auto">ברגע שתסמן משרות כ"נשלחו", הן יופיעו כאן עם כל הפרטים והניתוח</p>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in duration-500">
      <JobStats stats={stats} />

      <AppliedJobsTable 
        jobs={jobs} 
        onUpdateStatus={onUpdateStatus}
        onRowClick={setSelectedJob} 
      />

      {selectedJob && (
        <JobModal
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
          onAction={onRemove}
          onUpdateStatus={onUpdateStatus}
          onRetry={onRetry}
        />
      )}
    </div>
  );
};

export default AppliedJobsTab;