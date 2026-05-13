// frontend/src/components/MermaidBlock.tsx
// Renders Mermaid diagram from code block with View/Source toggle.
// Lazy-loaded from MarkdownMessage to avoid loading mermaid (~1MB) upfront.
//
// Default: Source mode with editable Monaco Editor.
// View mode renders on demand using dangerouslySetInnerHTML.
// Source edits are local only — not persisted to chat messages.
//
// Why source-default: View-default で複数 mermaid ブロック同時 render が OS-level hang
// を起こすため (Phase 39 / UIFIX-01)。恒久修正候補は ADR-0053 参照、v6.1+ spike 予定。

import { useState, useCallback, useRef, useEffect, memo } from 'react';
import Editor from '@monaco-editor/react';
import mermaid from 'mermaid';
import { toPng } from 'html-to-image';
import type { Theme } from '../contexts/ThemeContext';

let mermaidId = 0;
let lastTheme: string | null = null;

function initMermaid(theme: Theme) {
  const t = theme === 'dark' ? 'dark' : 'default';
  if (lastTheme === t) return;
  lastTheme = t;
  mermaid.initialize({
    startOnLoad: false,
    theme: t,
    securityLevel: 'strict',
  });
}

interface MermaidBlockProps {
  value: string;
  monacoTheme: 'vs' | 'vs-dark';
  theme: Theme;
}

const MermaidBlock = memo(function MermaidBlock({ value, monacoTheme, theme }: MermaidBlockProps) {
  const [mode, setMode] = useState<'view' | 'source'>('source');
  const [editedSource, setEditedSource] = useState(value);
  const [svgHtml, setSvgHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rendering, setRendering] = useState(false);
  const [copied, setCopied] = useState<false | 'image' | 'text'>(false);
  // Track which source was last rendered so we know when to re-render
  const lastRenderedSource = useRef<string | null>(null);
  const svgContainerRef = useRef<HTMLDivElement | null>(null);
  // View pane resize
  const [viewHeight, setViewHeight] = useState(500);
  const resizing = useRef(false);
  const resizeStartY = useRef(0);
  const resizeStartH = useRef(0);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!resizing.current) return;
      const delta = e.clientY - resizeStartY.current;
      setViewHeight(Math.max(200, resizeStartH.current + delta));
    };
    const onMouseUp = () => { resizing.current = false; };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  const copyAsText = useCallback(() => {
    navigator.clipboard.writeText(editedSource).then(() => {
      setCopied('text');
      setTimeout(() => setCopied(false), 2000);
    });
  }, [editedSource]);

  const handleCopy = useCallback(() => {
    if (mode !== 'view' || !svgContainerRef.current) {
      copyAsText();
      return;
    }
    const el = svgContainerRef.current;
    // Temporarily shrink container to fit SVG content (remove flex stretch)
    const saved = el.style.cssText;
    el.style.width = 'fit-content';
    el.style.height = 'fit-content';
    el.style.display = 'block';
    el.style.overflow = 'visible';

    toPng(el, { skipFonts: true, pixelRatio: 3 })
      .then((dataUrl) => fetch(dataUrl))
      .then((res) => res.blob())
      .then((blob) =>
        navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
      )
      .then(() => {
        setCopied('image');
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => {
        copyAsText();
      })
      .finally(() => {
        el.style.cssText = saved;
      });
  }, [mode, copyAsText]);

  const renderDiagram = useCallback(async () => {
    // Already rendered for this exact source
    if ((svgHtml || error) && lastRenderedSource.current === editedSource) return;

    // Source changed — clear old result
    setSvgHtml(null);
    setError(null);
    setRendering(true);
    lastRenderedSource.current = editedSource;

    const id = `mermaid-${++mermaidId}`;

    initMermaid(theme);

    const cleanup = () => {
      try { document.getElementById(id)?.remove(); } catch { /* ignore */ }
    };

    try {
      await mermaid.parse(editedSource);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setRendering(false);
      return;
    }

    try {
      const { svg } = await mermaid.render(id, editedSource);
      cleanup();
      // Remove fixed width/height so SVG scales with container.
      // Preserve viewBox for aspect ratio.
      const scalable = svg
        .replace(/(<svg[^>]*?)\s+width="[^"]*"/i, '$1')
        .replace(/(<svg[^>]*?)\s+height="[^"]*"/i, '$1')
        .replace(/(<svg[^>]*?)>/i, '$1 width="100%" height="100%">');
      setSvgHtml(scalable);
      setError(null);
    } catch (err) {
      cleanup();
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRendering(false);
    }
  }, [editedSource, theme, svgHtml, error]);

  const handleView = useCallback(() => {
    setMode('view');
    renderDiagram();
  }, [renderDiagram]);

  const lineCount = editedSource.split('\n').length;
  const visibleLines = Math.min(Math.max(lineCount, 3), 20);
  const editorHeight = visibleLines * 19 + 16;

  const borderColor = monacoTheme === 'vs-dark' ? '#3c3c3c' : '#e1e4e8';
  const headerBg = monacoTheme === 'vs-dark' ? '#1e1e1e' : '#f6f8fa';
  const headerColor = monacoTheme === 'vs-dark' ? '#858585' : '#57606a';
  const activeColor = monacoTheme === 'vs-dark' ? '#e8e8f0' : '#24292e';

  const tabStyle = (active: boolean): React.CSSProperties => ({
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    color: active ? activeColor : headerColor,
    fontWeight: active ? 600 : 400,
  });

  return (
    <div style={{
      border: `1px solid ${borderColor}`,
      borderRadius: '6px',
      margin: '8px 0',
      overflow: 'hidden',
      width: '100%',
      minWidth: 0,
    }}>
      {/* Header bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '4px 12px',
        backgroundColor: headerBg,
        borderBottom: `1px solid ${borderColor}`,
        fontSize: '12px',
        color: headerColor,
      }}>
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <span>mermaid</span>
          <span style={{ margin: '0 4px', color: borderColor }}>|</span>
          <button onClick={handleView} style={tabStyle(mode === 'view')}>
            View
          </button>
          <button onClick={() => setMode('source')} style={tabStyle(mode === 'source')}>
            Source
          </button>
        </div>
        <button onClick={handleCopy} style={tabStyle(false)} title="コードをコピー">
          {copied === 'image' ? '✓ Copied' : copied === 'text' ? '✓ Copied (text)' : 'Copy'}
        </button>
      </div>

      {/* Content */}
      {mode === 'view' ? (
        <div>
        <div style={{
          padding: '12px',
          maxWidth: '100%',
          height: `${viewHeight}px`,
          overflow: 'auto',
          backgroundColor: monacoTheme === 'vs-dark' ? '#1e1e2e' : '#ffffff',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'flex-start',
        }}>
          {error ? (
            <div style={{ width: '100%' }}>
              <div style={{ color: '#e05252', fontSize: '12px', marginBottom: '8px' }}>
                Mermaid render error: {error}
              </div>
              <pre style={{
                margin: 0,
                padding: '8px',
                backgroundColor: monacoTheme === 'vs-dark' ? '#1e1e1e' : '#f6f8fa',
                color: monacoTheme === 'vs-dark' ? '#d4d4d4' : '#24292e',
                fontSize: '13px',
                fontFamily: 'monospace',
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                borderRadius: '4px',
              }}>
                {editedSource}
              </pre>
            </div>
          ) : svgHtml ? (
            <div
              ref={svgContainerRef}
              dangerouslySetInnerHTML={{ __html: svgHtml }}
              style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}
            />
          ) : rendering ? (
            <span style={{ color: headerColor }}>Rendering...</span>
          ) : null}
        </div>
        {/* Resize handle */}
        <div
          onMouseDown={(e) => {
            e.preventDefault();
            resizing.current = true;
            resizeStartY.current = e.clientY;
            resizeStartH.current = viewHeight;
          }}
          style={{
            height: '6px',
            cursor: 'ns-resize',
            backgroundColor: headerBg,
            borderTop: `1px solid ${borderColor}`,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
          }}
        >
          <div style={{
            width: '30px',
            height: '2px',
            backgroundColor: headerColor,
            borderRadius: '1px',
            opacity: 0.5,
          }} />
        </div>
        </div>
      ) : (
        <Editor
          height={editorHeight}
          width="100%"
          language="markdown"
          value={editedSource}
          theme={monacoTheme}
          onChange={(v) => setEditedSource(v ?? '')}
          options={{
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            lineNumbers: lineCount > 1 ? 'on' : 'off',
            folding: false,
            renderLineHighlight: 'none',
            overviewRulerLanes: 0,
            hideCursorInOverviewRuler: true,
            scrollbar: {
              vertical: lineCount > 20 ? 'auto' : 'hidden',
              horizontal: 'auto',
              alwaysConsumeMouseWheel: false,
            },
            contextmenu: false,
            fontSize: 13,
            padding: { top: 8, bottom: 8 },
          }}
        />
      )}
    </div>
  );
});

export default MermaidBlock;
