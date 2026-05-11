// frontend/src/hooks/useAttachments.ts
// Phase 36 D-03/D-04/D-06/D-14/D-19: 3 入り口 (click/drop/paste) 統一 staging + upload + cancel.

import { useCallback, useRef, useState } from 'react';
import { postAttachments, deleteAttachment } from '../api/client';
import type { AttachmentMeta, ModelInfo } from '../types';

// D-01/D-02: pre-validate 用定数
const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'webp']);
const IMAGE_MAX_BYTES = 10 * 1024 * 1024;       // 10MB (D-02)
const TEXT_MAX_BYTES = 100 * 1024 * 1024;       // 100MB (D-01)
const MAX_IMAGES_PER_MESSAGE = 5;               // D-02
const ALLOWED_TEXT_EXTS = new Set([
  'txt', 'md', 'json', 'csv', 'py', 'js', 'ts', 'tsx', 'jsx',
  'html', 'css', 'yaml', 'yml', 'toml', 'xml', 'log', 'sh', 'sql',
]);
// text/* MIME はすべて許容 (D-01)

export interface StagingItem extends AttachmentMeta {
  localId: string;
  status: 'uploading' | 'done' | 'error';
  error?: string;
  abortCtrl?: AbortController;
  threadId?: string;
}

interface ValidationError {
  file: File;
  reason: string;
}

export function useAttachments(
  threadId: string | null,
  selectedModelInfo?: ModelInfo | null,
) {
  const [items, setItems] = useState<StagingItem[]>([]);
  const [validationError, setValidationError] = useState<ValidationError | null>(null);
  const latestItemsRef = useRef(items);
  latestItemsRef.current = items;

  const _currentImageCount = () =>
    latestItemsRef.current.filter((it) => IMAGE_EXTS.has(it.ext.toLowerCase())).length;

  const _validate = useCallback((file: File): string | null => {
    const ext = (file.name.split('.').pop() ?? '').toLowerCase();
    const isImage = IMAGE_EXTS.has(ext);
    const isTextLike = file.type.startsWith('text/') || ALLOWED_TEXT_EXTS.has(ext);

    if (isImage) {
      if (file.size > IMAGE_MAX_BYTES) {
        return `${file.name} は 10 MB を超えるため添付できません。`;
      }
      // D-19: model vision_limits による追加制約
      if (selectedModelInfo?.vision_limits) {
        const mps = selectedModelInfo.vision_limits.max_prompt_image_size;
        if (mps && file.size > mps) {
          return `${file.name} はモデルの上限サイズ (${Math.floor(mps / 1024 / 1024)} MB) を超えるため添付できません。`;
        }
        const allowed = selectedModelInfo.vision_limits.supported_media_types;
        if (allowed && allowed.length > 0 && !allowed.includes(file.type)) {
          return `${file.name} はモデルが対応していない形式です。`;
        }
      }
      // 枚数 cap
      if (_currentImageCount() >= MAX_IMAGES_PER_MESSAGE) {
        return `画像は 1 メッセージあたり ${MAX_IMAGES_PER_MESSAGE} 枚までです。`;
      }
      if (selectedModelInfo?.vision_limits?.max_prompt_images) {
        const cap = Math.min(MAX_IMAGES_PER_MESSAGE, selectedModelInfo.vision_limits.max_prompt_images);
        if (_currentImageCount() >= cap) {
          return `画像は 1 メッセージあたり ${cap} 枚までです。`;
        }
      }
      return null;
    }

    // text / code 系
    if (!isTextLike) {
      return `${ext} 形式は対応していません。対応形式: PNG / JPG / WebP / テキスト・コード系。`;
    }
    if (file.size > TEXT_MAX_BYTES) {
      return `${file.name} は 100 MB を超えるため添付できません。`;
    }
    return null;
  }, [selectedModelInfo]);

  const upload = useCallback(async (files: File[]) => {
    if (!threadId) {
      if (files.length > 0) {
        setValidationError({ file: files[0], reason: 'スレッドが未作成のため添付できません。' });
      }
      return;
    }
    for (const f of files) {
      const invalid = _validate(f);
      if (invalid) {
        setValidationError({ file: f, reason: invalid });
        // validation 失敗分は staging に入れない
        continue;
      }
      const ext = (f.name.split('.').pop() ?? '').toLowerCase();
      const localId = crypto.randomUUID();
      const ctrl = new AbortController();
      setItems((prev) => [...prev, {
        kind: 'file',
        name: f.name,
        storage_name: '',
        path: '',
        size: f.size,
        mime_type: f.type || 'application/octet-stream',
        ext,
        modified_at: new Date().toISOString(),
        localId,
        status: 'uploading',
        abortCtrl: ctrl,
        threadId,
      }]);
      try {
        const resp = await postAttachments(threadId, [f], ctrl.signal);
        const served = resp.attachments[0];
        setItems((prev) => prev.map((x) => x.localId === localId
          ? { ...x, ...served, threadId, status: 'done' as const } : x));
      } catch (e) {
        const msg = (e as Error).name === 'AbortError' ? 'cancelled' : (e as Error).message;
        if (msg === 'cancelled') {
          // AbortController で abort した場合は staging からも消す
          setItems((prev) => prev.filter((x) => x.localId !== localId));
        } else {
          setItems((prev) => prev.map((x) => x.localId === localId
            ? { ...x, status: 'error' as const, error: msg } : x));
        }
      }
    }
  }, [threadId, _validate]);

  const removeItem = useCallback(async (localId: string) => {
    const item = latestItemsRef.current.find((x) => x.localId === localId);
    // 楽観削除 — まず UI から消す
    setItems((prev) => prev.filter((x) => x.localId !== localId));
    if (!item) return;
    if (item.status === 'uploading' && item.abortCtrl) {
      item.abortCtrl.abort();
      return;
    }
    if (item.status === 'done' && threadId && item.storage_name) {
      // D-06 ケース D: サーバーも削除
      try {
        await deleteAttachment(threadId, item.storage_name);
      } catch {
        // best effort — UI 側は既に消しているので restore しない
      }
    }
  }, [threadId]);

  const clearAll = useCallback(() => setItems([]), []);

  const getReadyItems = useCallback(
    () => latestItemsRef.current.filter((x) => x.status === 'done').map((x) => ({
      kind: x.kind,
      name: x.name,
      storage_name: x.storage_name,
      path: x.path,
      size: x.size,
      mime_type: x.mime_type,
      ext: x.ext,
      modified_at: x.modified_at,
    }) as AttachmentMeta),
    [],
  );

  const dismissValidationError = useCallback(() => setValidationError(null), []);

  return {
    items,
    upload,
    removeItem,
    clearAll,
    getReadyItems,
    validationError,
    dismissValidationError,
  };
}
