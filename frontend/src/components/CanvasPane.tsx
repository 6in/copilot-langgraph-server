// frontend/src/components/CanvasPane.tsx
// Canvas editor/preview pane with deploy functionality.
// Phase 15: right-side panel rendered conditionally in ChatApp when canvasApp state is non-null.
// Security: iframe sandbox="allow-scripts allow-forms" only — NO allow-same-origin (XSS prevention, T-15-08).

import { useState, useEffect, useRef, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import { useCurrentTheme } from '../contexts/ThemeContext';
import type { CanvasAppInfo } from '../types';
import { postIframeRpc, streamJob, getJob } from '../api/client';

interface CanvasPaneProps {
  canvasApp: CanvasAppInfo;
  isSaving: boolean;
  isDeploying: boolean;
  deployUrl: string | null;
  deployError: string | null;
  onSave: (appId: string, html: string) => void;
  onDeploy: (appId: string) => void;
  onClose: () => void;
  style?: React.CSSProperties;
}

type TabId = 'editor' | 'preview';

export function CanvasPane({
  canvasApp,
  isSaving,
  isDeploying,
  deployUrl,
  deployError,
  onSave,
  onDeploy,
  onClose,
  style,
}: CanvasPaneProps) {
  const theme = useCurrentTheme();
  const monacoTheme = theme === 'dark' ? 'vs-dark' : 'vs';

  const [activeTab, setActiveTab] = useState<TabId>('editor');
  const [htmlContent, setHtmlContent] = useState(canvasApp.html);

  // VITE_APP_BASE is baked in at build time (e.g. '/orochi'); strip trailing slash.
  const appBase = (import.meta.env.VITE_APP_BASE as string ?? '').replace(/\/$/, '');

  // D-19: iframeRef for postMessage reply target
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Sync htmlContent when canvasApp.html changes (e.g. after save)
  useEffect(() => {
    setHtmlContent(canvasApp.html);
  }, [canvasApp.html]);

  // D-01: postMessage handler for iframe JSON-RPC bridge
  const handleIframeMessage = useCallback(async (e: MessageEvent) => {
    // D-02: Origin validation
    // Deployed apps at /apps/{id}/ share window.location.origin.
    // srcDoc preview iframe has origin 'null' (string) — allow both.
    if (e.origin !== window.location.origin && e.origin !== 'null') return;

    // JSON-RPC format check (T-18-10)
    const msg = e.data as Record<string, unknown>;
    if (!msg || typeof msg !== 'object' || msg.jsonrpc !== '2.0') return;

    const { id, method, params } = msg as { id: string; method: string; params?: Record<string, unknown> };
    if (!id || !method) return;

    try {
      // D-04: POST /api/iframe-rpc to enqueue job
      const { job_id } = await postIframeRpc(id, method, params);

      // D-04: SSE で完了を待つ
      const result = await new Promise<string>((resolve, reject) => {
        const es = streamJob(job_id);

        const timer = setTimeout(() => {
          es.close();
          reject(new Error('RPC timeout'));
        }, 60000);

        es.onmessage = async (ev: MessageEvent) => {
          try {
            const event = JSON.parse(ev.data as string) as { status: string };
            if (event.status === 'done') {
              clearTimeout(timer);
              es.close();
              const job = await getJob(job_id);
              resolve(job.result ?? '{"result":false,"error":"No result"}');
            }
            // status === 'thinking' → keep waiting
          } catch {
            // Malformed SSE — ignore, keep listening
          }
        };

        es.onerror = () => {
          clearTimeout(timer);
          es.close();
          reject(new Error('SSE connection failed'));
        };
      });

      // Parse result and send back to iframe
      let parsed: unknown;
      try {
        parsed = JSON.parse(result);
      } catch {
        parsed = { result: false, error: 'Invalid response format' };
      }

      // D-05: Return with matching JSON-RPC id
      // targetOrigin '*' required for srcDoc iframe (null origin) — T-18-11 accepted risk
      iframeRef.current?.contentWindow?.postMessage(
        { jsonrpc: '2.0', id, ...((parsed && typeof parsed === 'object') ? parsed : { result: parsed }) },
        '*'
      );
    } catch (err) {
      // Send error back to iframe
      iframeRef.current?.contentWindow?.postMessage(
        { jsonrpc: '2.0', id, result: false, error: err instanceof Error ? err.message : 'Unknown error' },
        '*'
      );
    }
  }, []);

  // D-01: Register/unregister postMessage listener
  useEffect(() => {
    window.addEventListener('message', handleIframeMessage);
    return () => window.removeEventListener('message', handleIframeMessage);
  }, [handleIframeMessage]);

  const focusVisibleStyle = `
    button:focus-visible {
      outline: 2px solid #7c6ff7;
      outline-offset: 2px;
    }
  `;

  const tabButtonBase: React.CSSProperties = {
    padding: '0 16px',
    height: '36px',
    border: 'none',
    cursor: 'pointer',
    fontSize: '0.875rem',
    fontWeight: 600,
    transition: 'background 0.1s',
    flexShrink: 0,
  };

  const tabActive: React.CSSProperties = {
    ...tabButtonBase,
    background: '#ffffff',
    borderBottom: '2px solid #7c6ff7',
    color: '#333333',
  };

  const tabInactive: React.CSSProperties = {
    ...tabButtonBase,
    background: '#f0f0f0',
    borderBottom: '2px solid transparent',
    color: '#666666',
  };

  return (
    <div
      style={{
        minWidth: '320px',
        width: '40%',
        display: 'flex',
        flexDirection: 'column',
        borderLeft: '1px solid #d1dbe3',
        background: '#ffffff',
        flexShrink: 0,
        overflow: 'hidden',
        ...style,
      }}
    >
      <style>{focusVisibleStyle}</style>

      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '0 12px',
          height: '48px',
          borderBottom: '1px solid #d1dbe3',
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontSize: '0.875rem',
            fontWeight: 600,
            color: '#333333',
            flex: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {canvasApp.name}
        </span>

        {/* Deploy button */}
        <button
          onClick={() => onDeploy(canvasApp.app_id)}
          disabled={isDeploying}
          style={{
            background: '#7c6ff7',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            height: '36px',
            padding: '0 14px',
            fontSize: '0.875rem',
            fontWeight: 600,
            cursor: isDeploying ? 'not-allowed' : 'pointer',
            opacity: isDeploying ? 0.7 : 1,
            flexShrink: 0,
          }}
        >
          {isDeploying ? 'Deploying...' : 'Deploy'}
        </button>

        {/* Close button */}
        <button
          onClick={onClose}
          aria-label="Close canvas pane"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: '#666666',
            fontSize: '1.1rem',
            lineHeight: 1,
            padding: '4px 6px',
            borderRadius: '4px',
            flexShrink: 0,
          }}
        >
          ×
        </button>
      </div>

      {/* Deploy result */}
      {(deployUrl || deployError) && (
        <div
          style={{
            padding: '4px 12px',
            borderBottom: '1px solid #d1dbe3',
            flexShrink: 0,
            background: '#fafafa',
          }}
        >
          {deployUrl && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <a
                href={appBase + deployUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: '0.75rem', color: '#666666' }}
              >
                Open app
              </a>
              <button
                onClick={() => navigator.clipboard.writeText(window.location.origin + appBase + deployUrl)}
                style={{
                  background: 'none',
                  border: '1px solid #d1dbe3',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  color: '#666666',
                  padding: '1px 6px',
                }}
              >
                Copy URL
              </button>
            </div>
          )}
          {deployError && (
            <div role="alert" style={{ color: '#e05252', fontSize: '0.75rem' }}>
              Deploy failed. Please try again.
            </div>
          )}
        </div>
      )}

      {/* Tab bar */}
      <div
        role="tablist"
        style={{
          display: 'flex',
          borderBottom: '1px solid #d1dbe3',
          flexShrink: 0,
          background: '#f0f0f0',
        }}
      >
        <button
          role="tab"
          aria-selected={activeTab === 'editor'}
          aria-controls="canvas-editor-panel"
          id="canvas-editor-tab"
          style={activeTab === 'editor' ? tabActive : tabInactive}
          onClick={() => setActiveTab('editor')}
        >
          Editor
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'preview'}
          aria-controls="canvas-preview-panel"
          id="canvas-preview-tab"
          style={activeTab === 'preview' ? tabActive : tabInactive}
          onClick={() => setActiveTab('preview')}
        >
          Preview
        </button>
      </div>

      {/* Editor panel */}
      <div
        role="tabpanel"
        id="canvas-editor-panel"
        aria-labelledby="canvas-editor-tab"
        style={{
          display: activeTab === 'editor' ? 'flex' : 'none',
          flexDirection: 'column',
          flex: 1,
          overflow: 'hidden',
        }}
      >
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          <Editor
            height="100%"
            width="100%"
            language="html"
            value={htmlContent}
            theme={monacoTheme}
            onChange={(val) => setHtmlContent(val ?? '')}
            options={{
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              fontSize: 13,
              lineNumbers: 'on',
              folding: true,
              padding: { top: 8, bottom: 8 },
              automaticLayout: true,
            }}
          />
        </div>
        <div
          style={{
            padding: '8px 12px',
            borderTop: '1px solid #d1dbe3',
            flexShrink: 0,
            display: 'flex',
            justifyContent: 'flex-end',
            background: '#ffffff',
          }}
        >
          <button
            onClick={() => onSave(canvasApp.app_id, htmlContent)}
            disabled={isSaving}
            style={{
              border: '1px solid #d1dbe3',
              background: 'none',
              height: '32px',
              padding: '0 14px',
              borderRadius: '6px',
              fontSize: '0.875rem',
              cursor: isSaving ? 'not-allowed' : 'pointer',
              color: '#333333',
              opacity: isSaving ? 0.6 : 1,
            }}
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Preview panel */}
      <div
        role="tabpanel"
        id="canvas-preview-panel"
        aria-labelledby="canvas-preview-tab"
        style={{
          display: activeTab === 'preview' ? 'flex' : 'none',
          flex: 1,
          overflow: 'hidden',
        }}
      >
        <iframe
          ref={iframeRef}
          srcDoc={htmlContent}
          sandbox="allow-scripts allow-forms"
          title="Canvas app preview"
          style={{ width: '100%', height: '100%', border: 'none' }}
        />
      </div>
    </div>
  );
}
