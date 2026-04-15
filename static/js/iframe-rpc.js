/**
 * iframe-rpc.js — ES module RPC client for Canvas iframe apps.
 *
 * Usage:
 *   <script type="module">
 *     import { ai, query, call } from '$URL_PREFIX/js/iframe-rpc.js';
 *     const res = await ai('Hello');
 *     const res2 = await ai('Hello', { model: 'sonnet' });       // モデル指定
 *     const res3 = await ai('Hi',    { model: 'haiku', timeoutMs: 30000 });
 *   </script>
 *
 * Communicates with the parent frame via postMessage using JSON-RPC 2.0 protocol.
 *
 * Protocol (matches CanvasPane handleIframeMessage):
 *   Request:  { jsonrpc: '2.0', id, method, params }
 *   Response: { jsonrpc: '2.0', id, result: true|false, ...payload }
 *             result === false means the call failed; error field contains the message.
 */

/** @type {Map<string, {resolve: Function, reject: Function, timer: ReturnType<typeof setTimeout>}>} */
const pending = new Map();

window.addEventListener('message', (e) => {
  const data = e.data;
  if (!data || data.jsonrpc !== '2.0' || !data.id) return;

  const entry = pending.get(data.id);
  if (!entry) return;

  pending.delete(data.id);
  clearTimeout(entry.timer);

  if (data.result === false) {
    entry.reject(new Error(data.error || 'RPC failed'));
  } else {
    entry.resolve(data);
  }
});

/**
 * @param {string} method
 * @param {object} params
 * @param {number} timeoutMs
 * @returns {Promise<object>}
 */
function _call(method, params, timeoutMs) {
  const id = crypto.randomUUID();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`RPC timeout: ${method}`));
    }, timeoutMs);
    pending.set(id, { resolve, reject, timer });
    parent.postMessage({ jsonrpc: '2.0', id, method, params }, '*');
  });
}

/**
 * Call the parent AI endpoint.
 *
 * @param {string} prompt
 * @param {object|number} [optsOrTimeout]
 *   Object form (new): `{ model?, timeoutMs? }`
 *     - `model` — alias (`'haiku'`|`'sonnet'`|`'gpt-4.1'`) or a full Copilot
 *       model ID. If omitted, the server defaults to Haiku (low-cost, fast).
 *       Unknown values are rejected with `{result:false, error:...}` — no
 *       silent fallback.
 *     - `timeoutMs` — RPC timeout in ms (default 60000).
 *   Number form (legacy): `ai(prompt, 30000)` — treated as `timeoutMs`.
 * @returns {Promise<{result: true, responseText: string}>}
 */
export function ai(prompt, optsOrTimeout) {
  let model;
  let timeoutMs = 60000;
  if (typeof optsOrTimeout === 'number') {
    // legacy: ai(prompt, 30000)
    timeoutMs = optsOrTimeout;
  } else if (optsOrTimeout && typeof optsOrTimeout === 'object') {
    model = optsOrTimeout.model;
    if (typeof optsOrTimeout.timeoutMs === 'number') {
      timeoutMs = optsOrTimeout.timeoutMs;
    }
  }
  const params = { prompt };
  if (model !== undefined) params.model = model;
  return _call('AI', params, timeoutMs);
}

/**
 * Call the parent DB query endpoint (SELECT only).
 * @param {string} poolName
 * @param {string} sql
 * @param {number} [timeoutMs=30000]
 * @returns {Promise<{result: true, rows: object[]}>}
 */
export function query(poolName, sql, timeoutMs = 30000) {
  return _call('QUERY', { pool_name: poolName, sql }, timeoutMs);
}

/**
 * Generic JSON-RPC 2.0 call.
 * @param {string} method
 * @param {object} params
 * @param {number} [timeoutMs=60000]
 * @returns {Promise<object>}
 */
export function call(method, params, timeoutMs = 60000) {
  return _call(method, params, timeoutMs);
}
