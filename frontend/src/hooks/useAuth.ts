// frontend/src/hooks/useAuth.ts
// Device Flow auth state machine.
// Mirrors static/app.js lines 97-239.

import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { checkAuthStatus, startAuthFlow, pollAuthFlow, logout } from '../api/client';
import type { AuthStartResponse } from '../types';

export type AuthState = 'unknown' | 'authenticated' | 'unauthenticated' | 'expired';

interface AuthContextValue {
  authState: AuthState;
  flowData: Pick<AuthStartResponse, 'user_code' | 'verification_uri' | 'flow_id'> | null;
  flowError: string | null;
  startFlow: () => Promise<void>;
  performLogout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue>({
  authState: 'unknown',
  flowData: null,
  flowError: null,
  startFlow: async () => {},
  performLogout: async () => {},
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}

export function useAuthProvider(): AuthContextValue {
  const [authState, setAuthState] = useState<AuthState>('unknown');
  const [flowData, setFlowData] = useState<AuthContextValue['flowData']>(null);
  const [flowError, setFlowError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // On mount: check current auth status
  useEffect(() => {
    checkAuthStatus()
      .then((data) => {
        if (data.authenticated) setAuthState('authenticated');
        else if (data.expired) setAuthState('expired');
        else setAuthState('unauthenticated');
      })
      .catch(() => setAuthState('unauthenticated'));

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const doPoll = async (flowId: string) => {
    try {
      const data = await pollAuthFlow(flowId);
      if (data.done) {
        clearInterval(pollRef.current!);
        pollRef.current = null;
        setFlowData(null);
        setAuthState('authenticated');
      } else if (data.retry_after) {
        // Adjust poll interval if server requests slower polling
        clearInterval(pollRef.current!);
        pollRef.current = setInterval(
          () => doPoll(flowId),
          data.retry_after * 1000
        );
      } else if (data.error && !data.done) {
        clearInterval(pollRef.current!);
        pollRef.current = null;
      }
    } catch {
      // Network error during poll — keep trying
    }
  };

  const startFlow = async () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setFlowError(null);
    try {
      const data = await startAuthFlow();
      setFlowData({
        user_code: data.user_code,
        verification_uri: data.verification_uri,
        flow_id: data.flow_id,
      });
      pollRef.current = setInterval(() => doPoll(data.flow_id), 5000);
    } catch (err) {
      setFlowError(err instanceof Error ? err.message : 'Failed to start authentication');
    }
  };

  const performLogout = async () => {
    await logout();
    setAuthState('unauthenticated');
    setFlowData(null);
  };

  return { authState, flowData, flowError, startFlow, performLogout };
}
