/**
 * parent-bridge.js — Parent frame relay for Canvas iframe JSON-RPC.
 *
 * Loaded by the hosting shell (GET /apps/{app_id}) and CanvasPane.tsx.
 * Listens for JSON-RPC 2.0 postMessages from child iframes, forwards to
 * POST /api/iframe-rpc, awaits completion via SSE, replies to the source iframe.
 *
 * Protocol (matches iframe-rpc.js on the iframe side):
 *   Request (iframe -> parent):  { jsonrpc: '2.0', id, method, params }
 *   Response (parent -> iframe): { jsonrpc: '2.0', id, result: true|false, ...payload }
 *
 * Phase 19 — shared between hosted shell and CanvasPane.tsx.
 */

/**
 * Wait for an arq job to complete via SSE, then fetch the result.
 * @param {string} job_id
 * @returns {Promise<string>} raw result JSON string
 */
async function _waitForJob(job_id) {
  return new Promise((resolve, reject) => {
    const es = new EventSource('/api/job/' + job_id + '/stream');

    const timer = setTimeout(function () {
      es.close();
      reject(new Error('RPC timeout'));
    }, 60000);

    es.onmessage = async function (ev) {
      try {
        var event = JSON.parse(ev.data);
        if (event.status === 'done') {
          clearTimeout(timer);
          es.close();
          var jobResp = await fetch('/api/job/' + job_id, { credentials: 'include' });
          var job = await jobResp.json();
          resolve(job.result != null ? job.result : '{"result":false,"error":"No result"}');
        }
        // status === 'thinking' — keep waiting
      } catch (_) {
        // Malformed SSE frame — ignore
      }
    };

    es.onerror = function () {
      clearTimeout(timer);
      es.close();
      reject(new Error('SSE connection failed'));
    };
  });
}

/**
 * Handle a postMessage from a child iframe.
 * Validates origin, parses JSON-RPC, relays to /api/iframe-rpc, replies to source.
 * @param {MessageEvent} e
 */
async function handleIframeMessage(e) {
  // Origin validation: same origin or 'null' (srcdoc iframe has null origin)
  if (e.origin !== window.location.origin && e.origin !== 'null') return;

  var msg = e.data;
  if (!msg || typeof msg !== 'object' || msg.jsonrpc !== '2.0') return;

  var id = msg.id;
  var method = msg.method;
  var params = msg.params;
  if (!id || !method) return;

  var source = e.source;
  if (!source) return;

  try {
    var resp = await fetch('/api/iframe-rpc', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id, method: method, params: params != null ? params : {} }),
    });

    if (!resp.ok) {
      throw new Error('iframe-rpc HTTP ' + resp.status);
    }

    var data = await resp.json();
    var job_id = data.job_id;
    var resultStr = await _waitForJob(job_id);

    var parsed;
    try {
      parsed = JSON.parse(resultStr);
    } catch (_) {
      parsed = { result: false, error: 'Invalid response format' };
    }

    var reply = { jsonrpc: '2.0', id: id };
    if (parsed && typeof parsed === 'object') {
      Object.assign(reply, parsed);
    } else {
      reply.result = parsed;
    }

    source.postMessage(reply, '*');
  } catch (err) {
    source.postMessage(
      { jsonrpc: '2.0', id: id, result: false, error: err instanceof Error ? err.message : 'Unknown error' },
      '*'
    );
  }
}

// Idempotency guard: prevent duplicate listeners if script is loaded multiple times
if (!window.__parentBridgeInstalled) {
  window.__parentBridgeInstalled = true;
  window.addEventListener('message', handleIframeMessage);
}
