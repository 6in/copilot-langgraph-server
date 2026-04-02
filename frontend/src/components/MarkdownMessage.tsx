// frontend/src/components/MarkdownMessage.tsx
// ReactMarkdown wrapper for AI message rendering.
// Block code is rendered via Monaco Editor (read-only, auto-height, theme-aware, copy button).
// Inline code uses a styled <code> tag.

import { useState, useCallback, useEffect, useRef, useMemo, memo } from 'react';
import type { editor } from 'monaco-editor';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Editor from '@monaco-editor/react';
import { useCurrentTheme } from '../contexts/ThemeContext';

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

export const MarkdownMessage = memo(function MarkdownMessage({ content }: MarkdownMessageProps) {
  const theme = useCurrentTheme();
  const monacoTheme = theme === 'dark' ? 'vs-dark' : 'vs';

  const components = useMemo(() => ({
    pre({ children }: { children?: React.ReactNode }) {
      return <div>{children}</div>;
    },
    code({ className, children, ...props }: React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode }) {
            const match = /language-(\w+)/.exec(className || '');
            const isBlock = !!match || (typeof children === 'string' && children.includes('\n'));

            if (isBlock) {
              const language = normalizeLanguage(match ? match[1] : '');
              const value = String(children).replace(/\n$/, '');
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
