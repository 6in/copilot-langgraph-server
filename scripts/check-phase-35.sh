#!/usr/bin/env bash
# scripts/check-phase-35.sh — Phase 35 ダッシュボード化 + デザイン統一の grep-based 検証ハーネス
#
# 用途: phase gate 直前に 1 回手動実行する。CI 統合はしない（UI-SPEC §Registry Safety）。
# 検証対象: UX-03-1〜3（ダッシュボード構造）+ UX-04-1〜7（CSS 変数・レスポンシブ・InputBar 分離）

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

FAIL=0

check() {
  local label="$1"
  local actual="$2"
  local op="$3"
  local expected="$4"
  if [ "$op" = "ge" ] && [ "$actual" -ge "$expected" ]; then
    echo "  PASS: $label ($actual >= $expected)"
  elif [ "$op" = "eq" ] && [ "$actual" = "$expected" ]; then
    echo "  PASS: $label ($actual == $expected)"
  else
    echo "  FAIL: $label (got $actual, expected $op $expected)"
    FAIL=1
  fi
}

echo "=== Phase 35 Verification Harness ==="

echo
echo "--- UX-04: CSS 変数基盤 ---"
C1=$(grep -cE '^\s*--color-(bg|surface|border|text|accent|destructive|success|header)' frontend/src/theme.css || true)
check "UX-04-1 semantic color 変数 >= 13" "$C1" ge 13

C2=$(awk '/\[data-theme="dark"\]\s*{/,/^\}$/' frontend/src/theme.css | grep -cE '^\s*--color-' || true)
check "UX-04-2 dark ブロック内 semantic override >= 9" "$C2" ge 9

C3=$(grep -c '@media (max-width: 1024px)' frontend/src/theme.css || true)
check "UX-04-3 @media tablet >= 1" "$C3" ge 1

C4=$(grep -c '@media (max-width: 767px)' frontend/src/theme.css || true)
check "UX-04-4 @media mobile >= 1" "$C4" ge 1

echo
echo "--- UX-04: 4 対象ファイルの hardcode / isDark 排除 ---"
for FILE in frontend/src/components/MenuScreen.tsx frontend/src/components/MessageArea.tsx frontend/src/components/ThreadSidebar.tsx frontend/src/components/Header.tsx; do
  C=$(grep -c '#7c6ff7' "$FILE" || true)
  check "UX-04-5 #7c6ff7 in $(basename "$FILE") == 0" "$C" eq 0

  C=$(grep -cE 'isDark \?' "$FILE" || true)
  check "UX-04-6 isDark 三項 in $(basename "$FILE") == 0" "$C" eq 0
done

echo
echo "--- UX-04: InputBar 分離 ---"
if [ -f frontend/src/components/InputBar.tsx ]; then
  echo "  PASS: InputBar.tsx が存在"
  C=$(grep -cE 'toolbarSlot|previewSlot|onSend' frontend/src/components/InputBar.tsx || true)
  check "UX-04-7 InputBar に toolbarSlot/previewSlot/onSend >= 3" "$C" ge 3
else
  echo "  FAIL: frontend/src/components/InputBar.tsx が存在しない"
  FAIL=1
fi

echo
echo "--- UX-03: MenuScreen ダッシュボード構造 ---"
C=$(grep -c 'aria-labelledby="section-' frontend/src/components/MenuScreen.tsx || true)
check "UX-03-1 aria-labelledby=section-* >= 3" "$C" ge 3

C=$(grep -c 'slice(0, 5)' frontend/src/components/MenuScreen.tsx || true)
check "UX-03-2 slice(0, 5) >= 1" "$C" ge 1

C=$(grep -cE 'アプリケーション|最近のスレッド|その他' frontend/src/components/MenuScreen.tsx || true)
check "UX-03-3 日本語セクション見出し 3 種 >= 3" "$C" ge 3

echo
if [ "$FAIL" -eq 0 ]; then
  echo "=== All Phase 35 checks passed ==="
  exit 0
else
  echo "=== FAIL: Phase 35 verification failed ==="
  exit 1
fi
