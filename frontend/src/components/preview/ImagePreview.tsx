// frontend/src/components/preview/ImagePreview.tsx
// Phase 38 Plan 05-B: Modal 内画像プレビュー (UI-SPEC §"ImagePreview" L432-436)。
// raw bytes 直配信、サムネ生成しない (Phase 36 D-23 と同方針)。
// size cap 10MB は AttachmentModal 側で attachment.size を見て fetch 前に弾く。

interface ImagePreviewProps {
  url: string;
  alt: string;
}

export default function ImagePreview({ url, alt }: ImagePreviewProps) {
  return (
    <img
      src={url}
      alt={alt}
      style={{
        maxWidth: '100%',
        maxHeight: '100%',
        objectFit: 'contain',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-border)',
      }}
    />
  );
}
