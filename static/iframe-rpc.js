/**
 * iframe-rpc.js — Promise-based RPC client for Canvas iframe apps.
 *
 * Exposes `window.RPC` with the following methods:
 *   RPC.ai(prompt, timeoutMs?)      — call the parent AI endpoint
 *   RPC.query(poolName, sql, params?, timeoutMs?) — call the parent DB query endpoint
 *   RPC.call(method, params, timeoutMs?) — generic JSON-RPC 2.0 call
 *
 * Communicates with the parent frame via postMessage using JSON-RPC 2.0 protocol.
 * Loaded automatically by CanvasPane into every srcDoc iframe via inline <script>.
 *
 * Protocol (matches CanvasPane handleIframeMessage):
 *   Request:  { jsonrpc: '2.0', id, method, params }
 *   Response: { jsonrpc: '2.0', id, result: true|false, ...payload }
 *             result === false means the call failed; error field contains the message.
 */
(function () {
  'use strict';

  /** @type {Map<string, {resolve: Function, reject: Function, timer: number}>} */
  var pending = new Map();

  /**
   * Global message handler — receives responses from the parent frame.
   * Matches by jsonrpc version and id, then settles the pending Promise.
   *
   * @param {MessageEvent} e
   */
  function handleMessage(e) {
    var data = e.data;
    if (!data || data.jsonrpc !== '2.0' || !data.id) return;

    var entry = pending.get(data.id);
    if (!entry) return;

    pending.delete(data.id);
    clearTimeout(entry.timer);

    if (data.result === false) {
      entry.reject(new Error(data.error || 'RPC failed'));
    } else {
      entry.resolve(data);
    }
  }

  window.addEventListener('message', handleMessage);

  /**
   * Internal generic call helper.
   *
   * @param {string} method       JSON-RPC method name
   * @param {object} params       Method parameters
   * @param {number} timeoutMs    Milliseconds before the promise rejects
   * @returns {Promise<object>}   Resolves with the full response object
   */
  function _call(method, params, timeoutMs) {
    var ms = typeof timeoutMs === 'number' ? timeoutMs : 60000;
    var id = crypto.randomUUID();

    return new Promise(function (resolve, reject) {
      var timer = setTimeout(function () {
        if (pending.has(id)) {
          pending.delete(id);
          reject(new Error('RPC timeout: ' + method));
        }
      }, ms);

      pending.set(id, { resolve: resolve, reject: reject, timer: timer });

      parent.postMessage(
        { jsonrpc: '2.0', id: id, method: method, params: params },
        '*'
      );
    });
  }

  /**
   * Call the parent AI chat endpoint.
   *
   * @param {string} prompt       The text prompt to send to the AI
   * @param {number} [timeoutMs=60000]  Timeout in milliseconds
   * @returns {Promise<{result: true, responseText: string}>}
   */
  function ai(prompt, timeoutMs) {
    return _call('ai', { prompt: prompt }, typeof timeoutMs === 'number' ? timeoutMs : 60000);
  }

  /**
   * Call the parent DB query endpoint.
   *
   * @param {string} poolName     Database pool name (e.g. 'default')
   * @param {string} sql          SQL query string
   * @param {Array}  [params]     Optional query parameters
   * @param {number} [timeoutMs=30000]  Timeout in milliseconds
   * @returns {Promise<{result: true, rows: Array}>}
   */
  function query(poolName, sql, params, timeoutMs) {
    var ms = typeof params === 'number' ? params : (typeof timeoutMs === 'number' ? timeoutMs : 30000);
    var p = Array.isArray(params) ? params : undefined;
    return _call('query', { pool_name: poolName, sql: sql, params: p }, ms);
  }

  /**
   * Generic JSON-RPC 2.0 call — for future extension points.
   *
   * @param {string} method       JSON-RPC method name
   * @param {object} params       Method parameters
   * @param {number} [timeoutMs=60000]  Timeout in milliseconds
   * @returns {Promise<object>}   Resolves with the full response object
   */
  function call(method, params, timeoutMs) {
    return _call(method, params, typeof timeoutMs === 'number' ? timeoutMs : 60000);
  }

  window.RPC = {
    ai: ai,
    query: query,
    call: call,
  };
})();
