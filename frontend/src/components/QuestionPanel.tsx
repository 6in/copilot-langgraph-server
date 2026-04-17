import { useState } from 'react';
import type { CSSProperties } from 'react';
import type { AUQQuestion, AskUserQuestionPayload } from '../types';
import { useCurrentTheme } from '../contexts/ThemeContext';

// -- Parser ------------------------------------------------------------------
const AUQ_RE = /<ask_user_question>([\s\S]*?)<\/ask_user_question>/;

export function parseAUQ(text: string): AskUserQuestionPayload | null {
  const m = text.match(AUQ_RE);
  if (!m) return null;
  try {
    return JSON.parse(m[1].trim()) as AskUserQuestionPayload;
  } catch {
    return null;
  }
}

// -- Indicator helper (Pitfall 5) --------------------------------------------
function getOptionIndicatorStyle(
  type: string,
  selected: boolean,
): CSSProperties {
  return {
    width: 12,
    height: 12,
    borderRadius: type === 'multi' ? 3 : '50%',
    border: `1.5px solid ${selected ? '#22c55e' : '#3a3a48'}`,
    background: selected ? '#22c55e' : 'transparent',
    flexShrink: 0,
    transition: 'all 0.15s',
  };
}

// -- Answer state type -------------------------------------------------------
interface AnswerEntry {
  selected?: string | string[] | null;
  freeText?: string;
  text?: string;
}

type AnswerMap = Record<string, AnswerEntry>;

// -- Props -------------------------------------------------------------------
interface QuestionPanelProps {
  questions: AUQQuestion[];
  onSubmit: (answers: Record<string, string>) => void;
}

// -- Component ---------------------------------------------------------------
export function QuestionPanel({ questions, onSubmit }: QuestionPanelProps) {
  const theme = useCurrentTheme();
  const isDark = theme === 'dark';
  const [answers, setAnswers] = useState<AnswerMap>({});

  function toggleOption(qid: string, label: string, type: string) {
    setAnswers((prev) => {
      const cur = prev[qid] || {};
      if (type === 'single') {
        const next = cur.selected === label ? null : label;
        return { ...prev, [qid]: { ...cur, selected: next, freeText: undefined } };
      }
      const sel = (cur.selected as string[] | undefined) || [];
      const next = sel.includes(label) ? sel.filter((l) => l !== label) : [...sel, label];
      return { ...prev, [qid]: { ...cur, selected: next } };
    });
  }

  function setFreeOther(qid: string, text: string) {
    setAnswers((prev) => ({
      ...prev,
      [qid]: { ...(prev[qid] || {}), selected: null, freeText: text },
    }));
  }

  function setText(qid: string, text: string) {
    setAnswers((prev) => ({ ...prev, [qid]: { text } }));
  }

  function isAnswered(q: AUQQuestion): boolean {
    const a = answers[q.question] || {};
    if (q.optional) return true;
    if (q.type === 'text') return !!(a.text?.trim());
    if (q.allowFreeText && a.freeText !== undefined) return !!(a.freeText?.trim());
    if (q.type === 'multi') return ((a.selected as string[] | undefined) || []).length > 0;
    return !!a.selected;
  }

  const canSubmit = questions.every(isAnswered);

  function getDisplayValue(q: AUQQuestion): string {
    const a = answers[q.question] || {};
    if (q.type === 'text') return a.text || '';
    if (a.freeText !== undefined) return a.freeText || '';
    if (q.type === 'multi') return ((a.selected as string[] | undefined) || []).join(', ');
    return (a.selected as string) || '';
  }

  function handleSubmit() {
    const result: Record<string, string> = {};
    questions.forEach((q) => {
      result[q.question] = getDisplayValue(q);
    });
    onSubmit(result);
  }

  // -- Theme-aware styles ----------------------------------------------------
  const S = buildStyles(isDark);

  return (
    <div style={S.panel}>
      {questions.map((q) => {
        const a = answers[q.question] || {};
        const isFreeOther = a.freeText !== undefined;

        return (
          <div key={q.question} style={S.questionBlock}>
            <div style={S.questionHeader}>
              <span style={S.headerBadge}>{q.header}</span>
              <span style={S.questionText}>
                {q.question}
                {!q.optional && <span style={S.requiredMark}> *</span>}
              </span>
              {q.type === 'multi' && <span style={S.tag}>複数選択可</span>}
              {q.optional && <span style={S.optionalTag}>任意</span>}
            </div>

            {/* text type */}
            {q.type === 'text' && (
              <input
                style={S.textInput}
                value={a.text || ''}
                onChange={(e) => setText(q.question, e.target.value)}
                placeholder={q.placeholder || '入力してください'}
              />
            )}

            {/* single / multi type */}
            {(q.type === 'single' || q.type === 'multi' || !q.type) && (
              <>
                <div style={S.optionGrid}>
                  {q.options?.map((opt) => {
                    const qType = q.type || 'single';
                    const selected =
                      qType === 'multi'
                        ? ((a.selected as string[] | undefined) || []).includes(opt.label)
                        : a.selected === opt.label;
                    return (
                      <button
                        key={opt.label}
                        style={{
                          ...S.optionBtn,
                          ...(selected ? S.optionSelected : {}),
                          cursor: 'pointer',
                        }}
                        onClick={() => toggleOption(q.question, opt.label, qType)}
                      >
                        <div style={S.optionRow}>
                          <span style={getOptionIndicatorStyle(qType, selected)} />
                          <span style={S.optionLabel}>{opt.label}</span>
                        </div>
                        {opt.description && (
                          <span style={S.optionDesc}>{opt.description}</span>
                        )}
                        {selected && <span style={S.check}>&#x2713;</span>}
                      </button>
                    );
                  })}
                </div>

                {/* allowFreeText */}
                {q.allowFreeText && (
                  <div style={S.freeOtherRow}>
                    <button
                      style={{
                        ...S.freeOtherToggle,
                        ...(isFreeOther ? S.freeOtherToggleActive : {}),
                      }}
                      onClick={() => {
                        if (isFreeOther) {
                          setAnswers((prev) => {
                            const cur = { ...prev[q.question] };
                            delete cur.freeText;
                            return { ...prev, [q.question]: cur };
                          });
                        } else {
                          setFreeOther(q.question, '');
                        }
                      }}
                    >
                      その他
                    </button>
                    {isFreeOther && (
                      <input
                        autoFocus
                        style={S.freeOtherInput}
                        value={a.freeText || ''}
                        onChange={(e) => setFreeOther(q.question, e.target.value)}
                        placeholder="自由に入力してください"
                      />
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        );
      })}

      <button
        style={{ ...S.submitBtn, ...(!canSubmit ? S.submitDisabled : {}) }}
        disabled={!canSubmit}
        onClick={handleSubmit}
      >
        回答を送信
      </button>
    </div>
  );
}

// -- Style builder -----------------------------------------------------------
function buildStyles(isDark: boolean) {
  const text = isDark ? '#e8e8ec' : '#24292e';
  const mutedText = isDark ? '#888' : '#666';
  const btnBg = isDark ? '#1a1a22' : '#f6f8fa';
  const btnBorder = isDark ? '#2a2a35' : '#d1dbe3';
  const inputBg = isDark ? '#1a1a22' : '#fff';
  const inputBorder = isDark ? '#2a2a35' : '#d1dbe3';

  return {
    panel: {
      display: 'flex',
      flexDirection: 'column' as const,
      gap: 16,
      background: isDark ? 'transparent' : '#ffffff',
    } satisfies CSSProperties,

    questionBlock: {
      display: 'flex',
      flexDirection: 'column' as const,
      gap: 8,
    } satisfies CSSProperties,

    questionHeader: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      flexWrap: 'wrap' as const,
    } satisfies CSSProperties,

    headerBadge: {
      background: isDark ? '#1e2a3a' : '#e8f0fe',
      border: `1px solid ${isDark ? '#2a3a4a' : '#b8d4f0'}`,
      color: isDark ? '#60a5fa' : '#1a56db',
      fontSize: 10,
      fontWeight: 600,
      padding: '4px 8px',
      borderRadius: 4,
      letterSpacing: '0.05em',
    } satisfies CSSProperties,

    requiredMark: {
      color: '#ef4444',
      fontWeight: 600,
    } satisfies CSSProperties,

    questionText: {
      fontSize: 13,
      fontWeight: 600,
      color: text,
    } satisfies CSSProperties,

    tag: {
      fontSize: 10,
      color: mutedText,
      marginLeft: 'auto',
    } satisfies CSSProperties,

    optionalTag: {
      fontSize: 10,
      color: isDark ? '#60a5fa' : '#1a56db',
      background: isDark ? '#1e2a3a' : '#e8f0fe',
      border: `1px solid ${isDark ? '#2a3a4a' : '#b8d4f0'}`,
      padding: '2px 6px',
      borderRadius: 4,
      marginLeft: 'auto',
    } satisfies CSSProperties,

    textInput: {
      background: inputBg,
      border: `1px solid ${inputBorder}`,
      borderRadius: 8,
      padding: '8px 12px',
      color: text,
      fontSize: 13,
      outline: 'none',
      width: '100%',
      boxSizing: 'border-box' as const,
    } satisfies CSSProperties,

    optionGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(2,1fr)',
      gap: 8,
    } satisfies CSSProperties,

    optionBtn: {
      position: 'relative' as const,
      background: btnBg,
      border: `1px solid ${btnBorder}`,
      borderRadius: 8,
      padding: '8px 12px',
      textAlign: 'left' as const,
      display: 'flex',
      flexDirection: 'column' as const,
      gap: 4,
      transition: 'border-color 0.15s,background 0.15s',
    } satisfies CSSProperties,

    optionSelected: {
      background: isDark ? '#0f1f0f' : '#f0fdf4',
      border: '1px solid #22c55e',
    } satisfies CSSProperties,

    optionRow: {
      display: 'flex',
      alignItems: 'center',
      gap: 6,
    } satisfies CSSProperties,

    optionLabel: {
      fontSize: 13,
      fontWeight: 600,
      color: text,
    } satisfies CSSProperties,

    optionDesc: {
      fontSize: 11,
      color: mutedText,
      paddingLeft: 18,
    } satisfies CSSProperties,

    check: {
      position: 'absolute' as const,
      top: 6,
      right: 8,
      color: '#22c55e',
      fontSize: 11,
      fontWeight: 600,
    } satisfies CSSProperties,

    freeOtherRow: {
      display: 'flex',
      gap: 8,
      alignItems: 'center',
    } satisfies CSSProperties,

    freeOtherToggle: {
      background: btnBg,
      border: `1px dashed ${btnBorder}`,
      borderRadius: 6,
      padding: '5px 12px',
      color: mutedText,
      fontSize: 12,
      cursor: 'pointer',
      whiteSpace: 'nowrap' as const,
    } satisfies CSSProperties,

    freeOtherToggleActive: {
      border: '1px dashed #22c55e',
      color: '#22c55e',
    } satisfies CSSProperties,

    freeOtherInput: {
      flex: 1,
      background: inputBg,
      border: '1px solid #22c55e',
      borderRadius: 6,
      padding: '5px 10px',
      color: text,
      fontSize: 13,
      outline: 'none',
    } satisfies CSSProperties,

    submitBtn: {
      background: '#22c55e',
      border: 'none',
      borderRadius: 8,
      color: '#fff',
      fontSize: 13,
      fontWeight: 600,
      padding: '10px',
      cursor: 'pointer',
    } satisfies CSSProperties,

    submitDisabled: {
      background: isDark ? '#1a2a1a' : '#e5e7eb',
      color: isDark ? '#2a4a2a' : '#9ca3af',
      cursor: 'default',
    } satisfies CSSProperties,
  };
}
