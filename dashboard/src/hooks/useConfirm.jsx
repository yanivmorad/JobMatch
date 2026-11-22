import React, { useCallback, useRef, useState } from 'react';
import Dialog from '../components/ui/Dialog';
import Button from '../components/ui/Button';

// אישור בתוך הדף (במקום window.confirm): const [confirm, element] = useConfirm()
export const useConfirm = () => {
  const [state, setState] = useState(null);
  const resolver = useRef(null);
  const confirm = useCallback((opts) => new Promise((resolve) => {
    resolver.current = resolve;
    setState(opts);
  }), []);
  const close = (answer) => {
    resolver.current?.(answer);
    resolver.current = null;
    setState(null);
  };
  const confirmRef = useRef(null);
  const element = (
    <Dialog
      open={Boolean(state)}
      onClose={() => close(false)}
      title={state?.title || ''}
      size="sm"
      initialFocusRef={confirmRef}
      footer={state && (
        <>
          <Button ref={confirmRef} variant={state.danger ? 'dangerSolid' : 'primary'} onClick={() => close(true)}>
            {state.confirmLabel || 'אישור'}
          </Button>
          <Button variant="ghost" onClick={() => close(false)}>ביטול</Button>
        </>
      )}
    >
      {state?.body && <p className="px-5 max-sm:px-4 pb-4 text-ink-2 leading-relaxed">{state.body}</p>}
    </Dialog>
  );
  return [confirm, element];
};
