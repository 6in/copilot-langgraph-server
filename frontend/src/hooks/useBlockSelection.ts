// frontend/src/hooks/useBlockSelection.ts
// AG Grid cell block selection (drag to select range, Ctrl+C to copy).
// Ported from work/web-api-proxy/packages/apps/app-template/src/hooks/useBlockSelection.ts

import { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import type { AgGridReact } from 'ag-grid-react';
import type { ColDef, CellMouseDownEvent, CellMouseOverEvent, CellStyleFunc } from 'ag-grid-community';

interface CellPos {
  rowIndex: number;
  colId: string;
}

interface Rect {
  minRow: number;
  maxRow: number;
  colIds: string[];
}

export function useBlockSelection<TData>({
  gridRef,
  containerRef,
  selectionColor = '#bbdefb',
  selectionBorderColor = '#1976d2',
}: {
  gridRef: React.RefObject<AgGridReact<TData> | null>;
  containerRef: React.RefObject<HTMLDivElement | null>;
  selectionColor?: string;
  selectionBorderColor?: string;
}) {
  const isDragging = useRef(false);
  const anchor = useRef<CellPos | null>(null);
  const current = useRef<CellPos | null>(null);
  const [selection, setSelection] = useState<Rect | null>(null);
  const selectionRef = useRef<Rect | null>(null);

  const computeRect = useCallback(
    (a: CellPos, b: CellPos): Rect | null => {
      const api = gridRef.current?.api;
      if (!api) return null;
      const allCols = api.getAllGridColumns();
      const allColIds = allCols.map((c) => c.getColId());
      const aIdx = allColIds.indexOf(a.colId);
      const bIdx = allColIds.indexOf(b.colId);
      if (aIdx === -1 || bIdx === -1) return null;
      const minColIdx = Math.min(aIdx, bIdx);
      const maxColIdx = Math.max(aIdx, bIdx);
      return {
        minRow: Math.min(a.rowIndex, b.rowIndex),
        maxRow: Math.max(a.rowIndex, b.rowIndex),
        colIds: allColIds.slice(minColIdx, maxColIdx + 1),
      };
    },
    [gridRef],
  );

  const isCellSelected = useCallback(
    (rowIndex: number, colId: string): boolean => {
      const sel = selectionRef.current;
      if (!sel) return false;
      return (
        rowIndex >= sel.minRow &&
        rowIndex <= sel.maxRow &&
        sel.colIds.includes(colId)
      );
    },
    [],
  );

  const clearSelection = useCallback(() => {
    selectionRef.current = null;
    setSelection(null);
    gridRef.current?.api?.redrawRows();
  }, [gridRef]);

  const onCellMouseDown = useCallback(
    (event: CellMouseDownEvent<TData>) => {
      if (event.rowIndex == null) return;
      event.event?.preventDefault();
      isDragging.current = true;
      const pos: CellPos = {
        rowIndex: event.rowIndex,
        colId: event.column.getColId(),
      };
      anchor.current = pos;
      current.current = pos;
      const rect = computeRect(pos, pos);
      selectionRef.current = rect;
      setSelection(rect);
      gridRef.current?.api?.redrawRows();

      const viewport = containerRef.current?.querySelector('.ag-body-viewport');
      viewport?.classList.add('block-selecting');
    },
    [computeRect, gridRef, containerRef],
  );

  const onCellMouseOver = useCallback(
    (event: CellMouseOverEvent<TData>) => {
      if (!isDragging.current || !anchor.current || event.rowIndex == null) return;
      const pos: CellPos = {
        rowIndex: event.rowIndex,
        colId: event.column.getColId(),
      };
      if (
        current.current &&
        current.current.rowIndex === pos.rowIndex &&
        current.current.colId === pos.colId
      ) {
        return;
      }
      current.current = pos;
      const rect = computeRect(anchor.current, pos);
      selectionRef.current = rect;
      setSelection(rect);
      gridRef.current?.api?.redrawRows();
    },
    [computeRect, gridRef],
  );

  // Global mouseup to end drag
  useEffect(() => {
    const handler = () => {
      if (isDragging.current) {
        isDragging.current = false;
        const viewport = containerRef.current?.querySelector('.ag-body-viewport');
        viewport?.classList.remove('block-selecting');
      }
    };
    document.addEventListener('mouseup', handler);
    return () => document.removeEventListener('mouseup', handler);
  }, [containerRef]);

  // Clear selection when clicking outside the grid
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (!selectionRef.current) return;
      if (containerRef.current?.contains(e.target as Node)) return;
      clearSelection();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [containerRef, clearSelection]);

  // Ctrl+C / Cmd+C clipboard copy
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const sel = selectionRef.current;
      if (!sel || !(e.ctrlKey || e.metaKey) || e.key !== 'c') return;
      const api = gridRef.current?.api;
      if (!api) return;

      e.preventDefault();
      const lines: string[] = [];
      for (let r = sel.minRow; r <= sel.maxRow; r++) {
        const rowNode = api.getDisplayedRowAtIndex(r);
        if (!rowNode) continue;
        const cells = sel.colIds.map((colId) => {
          const val = api.getCellValue({ rowNode, colKey: colId, useFormatter: true });
          return val ?? '';
        });
        lines.push(cells.join('\t'));
      }
      navigator.clipboard.writeText(lines.join('\n'));
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [gridRef]);

  const wrapColumnDefs = useMemo(() => {
    const wrap = (defs: ColDef<TData>[]): ColDef<TData>[] =>
      defs.map((def) => {
        const originalCellStyle = def.cellStyle as CellStyleFunc<TData> | undefined;
        return {
          ...def,
          cellStyle: (params: Parameters<CellStyleFunc<TData>>[0]) => {
            const base =
              typeof originalCellStyle === 'function'
                ? originalCellStyle(params)
                : originalCellStyle ?? null;
            const rowIdx = params.node.rowIndex;
            const colId = params.column.getColId();
            if (rowIdx != null && isCellSelected(rowIdx, colId)) {
              return {
                ...(base as Record<string, unknown> | null),
                backgroundColor: selectionColor,
                outline: `1px solid ${selectionBorderColor}`,
              };
            }
            return base;
          },
        };
      });
    return wrap;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selection, isCellSelected, selectionColor, selectionBorderColor]);

  return {
    onCellMouseDown,
    onCellMouseOver,
    wrapColumnDefs,
    clearSelection,
  };
}
