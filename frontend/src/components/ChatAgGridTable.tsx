// Lazy-loaded AG Grid wrapper for Markdown tables.
// MIT Community edition only — no enterprise features.
// Imported via React.lazy() from MarkdownMessage so the ~400KB bundle is
// fetched only when a chat response actually contains a large table.

import { useCallback, useMemo, useRef, useState } from 'react';
import { AgGridReact } from 'ag-grid-react';
import {
  AllCommunityModule,
  ModuleRegistry,
  themeQuartz,
  type ColDef,
  type GridApi,
  type GridReadyEvent,
  type IRowNode,
} from 'ag-grid-community';
import type { MarkdownTableData } from '../utils/markdownTable';
import { useBlockSelection } from '../hooks/useBlockSelection';

function escapeTsvCell(value: string): string {
  // TSV breaks on tabs and newlines. Swap them for spaces so the copied
  // output pastes correctly into spreadsheets without column misalignment.
  return value.replace(/\t/g, ' ').replace(/\r?\n/g, ' ');
}

ModuleRegistry.registerModules([AllCommunityModule]);

interface ChatAgGridTableProps {
  data: MarkdownTableData;
  theme: 'light' | 'dark';
}

const ROW_HEIGHT = 32;
const HEADER_HEIGHT = 36;
const MAX_VISIBLE_ROWS = 12;

export default function ChatAgGridTable({ data, theme }: ChatAgGridTableProps) {
  const gridApiRef = useRef<GridApi | null>(null);
  const gridRef = useRef<AgGridReact | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [copied, setCopied] = useState(false);

  const isDark = theme === 'dark';
  const { onCellMouseDown, onCellMouseOver, wrapColumnDefs } = useBlockSelection({
    gridRef,
    containerRef,
    selectionColor: isDark ? '#1a3a5c' : '#bbdefb',
    selectionBorderColor: isDark ? '#4a9eff' : '#1976d2',
  });

  const columnDefs = useMemo<ColDef[]>(
    () =>
      data.headers.map((h, i) => ({
        headerName: h || `col${i + 1}`,
        field: `c${i}`,
        sortable: true,
        filter: true,
        resizable: true,
        flex: 1,
        minWidth: 100,
      })),
    [data.headers],
  );

  const rowData = useMemo(
    () =>
      data.rows.map((row) => {
        const obj: Record<string, string> = {};
        row.forEach((cell, i) => {
          obj[`c${i}`] = cell;
        });
        return obj;
      }),
    [data.rows],
  );

  const visibleRows = Math.min(data.rows.length, MAX_VISIBLE_ROWS);
  const height = HEADER_HEIGHT + visibleRows * ROW_HEIGHT + 8;

  const gridTheme = useMemo(
    () =>
      themeQuartz.withParams(
        theme === 'dark'
          ? {
              backgroundColor: '#1e1e2e',
              foregroundColor: '#e8e8f0',
              headerBackgroundColor: '#2a2a3e',
              headerTextColor: '#e8e8f0',
              borderColor: '#3a3a52',
              oddRowBackgroundColor: '#252535',
              rowHoverColor: '#313145',
            }
          : {
              backgroundColor: '#ffffff',
              foregroundColor: '#24292e',
              headerBackgroundColor: '#f6f8fa',
              headerTextColor: '#24292e',
              borderColor: '#e1e4e8',
              oddRowBackgroundColor: '#fafbfc',
              rowHoverColor: '#f0f3f6',
            },
      ),
    [theme],
  );

  const onGridReady = useCallback((event: GridReadyEvent) => {
    gridApiRef.current = event.api;
  }, []);

  const handleCopyTsv = useCallback(async () => {
    const api = gridApiRef.current;
    // Walk rows after filter + sort so the copied TSV matches what the
    // user currently sees, not the original markdown order.
    const fields = data.headers.map((_, i) => `c${i}`);
    const bodyLines: string[] = [];
    if (api) {
      api.forEachNodeAfterFilterAndSort((node: IRowNode<Record<string, string>>) => {
        const row = node.data;
        if (!row) return;
        bodyLines.push(fields.map((f) => escapeTsvCell(row[f] ?? '')).join('\t'));
      });
    } else {
      // Fallback: grid not yet ready — copy original data
      for (const row of data.rows) {
        bodyLines.push(row.map(escapeTsvCell).join('\t'));
      }
    }
    const headerLine = data.headers.map(escapeTsvCell).join('\t');
    const tsv = [headerLine, ...bodyLines].join('\n');

    try {
      await navigator.clipboard.writeText(tsv);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API can fail in insecure contexts — silently ignore
    }
  }, [data]);

  const buttonColor = theme === 'dark' ? '#9090a8' : '#57606a';
  const buttonBorder = theme === 'dark' ? '#3a3a52' : '#e1e4e8';

  const wrappedColumnDefs = useMemo(() => wrapColumnDefs(columnDefs), [wrapColumnDefs, columnDefs]);

  return (
    <div ref={containerRef} style={{ width: '100%', margin: '8px 0' }}>
      <div style={{ width: '100%', height }}>
        <AgGridReact
          ref={gridRef}
          theme={gridTheme}
          columnDefs={wrappedColumnDefs}
          rowData={rowData}
          headerHeight={HEADER_HEIGHT}
          rowHeight={ROW_HEIGHT}
          suppressMovableColumns={false}
          domLayout="normal"
          onGridReady={onGridReady}
          onCellMouseDown={onCellMouseDown}
          onCellMouseOver={onCellMouseOver}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
        <button
          type="button"
          onClick={handleCopyTsv}
          title="現在表示中の行をタブ区切りでコピー（Excel / スプレッドシート貼り付け用）"
          style={{
            background: 'transparent',
            border: `1px solid ${buttonBorder}`,
            borderRadius: 4,
            padding: '2px 10px',
            fontSize: 12,
            color: buttonColor,
            cursor: 'pointer',
          }}
        >
          {copied ? '✓ Copied' : '⎘ TSV コピー'}
        </button>
      </div>
    </div>
  );
}
