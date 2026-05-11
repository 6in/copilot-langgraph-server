// frontend/src/components/MenuScreen.tsx
// Landing/home screen displayed after authentication.
// Phase 35 Plan 06: 3-section dashboard (アプリ / 最近のスレッド / その他)
// Fetches app list from GET /api/apps and recent threads from GET /api/threads.

import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router';
import { getApps, listThreads } from '../api/client';
import { getDateGroup } from '../utils/threadGroups';
import type { AppDefinition, ThreadInfo } from '../types';

interface MenuScreenProps {
  onNavigate: (app: AppDefinition) => void;
  onOpenGems: () => void;
  onOpenDebate: () => void;  // Phase 17
  onOpenCanvas: () => void;  // Phase 16 (D-05, D-06)
}

export function MenuScreen({ onNavigate, onOpenGems, onOpenDebate, onOpenCanvas }: MenuScreenProps) {
  const navigate = useNavigate();

  const [apps, setApps] = useState<AppDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [allThreads, setAllThreads] = useState<ThreadInfo[]>([]);
  const [threadsError, setThreadsError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getApps()
      .then((data) => {
        if (!cancelled) {
          setApps(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('アプリ一覧を取得できませんでした。ページを再読み込みしてください。');
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    listThreads()
      .then((res) => {
        if (!cancelled) setAllThreads(res ?? []);
      })
      .catch((e) => {
        if (!cancelled) setThreadsError(String(e?.message ?? e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Pitfall 3 対策: backend の order by に依存しない client-side sort
  const recentThreads = useMemo(
    () =>
      [...allThreads]
        .sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''))
        .slice(0, 5),
    [allThreads]
  );

  // B-1 設計: Props 経由ではなく useNavigate() 直接呼び出し (App.tsx の Props 拡張不要)
  const handleThreadClick = (thread: ThreadInfo) => {
    const tid = thread.thread_id;
    switch (thread.app_id) {
      case 'gem':
      case 'gems':
        // ThreadInfo には gem_id が無い (verified: types.ts L37-42) → Gems 一覧へフォールバック
        navigate('/gems');
        break;
      case 'canvas':
        navigate(`/canvaschat/${tid}`);
        break;
      case 'debate':
        navigate(`/debate/${tid}`);
        break;
      case 'superchat':
        // RecentThreadCard には app_slug 情報が無いので、chat フォールバック
        navigate(`/chat/${tid}`);
        break;
      case 'chat':
      default:
        navigate(`/chat/${tid}`);
        break;
    }
  };

  return (
    <div
      className="menu-screen"
      style={{
        background: 'var(--color-bg)',
        color: 'var(--color-text)',
        padding: 'var(--space-12) var(--space-8)',
        minHeight: '100%',
        overflowY: 'auto',
      }}
    >
      <div style={{ maxWidth: '960px', margin: '0 auto' }}>
        {/* Hero */}
        <h1
          style={{
            fontFamily: 'var(--font-family-display)',
            fontSize: '2.8rem',
            fontWeight: 700,
            marginBottom: 'var(--space-2)',
            letterSpacing: '0.1em',
            background: 'var(--gradient-title)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            textAlign: 'center',
          }}
        >
          Orochi Chat
        </h1>
        <p
          style={{
            fontSize: '1rem',
            color: 'var(--color-text-muted)',
            marginBottom: 'var(--space-8)',
            textAlign: 'center',
          }}
        >
          使いたいアプリを選んで始めましょう
        </p>

        {error && (
          <div
            role="alert"
            style={{
              background: 'rgba(224, 82, 82, 0.1)',
              border: '1px solid var(--color-destructive)',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-3) var(--space-4)',
              color: 'var(--color-destructive)',
              marginBottom: 'var(--space-8)',
            }}
          >
            {error}
          </div>
        )}

        {/* Section 1: アプリケーション */}
        <section aria-labelledby="section-apps" style={{ marginBottom: 'var(--space-8)' }}>
          <h2
            id="section-apps"
            style={{
              font: 'var(--font-heading)',
              marginBottom: 'var(--space-4)',
              color: 'var(--color-text)',
            }}
          >
            アプリケーション
          </h2>
          <div
            className="menu-card-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
              gap: 'var(--space-4)',
            }}
          >
            {/* Gems 固定カード */}
            <FeatureCard
              icon="💎"
              title="Gems"
              description="AI ペルソナを管理してチャットを起動する"
              onClick={onOpenGems}
            />
            {/* Phase 16: Canvas カード */}
            <FeatureCard
              icon="🎨"
              title="Canvas"
              description="AI チャットで HTML アプリを作成・プレビュー・デプロイ"
              onClick={onOpenCanvas}
            />
            {/* Phase 17: 討論チャットカード */}
            <FeatureCard
              icon="💬"
              title="討論チャット"
              description="複数のエージェントがターン制で議論する"
              onClick={onOpenDebate}
            />

            {loading ? (
              <>
                {[0, 1, 2].map((i) => (
                  <SkeletonCard key={i} />
                ))}
              </>
            ) : !error && apps.length === 0 ? (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-1)',
                  padding: 'var(--space-4)',
                  color: 'var(--color-text-muted)',
                }}
              >
                <div style={{ fontWeight: 600 }}>利用可能なアプリがありません</div>
                <div style={{ fontSize: '0.875rem' }}>
                  apps/ ディレクトリに APP.md を追加するとアプリとして認識されます。
                </div>
              </div>
            ) : (
              <>
                {apps.map((app) => (
                  <FeatureCard
                    key={app.slug}
                    icon={app.icon}
                    title={app.name}
                    description={app.description}
                    onClick={() => onNavigate(app)}
                  />
                ))}
              </>
            )}
          </div>
        </section>

        {/* Section 2: 最近のスレッド */}
        <section aria-labelledby="section-recent" style={{ marginBottom: 'var(--space-8)' }}>
          <h2
            id="section-recent"
            style={{
              font: 'var(--font-heading)',
              marginBottom: 'var(--space-4)',
              color: 'var(--color-text)',
            }}
          >
            最近のスレッド
          </h2>
          {threadsError ? (
            <p style={{ color: 'var(--color-destructive)' }}>
              スレッド一覧を取得できませんでした。時間を置いて再度お試しください。
            </p>
          ) : recentThreads.length === 0 ? (
            <div>
              <p style={{ color: 'var(--color-text-muted)', fontWeight: 600 }}>まだ会話がありません</p>
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                上のアプリカードから新しい会話を始められます。
              </p>
            </div>
          ) : (
            <div
              className="menu-recent-grid"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
                gap: 'var(--space-3)',
              }}
            >
              {recentThreads.map((t) => (
                <RecentThreadCard key={t.thread_id} thread={t} onClick={() => handleThreadClick(t)} />
              ))}
            </div>
          )}
        </section>

        {/* Section 3: その他 */}
        <section aria-labelledby="section-other">
          <h2
            id="section-other"
            style={{
              font: 'var(--font-heading)',
              marginBottom: 'var(--space-4)',
              color: 'var(--color-text)',
            }}
          >
            その他
          </h2>
          <p style={{ color: 'var(--color-text-muted)' }}>
            アプリが足りない場合は管理者にご相談ください。
          </p>
        </section>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-6)',
        height: '140px',
        animation: 'pulse 0.8s ease-in-out infinite',
      }}
    >
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}

interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
  onClick: () => void;
}

function FeatureCard({ icon, title, description, onClick }: FeatureCardProps) {
  return (
    <button
      onClick={onClick}
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-6)',
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'box-shadow 0.2s, transform 0.1s',
        color: 'var(--color-text)',
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLButtonElement;
        el.style.boxShadow = '0 4px 16px rgba(0,0,0,0.18)';
        el.style.transform = 'translateY(-2px)';
        el.style.borderColor = 'var(--color-accent)';
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLButtonElement;
        el.style.boxShadow = 'none';
        el.style.transform = 'none';
        el.style.borderColor = '';
      }}
    >
      <div
        aria-hidden="true"
        style={{ fontSize: '2rem', marginBottom: 'var(--space-3)', lineHeight: 1 }}
      >
        {icon}
      </div>
      <div style={{ fontWeight: 600, fontSize: '1rem', marginBottom: 'var(--space-2)', color: 'var(--color-text)' }}>
        {title}
      </div>
      <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.4 }}>
        {description}
      </div>
    </button>
  );
}

interface RecentThreadCardProps {
  thread: ThreadInfo;
  onClick: () => void;
}

function RecentThreadCard({ thread, onClick }: RecentThreadCardProps) {
  // app_id → アイコン絵文字
  const appIcon = ((): string => {
    switch (thread.app_id) {
      case 'gem':
      case 'gems':
        return '💎';
      case 'canvas':
        return '🎨';
      case 'debate':
        return '💬';
      case 'superchat':
        return '🧠';
      default:
        return '💭';
    }
  })();

  return (
    <button
      className="recent-thread-card"
      onClick={onClick}
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-4)',
        cursor: 'pointer',
        textAlign: 'left',
        color: 'var(--color-text)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-1)',
        transition: 'box-shadow 0.2s, transform 0.1s',
        width: '100%',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 4px 16px rgba(0,0,0,0.18)';
        (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLButtonElement).style.boxShadow = 'none';
        (e.currentTarget as HTMLButtonElement).style.transform = 'none';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
        <span aria-hidden="true" style={{ fontSize: '1.25rem' }}>
          {appIcon}
        </span>
        <span
          style={{
            fontSize: '14px',
            fontWeight: 600,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
            color: 'var(--color-text)',
          }}
        >
          {thread.label}
        </span>
      </div>
      <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
        {getDateGroup(thread.updated_at)}
      </span>
    </button>
  );
}
