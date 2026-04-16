// Utilities for extracting structured data from react-markdown <table> children.
// Used by MarkdownMessage to hand off tables to AG Grid / a styled fallback.

import { Children, isValidElement, type ReactNode } from 'react';

export interface MarkdownTableData {
  headers: string[];
  rows: string[][];
}

function collectText(node: ReactNode): string {
  if (node == null || typeof node === 'boolean') return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(collectText).join('');
  if (isValidElement(node)) {
    return collectText((node.props as { children?: ReactNode }).children);
  }
  return '';
}

function extractCellRows(body: ReactNode): string[][] {
  const out: string[][] = [];
  Children.forEach(body, (tr) => {
    if (!isValidElement(tr)) return;
    const cells: string[] = [];
    Children.forEach((tr.props as { children?: ReactNode }).children, (cell) => {
      if (!isValidElement(cell)) return;
      cells.push(collectText((cell.props as { children?: ReactNode }).children).trim());
    });
    if (cells.length > 0) out.push(cells);
  });
  return out;
}

export function extractTableData(tableChildren: ReactNode): MarkdownTableData {
  let headers: string[] = [];
  let rows: string[][] = [];
  Children.forEach(tableChildren, (section) => {
    if (!isValidElement(section)) return;
    const tag =
      typeof section.type === 'string' ? section.type.toLowerCase() : '';
    const body = (section.props as { children?: ReactNode }).children;
    if (tag === 'thead') {
      const headRows = extractCellRows(body);
      if (headRows.length > 0) headers = headRows[0];
    } else if (tag === 'tbody') {
      rows = extractCellRows(body);
    }
  });
  return { headers, rows };
}

// All valid tables go through AG Grid so users get sort/filter/resize
// regardless of size. The CSS fallback (StyledFallbackTable) is still
// used as the Suspense placeholder while the AG Grid chunk loads, and
// for structurally-invalid tables (empty headers or rows).
export function shouldUseAgGrid(data: MarkdownTableData): boolean {
  return data.headers.length > 0 && data.rows.length > 0;
}
