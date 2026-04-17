// frontend/src/components/MarkdownMessage.tsx
// ReactMarkdown wrapper for AI message rendering.
// Block code is rendered via Monaco Editor (read-only, auto-height, theme-aware, copy button).
// Inline code uses a styled <code> tag.

import { useState, useCallback, useEffect, useRef, useMemo, memo, lazy, Suspense } from 'react';
import type { editor } from 'monaco-editor';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Editor from '@monaco-editor/react';
import { useCurrentTheme } from '../contexts/ThemeContext';
import { extractTableData, shouldUseAgGrid, type MarkdownTableData } from '../utils/markdownTable';

// AG Grid is ~400KB; load only when a response actually contains a large table.
const ChatAgGridTable = lazy(() => import('./ChatAgGridTable'));

// Mermaid is ~1MB; load only when a response contains a mermaid code block.
const MermaidBlock = lazy(() => import('./MermaidBlock'));

function StyledFallbackTable({ data }: { data: MarkdownTableData }) {
  return (
    <div className="md-table-wrap">
      <table className="md-table">
        <thead>
          <tr>
            {data.headers.map((h, i) => (
              <th key={i}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface MarkdownMessageProps {
  content: string;
}

// Normalize common markdown language aliases to Monaco language IDs
const LANG_ALIASES: Record<string, string> = {
  js: 'javascript',
  ts: 'typescript',
  jsx: 'javascript',
  tsx: 'typescript',
  py: 'python',
  rb: 'ruby',
  sh: 'shell',
  bash: 'shell',
  zsh: 'shell',
  yml: 'yaml',
  md: 'markdown',
  Dockerfile: 'dockerfile',
};

function normalizeLanguage(lang: string): string {
  return LANG_ALIASES[lang] ?? lang;
}

interface CodeBlockProps {
  language: string;
  value: string;
  monacoTheme: 'vs' | 'vs-dark';
}

const CodeBlock = memo(function CodeBlock({ language, value, monacoTheme }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [value]);

  // Line count for auto-height: min 3, max 30 lines shown
  const lineCount = value.split('\n').length;
  const visibleLines = Math.min(Math.max(lineCount, 3), 30);
  const editorHeight = visibleLines * 19 + 16;

  // Walk up the DOM to find .cs-message-list and observe its width.
  // Monaco can't rely on its container width because chatscope's bubble
  // sizes itself to fit text content — we need the message list's width instead.
  useEffect(() => {
    if (!wrapperRef.current) return;

    let listEl: HTMLElement | null = wrapperRef.current;
    while (listEl && !listEl.classList.contains('cs-message-list')) {
      listEl = listEl.parentElement;
    }
    const target = listEl ?? wrapperRef.current;

    const relayout = () => {
      const available = target.clientWidth - 80; // subtract bubble padding
      if (available > 0) {
        wrapperRef.current!.style.width = available + 'px';
        editorRef.current?.layout({ width: available, height: editorHeight });
      }
    };

    relayout();
    const observer = new ResizeObserver(relayout);
    observer.observe(target);
    return () => observer.disconnect();
  }, [editorHeight]);

  return (
    <div
      ref={wrapperRef}
      style={{
        position: 'relative',
        margin: '8px 0',
        borderRadius: '6px',
        overflow: 'hidden',
        border: '1px solid var(--border-color, #e1e4e8)',
      }}
    >
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '4px 12px',
        backgroundColor: monacoTheme === 'vs-dark' ? '#1e1e1e' : '#f6f8fa',
        borderBottom: '1px solid var(--border-color, #e1e4e8)',
        fontSize: '12px',
        color: monacoTheme === 'vs-dark' ? '#858585' : '#57606a',
      }}>
        <span>{language || 'plaintext'}</span>
        <button
          onClick={handleCopy}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '12px',
            color: monacoTheme === 'vs-dark' ? '#858585' : '#57606a',
            transition: 'background 0.1s',
          }}
          title="コードをコピー"
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <Editor
        height={editorHeight}
        width="100%"
        language={language || 'plaintext'}
        value={value}
        theme={monacoTheme}
        onMount={(ed) => {
          editorRef.current = ed;
          // Trigger initial layout after mount so width is applied immediately
          if (wrapperRef.current) {
            let listEl: HTMLElement | null = wrapperRef.current;
            while (listEl && !listEl.classList.contains('cs-message-list')) {
              listEl = listEl.parentElement;
            }
            const target = listEl ?? wrapperRef.current;
            const available = target.clientWidth - 80;
            if (available > 0) {
              wrapperRef.current.style.width = available + 'px';
              ed.layout({ width: available, height: editorHeight });
            }
          }
        }}
        options={{
          readOnly: true,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: 'off',
          lineNumbers: lineCount > 1 ? 'on' : 'off',
          folding: false,
          renderLineHighlight: 'none',
          overviewRulerLanes: 0,
          hideCursorInOverviewRuler: true,
          scrollbar: {
            vertical: lineCount > 30 ? 'auto' : 'hidden',
            horizontal: 'auto',
            alwaysConsumeMouseWheel: false,
          },
          contextmenu: false,
          fontSize: 13,
          padding: { top: 8, bottom: 8 },
        }}
      />
    </div>
  );
});

// Collapsible HTML block for canvas responses (canvashtml language tag).
// Starts collapsed to avoid cluttering the chat with large HTML payloads.
const CollapsibleCodeBlock = memo(function CollapsibleCodeBlock({
  value,
  monacoTheme,
}: {
  value: string;
  monacoTheme: 'vs' | 'vs-dark';
}) {
  const [expanded, setExpanded] = useState(false);
  const lineCount = value.split('\n').length;
  const editorHeight = Math.min(Math.max(lineCount, 3), 30) * 19 + 16;
  const borderColor = monacoTheme === 'vs-dark' ? '#3c3c3c' : '#e1e4e8';
  const headerBg = monacoTheme === 'vs-dark' ? '#1e1e1e' : '#f6f8fa';
  const headerColor = monacoTheme === 'vs-dark' ? '#858585' : '#57606a';

  return (
    <div style={{ border: `1px solid ${borderColor}`, borderRadius: '6px', margin: '8px 0', overflow: 'hidden', width: '100%', minWidth: 0 }}>
      <button
        onClick={() => setExpanded((e) => !e)}
        style={{
          display: 'flex',
          width: '100%',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '4px 12px',
          background: headerBg,
          border: 'none',
          borderBottom: expanded ? `1px solid ${borderColor}` : 'none',
          cursor: 'pointer',
          fontSize: '12px',
          color: headerColor,
        }}
      >
        <span>{expanded ? '▼' : '▶'} HTML ({lineCount}行)</span>
        <span>{expanded ? '折りたたむ' : '展開する'}</span>
      </button>
      {expanded && (
        <Editor
          height={editorHeight}
          width="100%"
          language="html"
          value={value}
          theme={monacoTheme}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            lineNumbers: 'on',
            folding: true,
            renderLineHighlight: 'none',
            scrollbar: { vertical: lineCount > 30 ? 'auto' : 'hidden', horizontal: 'auto', alwaysConsumeMouseWheel: false },
            contextmenu: false,
            fontSize: 13,
            padding: { top: 8, bottom: 8 },
          }}
        />
      )}
    </div>
  );
});

export const MarkdownMessage = memo(function MarkdownMessage({ content }: MarkdownMessageProps) {
  const theme = useCurrentTheme();
  const monacoTheme = theme === 'dark' ? 'vs-dark' : 'vs';

  const components = useMemo(() => ({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    pre({ children, node }: { children?: React.ReactNode; node?: any }) {
      // Extract language from pre > code.properties.className (hast node tree).
      const codeNode = node?.children?.find((c: { tagName?: string }) => c.tagName === 'code');
      const classNames: string[] = codeNode?.properties?.className ?? [];
      const langMatch = classNames.join(' ').match(/language-(\w+)/);
      const language = langMatch ? normalizeLanguage(langMatch[1]) : '';

      const value = codeNode
        ? String(codeNode.children?.map((c: { value?: string }) => c.value ?? '').join('') ?? '').replace(/\n$/, '')
        : '';

      // canvashtml / html: collapsible, read-only HTML block
      if (language === 'canvashtml' || language === 'html') {
        return <CollapsibleCodeBlock value={value} monacoTheme={monacoTheme} />;
      }

      // mermaid: render diagram with View/Source toggle
      if (language === 'mermaid') {
        return (
          <Suspense fallback={<div style={{ padding: '12px', fontSize: '13px', color: '#858585' }}>Loading Mermaid...</div>}>
            <MermaidBlock value={value} monacoTheme={monacoTheme} theme={theme} />
          </Suspense>
        );
      }

      // Other block code — let the code component handle it inside this wrapper
      return <div style={{ width: '100%', minWidth: 0 }}>{children}</div>;
    },
    p({ children }: { children?: React.ReactNode }) {
      return <p style={{ margin: '0 0 0.2em 0' }}>{children}</p>;
    },
    table({ children }: { children?: React.ReactNode }) {
      const data = extractTableData(children);
      // Structurally invalid table (empty headers or rows) — fall back to
      // react-markdown's default <table> structure with our CSS.
      if (!shouldUseAgGrid(data)) {
        return (
          <div className="md-table-wrap">
            <table className="md-table">{children}</table>
          </div>
        );
      }
      return (
        <Suspense fallback={<StyledFallbackTable data={data} />}>
          <ChatAgGridTable data={data} theme={theme} />
        </Suspense>
      );
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    code({ className, children, node, ...props }: React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode; node?: any }) {
            // react-markdown v10: className may come from hast node properties
            const effectiveClassName = className
              || (node?.properties?.className && Array.isArray(node.properties.className)
                  ? node.properties.className.join(' ')
                  : node?.properties?.className)
              || '';
            const match = /language-(\w+)/.exec(effectiveClassName);
            const isBlock = !!match || (typeof children === 'string' && children.includes('\n'));

            if (isBlock) {
              const language = normalizeLanguage(match ? match[1] : '');
              const value = String(children).replace(/\n$/, '');

              // canvashtml and mermaid are handled by the pre component above;
              // this handles all other block code languages
              return (
                <CodeBlock
                  language={language}
                  value={value}
                  monacoTheme={monacoTheme}
                />
              );
            }

            return (
              <code
                {...props}
                style={{
                  backgroundColor: theme === 'dark' ? '#2d2d2d' : '#f0f0f0',
                  color: theme === 'dark' ? '#e6e6e6' : '#24292e',
                  padding: '2px 5px',
                  borderRadius: '3px',
                  fontSize: '0.875em',
                  fontFamily: 'monospace',
                }}
              >
                {children}
              </code>
            );
        },
      }), [theme, monacoTheme]);

  return (
    <div style={{ maxWidth: '100%' }}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
});
