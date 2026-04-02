// frontend/src/components/MarkdownMessage.tsx
// ReactMarkdown wrapper for AI message rendering.
// Per 07-RESEARCH.md Pattern 2: use type="custom" + Message.CustomContent.
// NOT type="html" — that sets innerHTML and bypasses React's XSS protection.

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';

interface MarkdownMessageProps {
  content: string;
}

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  return (
    <div style={{ maxWidth: '100%', overflow: 'auto' }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
