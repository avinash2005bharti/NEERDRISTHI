import { useState, useEffect } from 'react';
import { appStore, AppState } from '../stores/appState';

export function useAppState(): AppState {
  const [state, setState] = useState<AppState>(appStore.getState());

  useEffect(() => {
    return appStore.subscribe(() => {
      setState(appStore.getState());
    });
  }, []);

  return state;
}
