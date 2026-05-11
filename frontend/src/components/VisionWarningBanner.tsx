// frontend/src/components/VisionWarningBanner.tsx
// Phase 36 D-17: vision 非対応モデル選択中に画像を staging したときの警告 + ワンクリック切替 CTA。
// 色は accent 系のみ (negative/red トークン未使用、graceful 方針 = UI-SPEC Checker #9)。
// バナー自体は要素を完全に消す手段 (× ボタン) を提供し、モデル変更時は dismiss state がリセットされる。

interface VisionWarningBannerProps {
  currentModel: string;       // 現在選択中のモデル表示名
  suggestedModel: string;     // 推奨する vision 対応モデル表示名
  onSwitchModel: () => void;  // CTA クリック → 推奨モデルへ切替
  onDismiss?: () => void;     // × クリック → バナーを閉じる
}

export function VisionWarningBanner({
  currentModel,
  suggestedModel,
  onSwitchModel,
  onDismiss,
}: VisionWarningBannerProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 'var(--space-3)',
        padding: 'var(--space-3) var(--space-4)',
        borderLeft: '3px solid var(--color-accent)',
        background: 'var(--color-accent-subtle)',
      }}
    >
      <span aria-hidden="true" style={{ fontSize: 20, flexShrink: 0 }}>⚠</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: 'var(--color-text)',
            marginBottom: 4,
          }}
        >
          画像非対応モデル
        </div>
        <div style={{ fontSize: 14, color: 'var(--color-text)', lineHeight: 1.4 }}>
          現在のモデル（{currentModel}）は画像を読めません。
          <br />
          画像対応モデル（例: {suggestedModel}）に切り替えると画像付きで送信できます。
        </div>
        <button
          onClick={onSwitchModel}
          aria-label={`モデルを ${suggestedModel} に切り替える`}
          style={{
            marginTop: 'var(--space-2)',
            padding: 'var(--space-2) var(--space-3)',
            borderRadius: 'var(--radius-md)',
            border: 'none',
            background: 'var(--color-accent)',
            color: 'var(--color-accent-contrast)',
            fontWeight: 'bold',
            fontSize: 14,
            cursor: 'pointer',
          }}
        >
          {suggestedModel} に切り替える
        </button>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="この案内を閉じる"
          style={{
            border: 'none',
            background: 'transparent',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
            fontSize: 18,
            lineHeight: 1,
            padding: 'var(--space-1)',
            flexShrink: 0,
          }}
        >
          ×
        </button>
      )}
    </div>
  );
}
