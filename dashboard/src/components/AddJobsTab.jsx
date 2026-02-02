import React, { useState, useMemo } from 'react';
import { useJobActions } from '../hooks/useJobActions';
import ManualFixModal from './AddJobsTab/ManualFixModal';
import SmartImportCard from './AddJobsTab/SmartImportCard';
import ManualInputCard from './AddJobsTab/ManualInputCard';
import AttentionRequiredList from './AddJobsTab/AttentionRequiredList';
import { Sparkles } from 'lucide-react';

const AddJobsTab = ({ pendingJobs, onJobAdded }) => {
  const [rawInput, setRawInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [textTitle, setTextTitle] = useState('');
  const [isFixModalOpen, setIsFixModalOpen] = useState(false);
  const [jobToFix, setJobToFix] = useState(null);

  const {
    submitStatus,
    duplicateJobs,
    setDuplicateJobs,
    handleUrlSubmit,
    handleTextSubmit,
    handleRescan,
    handleCancel,
    handleRetry,
    handleDismissDuplicate
  } = useJobActions(onJobAdded);

  const { activeQueue, failedJobs } = useMemo(() => {
    return {
      activeQueue: pendingJobs.filter(j => !['FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA'].includes(j.status)),
      failedJobs: pendingJobs.filter(j => ['FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA'].includes(j.status))
    };
  }, [pendingJobs]);

  return (
    <div className="w-full min-h-screen bg-slate-50/50" dir="rtl">
      <ManualFixModal 
        isOpen={isFixModalOpen}
        onClose={() => setIsFixModalOpen(false)}
        job={jobToFix}
        onSubmit={async (url, title, content) => {
          const success = await handleTextSubmit(content, title, url);
          if (success) {
            await handleCancel(url);
            setIsFixModalOpen(false);
          }
        }}
        isSubmitting={submitStatus === 'sending'}
      />

      <div className="max-w-[1600px] mx-auto w-full px-6 py-10 flex flex-col gap-10">
<section className="flex flex-col items-center text-center gap-4 mb-4">
 
  <div className="space-y-2">
    <h2 className="text-4xl md:text-5xl font-black text-slate-900 tracking-tight">
      מרכז <span className="text-blue-600">הזנת משרות</span>
    </h2>
    <div className="flex items-center justify-center gap-3">
      <span className="h-px w-12 bg-slate-200"></span>
      <p className="text-slate-500 text-lg font-medium">ניהול מקורות מידע ועיבוד AI חכם</p>
      <span className="h-px w-12 bg-slate-200"></span>
    </div>
  </div>
</section>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-10 items-start">
          <div className="xl:col-span-8 flex flex-col gap-10">
            
            <SmartImportCard 
              rawInput={rawInput}
              setRawInput={setRawInput}
              duplicateJobs={duplicateJobs}
              setDuplicateJobs={setDuplicateJobs}
              submitStatus={submitStatus}
              onSubmit={(parsedLinks) => handleUrlSubmit(parsedLinks, () => setRawInput(''))}
            />

            <ManualInputCard 
              textTitle={textTitle}
              setTextTitle={setTextTitle}
              textInput={textInput}
              setTextInput={setTextInput}
              submitStatus={submitStatus}
              onSubmit={(text, title) => handleTextSubmit(text, title, null, false, () => {
                setTextInput('');
                setTextTitle('');
              })}
            />
          </div>

          <AttentionRequiredList 
            failedJobs={failedJobs}
            duplicateJobs={duplicateJobs}
            handleRescan={handleRescan}
            handleDismissDuplicate={handleDismissDuplicate}
            handleRetry={handleRetry}
            handleCancel={handleCancel}
            setJobToFix={setJobToFix}
            setIsFixModalOpen={setIsFixModalOpen}
            activeQueue={activeQueue}
          />
        </div>
      </div>
    </div>
  );
};

export default AddJobsTab;