// frontend/src/components/CanvasScreen.tsx
// CanvasScreen: Canvas App ハブ画面。
// デプロイ済みアプリ一覧 + 新規チャット起動 CTA を表示する（D-08〜D-11）。
// GemsScreen.tsx の骨格パターンを参照実装として使用。

import { useEffect, useState } from 'react';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { listCanvasApps } from '../api/client';
import type { CanvasAppInfo } from '../types';

interface CanvasScreenProps {
  onBack: () => void;                            // D-11: MenuScreen に戻る
  onStartChat: (initialThreadId?: string) => void; // D-09: 新規チャット or 既存アプリ起動
}

interface SkeletonCardProps {
  cardBg: string;
}

function SkeletonCard({ cardBg }: SkeletonCardProps) {
  return (
    <div
      style={{
        background: cardBg,
        borderRadius: '12px',
        padding: '24px',
        height: '120px',
        marginBottom: '16px',
        animation: 'pulse 0.8s ease-in-out infinite',
      }}
    >
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }`}</style>
    </div>
  );
}

interface CanvasAppCardProps {
  app: CanvasAppInfo;
  cardBg: string;
  cardBorder: string;
  textColor: string;
  onClick: () => void;
}

function CanvasAppCard({ app, cardBg, cardBorder, textColor, onClick }: CanvasAppCardProps) {
  const appBase = (import.meta.env.VITE_APP_BASE as string ?? '').replace(/\/$/, '');
  return (
    <div
      style={{
        background: cardBg,
        border: `1px solid ${cardBorder}`,
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '16px',
        cursor: 'pointer',
        transition: 'box-shadow 0.2s, transform 0.1s',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 16px rgba(0,0,0,0.18)';
        (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow = 'none';
        (e.currentTarget as HTMLElement).style.transform = 'none';
      }}
      onClick={onClick}
    >
      <div style={{ fontSize: '1rem', fontWeight: 600, color: textColor, marginBottom: '8px' }}>
        {app.name}
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
        <button
          style={{
            padding: '8px 16px',
            borderRadius: '4px',
            border: 'none',
            background: '#7c6ff7',
            color: '#ffffff',
            cursor: 'pointer',
            fontSize: '0.875rem',
            fontWeight: 600,
            minHeight: '48px',
          }}
          onClick={(e) => { e.stopPropagation(); onClick(); }}
        >
          チャットを開く
        </button>
        {app.deployed && (
          <button
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #7c6ff7',
              background: '#ffffff',
              color: '#7c6ff7',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: 600,
              minHeight: '48px',
            }}
            onClick={(e) => {
              e.stopPropagation();
              window.open(`${appBase}/apps/${app.app_id}/`, '_blank', 'noopener,noreferrer');
            }}
          >
            アプリを開く ↗
          </button>
        )}
      </div>
    </div>
  );
}

export function CanvasScreen({ onBack, onStartChat }: CanvasScreenProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';

  const screenBg = isDark ? '#1e1e2e' : '#f5f5f5';
  const cardBg = isDark ? '#2a2a3e' : '#ffffff';
  const textColor = isDark ? '#e0e0e0' : '#333333';
  const cardBorder = isDark ? '#3a3a52' : '#dddddd';
  const textSecondary = isDark ? '#a0a0b8' : '#666666';
  const mutedColor = isDark ? '#a0a0b8' : '#666666';

  const [apps, setApps] = useState<CanvasAppInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listCanvasApps(true) // deployed=true のみ
      .then((data) => { setApps(data); setLoading(false); })
      .catch(() => {
        setError('Canvas アプリの読み込みに失敗しました。ページを更新してください。');
        setLoading(false);
      });
  }, []);

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '48px 32px',
        background: screenBg,
        overflowY: 'auto',
      }}
    >
      <style>{`button:focus-visible { outline: 2px solid #7c6ff7; outline-offset: 2px; }`}</style>
      <div style={{ maxWidth: '640px', width: '100%' }}>

        {/* ヘッダー行 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
          <button
            onClick={onBack}
            aria-label="Back to menu"
            style={{
              padding: '0.25rem 0.75rem',
              borderRadius: '4px',
              border: '1px solid #555',
              background: 'transparent',
              color: textColor,
              cursor: 'pointer',
              fontSize: '0.875rem',
            }}
          >
            ← Back
          </button>
          <h1 style={{ fontSize: '2rem', fontWeight: 600, color: textColor, margin: 0 }}>
            Canvas Apps
          </h1>
        </div>

        {/* エラー表示 */}
        {error && (
          <div
            role="alert"
            style={{
              background: 'rgba(224,82,82,0.1)',
              border: '1px solid #e05252',
              borderRadius: '8px',
              padding: '12px 16px',
              color: '#e05252',
              marginBottom: '16px',
            }}
          >
            {error}
          </div>
        )}

        {/* Section 1: Deployed Apps */}
        <div style={{ marginBottom: '32px' }}>
          <div
            style={{
              fontSize: '0.875rem',
              fontWeight: 600,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: textSecondary,
              marginBottom: '16px',
            }}
          >
            Deployed Apps
          </div>

          {loading ? (
            <div aria-busy="true" aria-label="Loading canvas apps">
              {[0, 1, 2].map((i) => <SkeletonCard key={i} cardBg={cardBg} />)}
            </div>
          ) : apps.length === 0 ? (
            /* 空状態 */
            <div style={{ textAlign: 'center', padding: '48px 0' }}>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: mutedColor, marginBottom: '8px' }}>
                まだデプロイ済みアプリがありません
              </div>
              <div style={{ fontSize: '0.875rem', color: mutedColor, lineHeight: 1.5 }}>
                チャットで HTML アプリを生成して Deploy App ボタンを押すとここに表示されます
              </div>
            </div>
          ) : (
            /* アプリカード一覧 */
            apps.map((app) => (
              <CanvasAppCard
                key={app.app_id}
                app={app}
                cardBg={cardBg}
                cardBorder={cardBorder}
                textColor={textColor}
                onClick={() => onStartChat(app.thread_id ?? undefined)}  // D-10
              />
            ))
          )}
        </div>

        {/* Section 2: 新規チャット起動 CTA */}
        <button
          onClick={() => onStartChat()}
          style={{
            width: '100%',
            padding: '16px',
            borderRadius: '8px',
            border: 'none',
            background: '#7c6ff7',
            color: '#ffffff',
            fontSize: '1rem',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '48px',
          }}
        >
          + 新しいチャットを開始
        </button>

      </div>
    </div>
  );
}
