// frontend/src/components/MenuScreen.tsx
// Landing/home screen displayed after authentication.
// Fetches app list from GET /api/apps and renders one card per app.

import { useEffect, useState } from 'react';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { getApps } from '../api/client';
import type { AppDefinition } from '../types';

interface MenuScreenProps {
  onNavigate: (app: AppDefinition) => void;
  onOpenGems: () => void;
  onOpenDebate: () => void;  // Phase 17
  onOpenCanvas: () => void;  // Phase 16 (D-05, D-06)
}

export function MenuScreen({ onNavigate, onOpenGems, onOpenDebate, onOpenCanvas }: MenuScreenProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';

  const screenBg = isDark ? '#1e1e2e' : '#f5f5f5';
  const cardBg = isDark ? '#2a2a3e' : '#fff';
  const textColor = isDark ? '#e0e0e0' : '#333';
  const cardBorder = isDark ? '#3a3a52' : '#ddd';
  const subtitleColor = isDark ? '#a0a0b8' : '#666';
  const mutedColor = isDark ? '#9090a8' : '#666666';

  const [apps, setApps] = useState<AppDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getApps()
      .then((data) => {
        setApps(data);
        setLoading(false);
      })
      .catch(() => {
        setError('Could not load applications. Please refresh the page.');
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
        justifyContent: 'flex-start',
        padding: '3rem 2rem',
        background: screenBg,
        color: textColor,
        minHeight: 0,
        overflowY: 'auto',
      }}
    >
      <h1
        style={{
          fontSize: '2rem',
          fontWeight: 600,
          marginBottom: '0.5rem',
          color: textColor,
        }}
      >
        Copilot Chat
      </h1>
      <p
        style={{
          fontSize: '1rem',
          color: subtitleColor,
          marginBottom: error ? '1rem' : '2.5rem',
          textAlign: 'center',
        }}
      >
        Choose an application to get started
      </p>

      {error && (
        <div
          role="alert"
          style={{
            background: 'rgba(224,82,82,0.1)',
            border: '1px solid #e05252',
            borderRadius: '8px',
            padding: '12px 16px',
            color: '#e05252',
            marginBottom: '2.5rem',
            width: '100%',
            maxWidth: '600px',
          }}
        >
          {error}
        </div>
      )}

      {/* Gems 固定カード — ロード状態・エラー状態に依存しない（Pitfall 5 対策） */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
          gap: '1rem',
          width: '100%',
          maxWidth: '600px',
          marginBottom: '1rem',
        }}
      >
        <FeatureCard
          icon="💎"
          title="Gems"
          description="AI ペルソナを管理してチャットを起動する"
          cardBg={cardBg}
          cardBorder={cardBorder}
          textColor={textColor}
          subtitleColor={subtitleColor}
          onClick={onOpenGems}
        />
        {/* Phase 16: Canvas カード（D-05, D-16） */}
        <FeatureCard
          icon="🎨"
          title="Canvas"
          description="AI チャットで HTML アプリを作成・プレビュー・デプロイ"
          cardBg={cardBg}
          cardBorder={cardBorder}
          textColor={textColor}
          subtitleColor={subtitleColor}
          onClick={onOpenCanvas}
        />
        {/* Phase 17: 討論チャットカード */}
        <FeatureCard
          icon="💬"
          title="討論チャット"
          description="複数のエージェントがターン制で議論する"
          cardBg={cardBg}
          cardBorder={cardBorder}
          textColor={textColor}
          subtitleColor={subtitleColor}
          onClick={onOpenDebate}
        />
      </div>

      {loading ? (
        <div
          aria-busy="true"
          aria-label="Loading applications"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
            gap: '1rem',
            width: '100%',
            maxWidth: '600px',
          }}
        >
          {[0, 1, 2].map((i) => (
            <SkeletonCard key={i} cardBg={cardBg} />
          ))}
        </div>
      ) : !error && apps.length === 0 ? (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            gap: '0.5rem',
          }}
        >
          <div style={{ fontSize: '1rem', fontWeight: 600, color: mutedColor }}>
            No applications available
          </div>
          <div style={{ fontSize: '0.875rem', color: mutedColor }}>
            Add an APP.md file to the apps/ directory to define an application.
          </div>
        </div>
      ) : !loading && apps.length > 0 ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
            gap: '1rem',
            width: '100%',
            maxWidth: '600px',
          }}
        >
          {apps.map((app) => (
            <FeatureCard
              key={app.slug}
              icon={app.icon}
              title={app.name}
              description={app.description}
              cardBg={cardBg}
              cardBorder={cardBorder}
              textColor={textColor}
              subtitleColor={subtitleColor}
              onClick={() => onNavigate(app)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
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
        padding: '1.5rem',
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
  cardBg: string;
  cardBorder: string;
  textColor: string;
  subtitleColor: string;
  onClick: () => void;
}

function FeatureCard({
  icon,
  title,
  description,
  cardBg,
  cardBorder,
  textColor,
  subtitleColor,
  onClick,
}: FeatureCardProps) {
  return (
    <button
      onClick={onClick}
      style={{
        background: cardBg,
        border: `1px solid ${cardBorder}`,
        borderRadius: '12px',
        padding: '1.5rem',
        cursor: 'pointer',
        textAlign: 'left',
        transition: 'box-shadow 0.2s, transform 0.1s',
        color: textColor,
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLButtonElement).style.boxShadow =
          '0 4px 16px rgba(0,0,0,0.18)';
        (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLButtonElement).style.boxShadow = 'none';
        (e.currentTarget as HTMLButtonElement).style.transform = 'none';
      }}
    >
      <div
        aria-hidden="true"
        style={{ fontSize: '2rem', marginBottom: '0.75rem', lineHeight: 1 }}
      >
        {icon}
      </div>
      <div style={{ fontWeight: 600, fontSize: '1rem', marginBottom: '0.5rem' }}>
        {title}
      </div>
      <div style={{ fontSize: '0.85rem', color: subtitleColor, lineHeight: 1.4 }}>
        {description}
      </div>
    </button>
  );
}
