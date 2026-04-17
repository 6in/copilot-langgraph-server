// frontend/src/components/AuthPanel.tsx
// Device Flow UI: shows user_code + verification_uri, polls for completion.
// Device Flow UI: shows user_code + verification_uri, polls for completion.

import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export function AuthPanel() {
  const { authState, flowData, flowError, startFlow } = useAuth();
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!flowData) return;
    navigator.clipboard.writeText(flowData.user_code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
    window.open(flowData.verification_uri, '_blank');
  };

  return (
    <div className="auth-panel-root" style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      fontFamily: 'sans-serif',
      gap: '1rem',
      padding: '2rem',
    }}>
      <h2>Connect to GitHub Copilot</h2>

      {authState === 'expired' && (
        <p style={{ color: '#c0392b' }}>Session expired — please authenticate again.</p>
      )}

      {flowError && (
        <p style={{ color: '#c0392b' }}>{flowError}</p>
      )}

      {!flowData ? (
        <button
          onClick={startFlow}
          className="auth-start-btn"
          style={{
            padding: '0.75rem 1.5rem',
            fontSize: '1rem',
            cursor: 'pointer',
            borderRadius: '6px',
            border: '1px solid #ccc',
            background: '#24292e',
            color: '#fff',
          }}
        >
          Start GitHub Authentication
        </button>
      ) : (
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <p>Open the URL below and enter the code:</p>

          <a
            href={flowData.verification_uri}
            target="_blank"
            rel="noopener noreferrer"
            className="auth-link"
            style={{ fontSize: '1.1rem', color: '#0366d6' }}
          >
            {flowData.verification_uri}
          </a>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', justifyContent: 'center' }}>
            <span className="auth-device-code" style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              fontFamily: 'monospace',
              letterSpacing: '0.15em',
              background: '#f6f8fa',
              border: '1px solid #d0d7de',
              borderRadius: '6px',
              padding: '0.5rem 1rem',
            }}>
              {flowData.user_code}
            </span>
            <button
              onClick={handleCopy}
              className="auth-copy-btn"
              style={{
                padding: '0.5rem 1rem',
                cursor: 'pointer',
                borderRadius: '6px',
                border: '1px solid #ccc',
              }}
            >
              {copied ? 'Copied ✓' : 'Copy & Open'}
            </button>
          </div>

          <div className="auth-waiting-text" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#57606a' }}>
            <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⟳</span>
            <span>Waiting for authentication...</span>
          </div>
        </div>
      )}
    </div>
  );
}
