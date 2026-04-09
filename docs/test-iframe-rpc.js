/**
 * Phase 18 E2E テストスクリプト — ブラウザコンソールで実行
 *
 * 前提:
 *   - Canvas App を開いてプレビュータブに切り替えておく
 *   - このスクリプトをブラウザの DevTools Console に貼り付けて実行する
 *
 * テスト項目:
 *   1. AI メソッド — postMessage で AI 返答が返る
 *   2. QUERY メソッド — SELECT 1 が成功する
 *   3. QUERY ガード — INSERT が拒否される
 *   4. 不正 origin — 別 origin からのメッセージが無視される
 */

// ─── ユーティリティ ───────────────────────────────────────────────

/** iframe の contentWindow を取得（CanvasPane の preview iframe） */
function getPreviewIframe() {
  const iframe = document.querySelector('iframe');
  if (!iframe) throw new Error('iframe が見つかりません。プレビュータブを開いてください。');
  return iframe;
}

/**
 * postMessage を送信し、JSON-RPC レスポンスを Promise で受け取る。
 * @param {Window} targetWindow  送信先 (iframe.contentWindow)
 * @param {object} rpcRequest    JSON-RPC 2.0 リクエスト
 * @param {number} timeoutMs     タイムアウト（ms）
 */
function sendRpc(targetWindow, rpcRequest, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      window.removeEventListener('message', handler);
      reject(new Error(`タイムアウト (${timeoutMs}ms) — id=${rpcRequest.id}`));
    }, timeoutMs);

    function handler(e) {
      // 親フレームに返ってくるレスポンスを待つ
      if (e.data?.jsonrpc === '2.0' && e.data?.id === rpcRequest.id) {
        clearTimeout(timer);
        window.removeEventListener('message', handler);
        resolve(e.data);
      }
    }

    window.addEventListener('message', handler);
    // iframe から送る想定のリクエストを親に送信
    // (テスト時は直接 window.dispatchEvent で模倣)
    targetWindow.postMessage(rpcRequest, '*');
  });
}

/**
 * iframe から親フレームへ postMessage を送る模倣。
 * iframe.contentWindow.postMessage は same-origin 制限があるため、
 * 代わりに CustomEvent で iframe 内のコードが送る形を再現する。
 *
 * 実際の動作確認は下記の「HTMLコード貼り付け」方式を推奨。
 */
function dispatchFromIframe(rpcRequest) {
  // srcDoc iframe は origin='null' で postMessage を送る
  const fakeEvent = new MessageEvent('message', {
    data: rpcRequest,
    origin: 'null',
    source: getPreviewIframe().contentWindow,
  });
  window.dispatchEvent(fakeEvent);
}

// ─── テスト 1: AI メソッド ────────────────────────────────────────

async function testAI() {
  console.group('▶ Test 1: AI メソッド');
  const req = { jsonrpc: '2.0', id: 'test-ai-1', method: 'AI', params: { prompt: 'Reply with exactly: PONG' } };
  try {
    const responsePromise = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('タイムアウト')), 60000);
      function handler(e) {
        if (e.data?.jsonrpc === '2.0' && e.data?.id === req.id) {
          clearTimeout(timer);
          window.removeEventListener('message', handler);
          resolve(e.data);
        }
      }
      window.addEventListener('message', handler);
    });

    dispatchFromIframe(req);
    const res = await responsePromise;
    console.log('レスポンス:', res);
    if (res.error) {
      console.warn('⚠ エラーレスポンス:', res.error);
    } else {
      console.log('✓ AI レスポンス受信');
    }
  } catch (e) {
    console.error('✗ 失敗:', e.message);
  }
  console.groupEnd();
}

// ─── テスト 2: QUERY — SELECT 1 ───────────────────────────────────

async function testQuerySelect() {
  console.group('▶ Test 2: QUERY SELECT 1');
  const req = { jsonrpc: '2.0', id: 'test-q-1', method: 'QUERY', params: { sql: 'SELECT 1 AS val', pool_name: 'default' } };
  try {
    const responsePromise = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('タイムアウト')), 30000);
      function handler(e) {
        if (e.data?.jsonrpc === '2.0' && e.data?.id === req.id) {
          clearTimeout(timer);
          window.removeEventListener('message', handler);
          resolve(e.data);
        }
      }
      window.addEventListener('message', handler);
    });

    dispatchFromIframe(req);
    const res = await responsePromise;
    console.log('レスポンス:', res);
    if (res.error) {
      console.warn('⚠ エラーレスポンス:', res.error);
    } else {
      console.log('✓ SELECT クエリ成功 — rows:', res.result?.rows ?? res.result);
    }
  } catch (e) {
    console.error('✗ 失敗:', e.message);
  }
  console.groupEnd();
}

// ─── テスト 3: QUERY — INSERT が拒否される ────────────────────────

async function testQueryInsertBlocked() {
  console.group('▶ Test 3: QUERY INSERT（拒否確認）');
  const req = { jsonrpc: '2.0', id: 'test-q-2', method: 'QUERY', params: { sql: "INSERT INTO test VALUES (1)", pool_name: 'default' } };
  try {
    const responsePromise = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('タイムアウト')), 30000);
      function handler(e) {
        if (e.data?.jsonrpc === '2.0' && e.data?.id === req.id) {
          clearTimeout(timer);
          window.removeEventListener('message', handler);
          resolve(e.data);
        }
      }
      window.addEventListener('message', handler);
    });

    dispatchFromIframe(req);
    const res = await responsePromise;
    console.log('レスポンス:', res);
    if (res.error && typeof res.error === 'string' && res.error.toLowerCase().includes('select')) {
      console.log('✓ INSERT が正しく拒否された — error:', res.error);
    } else if (res.result === false) {
      console.log('✓ INSERT が正しく拒否された（result=false）');
    } else {
      console.warn('✗ INSERT が許可されてしまった — 要確認:', res);
    }
  } catch (e) {
    console.error('✗ 失敗:', e.message);
  }
  console.groupEnd();
}

// ─── テスト 4: 不正 origin — 無視される ──────────────────────────

function testInvalidOrigin() {
  console.group('▶ Test 4: 不正 origin（無視確認）');

  let received = false;
  const req = { jsonrpc: '2.0', id: 'test-origin-bad', method: 'AI', params: { prompt: 'hello' } };

  function handler(e) {
    if (e.data?.id === req.id) received = true;
  }
  window.addEventListener('message', handler);

  // 不正 origin を持つ MessageEvent を直接ディスパッチ
  const fakeEvent = new MessageEvent('message', {
    data: req,
    origin: 'https://evil.example.com',  // 不正 origin
    source: window,
  });
  window.dispatchEvent(fakeEvent);

  // 500ms 後に受信されていないことを確認
  setTimeout(() => {
    window.removeEventListener('message', handler);
    if (received) {
      console.warn('✗ 不正 origin のメッセージが処理された — セキュリティ問題！');
    } else {
      console.log('✓ 不正 origin のメッセージが正しく無視された');
    }
    console.groupEnd();
  }, 500);
}

// ─── 全テスト実行 ─────────────────────────────────────────────────

async function runAllTests() {
  console.log('='.repeat(50));
  console.log('Phase 18 E2E テスト開始');
  console.log('='.repeat(50));

  testInvalidOrigin();           // 同期（500ms 後に結果表示）
  await new Promise(r => setTimeout(r, 600));

  await testQueryInsertBlocked();
  await testQuerySelect();
  await testAI();                // 最後（AI は時間がかかる）

  console.log('='.repeat(50));
  console.log('テスト完了');
  console.log('='.repeat(50));
}

// ─── 個別実行用エクスポート ───────────────────────────────────────
// コンソールで個別実行: testAI(), testQuerySelect(), testQueryInsertBlocked(), testInvalidOrigin()

console.log(`
Phase 18 テストスクリプトが読み込まれました。

実行方法:
  runAllTests()         — 全テスト実行
  testAI()              — AI メソッドのみ
  testQuerySelect()     — SELECT 1 のみ
  testQueryInsertBlocked() — INSERT 拒否確認のみ
  testInvalidOrigin()   — 不正 origin 確認のみ

注意: Canvas App を開いてプレビュータブを表示した状態で実行してください。
`);
