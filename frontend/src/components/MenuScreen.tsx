// frontend/src/components/MenuScreen.tsx
// Landing/home screen displayed after authentication.
// Shows feature cards for available app sections.

import { useCurrentTheme } from '../contexts/ThemeContext';

interface MenuScreenProps {
  onNavigate: (screen: string) => void;
}

export function MenuScreen({ onNavigate }: MenuScreenProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';

  const screenBg = isDark ? '#1e1e2e' : '#f5f5f5';
  const cardBg = isDark ? '#2a2a3e' : '#fff';
  const textColor = isDark ? '#e0e0e0' : '#333';
  const cardBorder = isDark ? '#3a3a52' : '#ddd';
  const subtitleColor = isDark ? '#a0a0b8' : '#666';

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
          fontWeight: 700,
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
          marginBottom: '2.5rem',
          textAlign: 'center',
        }}
      >
        Choose a feature to get started
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
          gap: '1rem',
          width: '100%',
          maxWidth: '600px',
        }}
      >
        <FeatureCard
          icon="💬"
          title="Chat"
          description="AI-powered chat with GitHub Copilot"
          cardBg={cardBg}
          cardBorder={cardBorder}
          textColor={textColor}
          subtitleColor={subtitleColor}
          onClick={() => onNavigate('chat')}
        />
      </div>
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
      <div style={{ fontSize: '2rem', marginBottom: '0.75rem', lineHeight: 1 }}>
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
