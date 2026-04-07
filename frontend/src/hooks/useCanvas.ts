// frontend/src/hooks/useCanvas.ts
// Canvas app state management hook.

import { useCallback, useState } from 'react';
import { updateCanvasApp, deployCanvasApp, getCanvasAppByThread } from '../api/client';
import type { CanvasAppInfo } from '../types';

interface UseCanvasReturn {
  canvasApp: CanvasAppInfo | null;
  setCanvasApp: (app: CanvasAppInfo | null) => void;
  isSaving: boolean;
  isDeploying: boolean;
  deployUrl: string | null;
  deployError: string | null;
  saveCanvas: (appId: string, html: string) => Promise<void>;
  deployCanvas: (appId: string) => Promise<string>;
  dismissCanvas: () => void;
  loadCanvasForThread: (threadId: string) => Promise<void>;
}

export function useCanvas(): UseCanvasReturn {
  const [canvasApp, setCanvasApp] = useState<CanvasAppInfo | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployUrl, setDeployUrl] = useState<string | null>(null);
  const [deployError, setDeployError] = useState<string | null>(null);

  const saveCanvas = useCallback(async (appId: string, html: string) => {
    setIsSaving(true);
    try {
      const updated = await updateCanvasApp(appId, html);
      setCanvasApp(updated);
    } finally {
      setIsSaving(false);
    }
  }, []);

  const deployCanvas = useCallback(async (appId: string): Promise<string> => {
    setIsDeploying(true);
    setDeployError(null);
    try {
      const res = await deployCanvasApp(appId);
      setDeployUrl(res.url);
      if (canvasApp) {
        setCanvasApp({ ...canvasApp, deployed: true, deployed_at: new Date().toISOString() });
      }
      return res.url;
    } catch {
      setDeployError('Deploy failed. Please try again.');
      throw new Error('Deploy failed');
    } finally {
      setIsDeploying(false);
    }
  }, [canvasApp]);

  const dismissCanvas = useCallback(() => {
    setCanvasApp(null);
    setDeployUrl(null);
    setDeployError(null);
  }, []);

  const loadCanvasForThread = useCallback(async (threadId: string) => {
    setDeployUrl(null);
    setDeployError(null);
    try {
      const apps = await getCanvasAppByThread(threadId);
      setCanvasApp(apps.length > 0 ? apps[0] : null);
    } catch {
      setCanvasApp(null);
    }
  }, []);

  return { canvasApp, setCanvasApp, isSaving, isDeploying, deployUrl, deployError, saveCanvas, deployCanvas, dismissCanvas, loadCanvasForThread };
}
