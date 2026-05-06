/**
 * Content script (bundled to content-bundle.js).
 * Extraction order: JSON-LD (NewsArticle/Article + articleBody) → Mozilla Readability → body innerText fallback.
 */
import { Readability } from '@mozilla/readability';

const MAX_CHARS = 12000;
/** Prefer JSON-LD only when the body looks like a real article chunk. */
const MIN_JSONLD_BODY = 400;
/** Accept Readability only if we got a meaningful slice of text. */
const MIN_READABILITY_CHARS = 200;

function getMetaDate() {
  const pairs = [
    ['meta[property="article:published_time"]', 'content'],
    ['meta[property="article:modified_time"]', 'content'],
    ['meta[name="article:published_time"]', 'content'],
    ['meta[property="og:updated_time"]', 'content'],
    ['meta[name="pubdate"]', 'content'],
    ['meta[name="date"]', 'content'],
  ];
  for (const [sel, attr] of pairs) {
    const el = document.querySelector(sel);
    const v = el?.getAttribute(attr)?.trim();
    if (v) return v.slice(0, 64);
  }
  const timeEl = document.querySelector('time[datetime]');
  const dt = timeEl?.getAttribute('datetime')?.trim();
  if (dt) return dt.slice(0, 64);
  return '';
}

function normalizeWhitespace(s) {
  return String(s || '').replace(/\s+/g, ' ').trim();
}

function truncate(s) {
  const t = normalizeWhitespace(s);
  return t.length > MAX_CHARS ? t.slice(0, MAX_CHARS) : t;
}

function ldTypes(obj) {
  const t = obj?.['@type'];
  if (!t) return [];
  return Array.isArray(t) ? t.map(String) : [String(t)];
}

function isArticleLike(obj) {
  return ldTypes(obj).some((t) => {
    const l = t.toLowerCase();
    return (
      l.includes('newsarticle') ||
      l === 'article' ||
      l.includes('blogposting') ||
      l.includes('reportagearticle')
    );
  });
}

function textField(v) {
  if (typeof v === 'string') return v.trim();
  if (v && typeof v === 'object' && typeof v['@value'] === 'string') return v['@value'].trim();
  return '';
}

function getArticleBody(obj) {
  const b = obj?.articleBody;
  if (typeof b === 'string') return b.trim();
  if (b && typeof b === 'object' && typeof b['@value'] === 'string') return b['@value'].trim();
  if (Array.isArray(b)) {
    return b
      .map((x) => (typeof x === 'string' ? x : textField(x)))
      .filter(Boolean)
      .join('\n\n')
      .trim();
  }
  return '';
}

function getHeadline(obj) {
  return (
    textField(obj?.headline) ||
    textField(obj?.name) ||
    textField(obj?.title) ||
    ''
  );
}

function collectJsonLdObjects() {
  const out = [];
  const scripts = document.querySelectorAll('script[type="application/ld+json"]');
  for (const script of scripts) {
    let data;
    try {
      data = JSON.parse(script.textContent.trim());
    } catch {
      continue;
    }
    const pushObj = (o) => {
      if (o && typeof o === 'object') out.push(o);
    };
    if (Array.isArray(data)) {
      data.forEach((item) => {
        if (item?.['@graph'] && Array.isArray(item['@graph'])) {
          item['@graph'].forEach(pushObj);
        } else {
          pushObj(item);
        }
      });
    } else if (data?.['@graph'] && Array.isArray(data['@graph'])) {
      data['@graph'].forEach(pushObj);
    } else {
      pushObj(data);
    }
  }
  return out;
}

function tryJsonLd() {
  const objs = collectJsonLdObjects();
  let best = null;
  let bestLen = 0;
  for (const obj of objs) {
    if (!isArticleLike(obj)) continue;
    const body = getArticleBody(obj);
    if (body.length > bestLen) {
      bestLen = body.length;
      best = obj;
    }
  }
  if (!best || bestLen < MIN_JSONLD_BODY) return null;

  const headline = getHeadline(best);
  const body = getArticleBody(best);
  const parts = [];
  if (headline) parts.push(headline);
  parts.push(body);
  const text = truncate(parts.join('\n\n'));

  let articleDate = '';
  const dp = best.datePublished || best.dateModified || best.uploadDate;
  if (typeof dp === 'string') articleDate = dp.slice(0, 64);
  else if (dp && typeof dp === 'object' && typeof dp['@value'] === 'string') {
    articleDate = dp['@value'].slice(0, 64);
  }
  if (!articleDate) articleDate = getMetaDate();

  return { text: text || body, article_date: articleDate, extraction: 'json-ld' };
}

function tryReadability() {
  try {
    const clone = document.cloneNode(true);
    const reader = new Readability(clone);
    const article = reader.parse();
    if (!article) return null;
    const raw =
      [article.title, article.textContent].filter(Boolean).join('\n\n') ||
      article.textContent ||
      '';
    const text = truncate(raw);
    if (text.length < MIN_READABILITY_CHARS) return null;
    return {
      text,
      article_date: getMetaDate(),
      extraction: 'readability',
    };
  } catch {
    return null;
  }
}

function fallbackInnerText() {
  const raw = document.body?.innerText || '';
  const text = truncate(raw) || '(no visible text on this page)';
  return {
    text,
    article_date: getMetaDate(),
    extraction: 'fallback',
  };
}

function extractPageData() {
  const fromLd = tryJsonLd();
  if (fromLd) return { ...fromLd, source_url: window.location.href };

  const fromRd = tryReadability();
  if (fromRd) return { ...fromRd, source_url: window.location.href };

  return { ...fallbackInnerText(), source_url: window.location.href };
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'GET_PAGE_DATA') {
    try {
      sendResponse({ ok: true, ...extractPageData() });
    } catch (e) {
      sendResponse({ ok: false, error: String(e) });
    }
    return true;
  }
  return false;
});
