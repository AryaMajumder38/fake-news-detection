const $ = (id) => document.getElementById(id);

const DEFAULTS = {
  gatewayUrl: 'https://fake-news-gateway.fly.dev',
  apiKey: '',
};

async function loadSettings() {
  const s = await chrome.storage.sync.get(['gatewayUrl', 'apiKey']);
  return {
    gatewayUrl: (s.gatewayUrl || DEFAULTS.gatewayUrl).replace(/\/$/, ''),
    apiKey: s.apiKey || DEFAULTS.apiKey,
  };
}

function setStatus(text, isError) {
  const el = $('status');
  el.textContent = text;
  el.classList.toggle('error', !!isError);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Only http(s) for href; avoids breaking & in query strings from escapeHtml. */
function safeHttpUrl(u) {
  try {
    const x = new URL(String(u || ''), window?.location?.origin || 'http://localhost');
    if (x.protocol !== 'http:' && x.protocol !== 'https:') return '#';
    return x.href;
  } catch {
    return '#';
  }
}

function renderResult(data, extraction) {
  const sec = $('result');
  sec.classList.remove('hidden');
  const reasoning = data.reasoning ? escapeHtml(data.reasoning) : '';
  const related = (data.related_articles || [])
    .map((a) => {
      const title = escapeHtml(a.title || '');
      const href = safeHttpUrl(a.url);
      return `<li>${title} — <a href="${href}" target="_blank" rel="noopener">link</a></li>`;
    })
    .join('');
  const facts = (data.fact_checks || [])
    .map((f) => `<li>${escapeHtml(f.verdict || f.title || JSON.stringify(f))}</li>`)
    .join('');

  const extLine = extraction
    ? `<div class="meta">Text extraction: <strong>${escapeHtml(extraction)}</strong></div>`
    : '';

  sec.innerHTML = `
    <div class="verdict">Verdict: <span>${escapeHtml(data.verdict || '')}</span></div>
    ${extLine}
    <div class="meta">
      Confidence: ${Number(data.confidence).toFixed(4)}<br/>
      Credibility: ${Number(data.credibility_score).toFixed(2)}<br/>
      Domain: ${escapeHtml(data.domain || '')}<br/>
      Article date: ${escapeHtml(data.article_date || '')}
    </div>
    ${reasoning ? `<div class="reasoning">${reasoning}</div>` : ''}
    <details><summary>Related articles (${(data.related_articles || []).length})</summary>
      ${related ? `<ul class="list">${related}</ul>` : '<p class="meta">None</p>'}
    </details>
    <details><summary>Fact checks (${(data.fact_checks || []).length})</summary>
      ${facts ? `<ul class="list">${facts}</ul>` : '<p class="meta">None</p>'}
    </details>
  `;
}

$('openOptions').addEventListener('click', (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

$('analyze').addEventListener('click', async () => {
  const btn = $('analyze');
  const sec = $('result');
  sec.classList.add('hidden');
  sec.innerHTML = '';
  btn.disabled = true;
  setStatus('');

  const { gatewayUrl, apiKey } = await loadSettings();
  if (!apiKey) {
    setStatus('Set API key in Options (same as gateway API_KEY).', true);
    btn.disabled = false;
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    setStatus('No active tab.', true);
    btn.disabled = false;
    return;
  }

  if (tab.url?.startsWith('chrome://') || tab.url?.startsWith('edge://') || tab.url?.startsWith('about:')) {
    setStatus('Open a normal http(s) page to analyze.', true);
    btn.disabled = false;
    return;
  }

  let page;
  try {
    page = await chrome.tabs.sendMessage(tab.id, { type: 'GET_PAGE_DATA' });
  } catch {
    setStatus('Could not read this page. Reload the tab and try again.', true);
    btn.disabled = false;
    return;
  }

  if (!page?.ok) {
    setStatus(page?.error || 'Failed to read page.', true);
    btn.disabled = false;
    return;
  }

  setStatus(`Using ${page.extraction} text, calling gateway (RAG can take 30–60s)…`);

  const url = `${gatewayUrl}/predict`;
  const body = JSON.stringify({
    text: page.text,
    source_url: page.source_url,
    article_date: page.article_date || '',
  });

  // DEBUG: exact JSON sent to POST /predict (compare to visible page / manual curl)
  console.log('[FakeNewsCheck] POST /predict body (exact):', body);
  console.log('[FakeNewsCheck] extraction:', page.extraction, 'text.length:', (page.text || '').length);

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body,
    });

    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      setStatus(`Bad response (${res.status}): ${text.slice(0, 120)}`, true);
      btn.disabled = false;
      return;
    }

    if (!res.ok) {
      setStatus(data?.error || `HTTP ${res.status}`, true);
      btn.disabled = false;
      return;
    }

    setStatus('Done.');
    renderResult(data, page.extraction);
  } catch (e) {
    setStatus(`Network error: ${e.message || e}. Is the gateway running?`, true);
  } finally {
    btn.disabled = false;
  }
});
