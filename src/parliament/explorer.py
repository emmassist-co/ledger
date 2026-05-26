from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


def build_explorer_payload(document_root: Path) -> dict[str, object]:
    metadata = _read_json(document_root / "metadata.json")
    views_dir = document_root / "views"
    page_map = _read_json(document_root / "source" / "page_map.json")
    source_pages = page_map.get("pages", [])
    payload = {
        "document": {
            "document_id": metadata.get("document_id", document_root.name),
            "title": metadata.get("document_id", document_root.name),
            "page_count": metadata.get("page_count", 0),
            "episode_count": metadata.get("episode_count", 0),
            "claim_count": metadata.get("claim_count", 0),
            "reference_count": metadata.get("reference_count", 0),
            "source_pdf": _source_pdf_relpath(document_root),
            "cost_summary": metadata.get("cost_summary", {}),
            "pages": page_map.get("pages", []),
        },
        "counts": {
            "episodes": len(list((document_root / "episodes").glob("*.md"))),
            "claims": len(list((document_root / "claims").glob("clm-*.md"))),
            "references": len(list((document_root / "references").glob("ref-*.md"))),
            "views": len(list(views_dir.glob("*.md"))),
        },
        "views": [
            _artifact_record(path, id_key="view_id")
            for path in sorted(views_dir.glob("*.md"))
        ],
        "episodes": [
            _artifact_record(path, id_key="episode_id")
            for path in sorted((document_root / "episodes").glob("*.md"))
        ],
        "claims": [
            _artifact_record(path, id_key="claim_id", source_pages=source_pages)
            for path in sorted((document_root / "claims").glob("clm-*.md"))
        ],
        "references": [
            _artifact_record(path, id_key="reference_id")
            for path in sorted((document_root / "references").glob("ref-*.md"))
        ],
        "index": _artifact_record(document_root / "index.md", id_key="view_id"),
    }
    return payload


def build_explorer_html(payload: dict[str, object]) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Parliament Explorer</title>
  <style>
    :root {{
      --bg: #efe7da;
      --surface: #fffdf8;
      --surface-2: #f6efe4;
      --surface-3: #fbf7f1;
      --border: #d8ccb7;
      --border-strong: #bca88b;
      --text: #231b13;
      --text-dim: #706355;
      --accent: #0b6e63;
      --accent-2: #8a5b32;
      --accent-soft: rgba(11,110,99,.1);
      --code: #f1e6d5;
      --shadow: 0 18px 40px rgba(35,27,19,.06);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia, serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(11,110,99,.08), transparent 28%),
        linear-gradient(180deg, #f6f0e7 0%, var(--bg) 100%);
    }}
    .app {{ display: grid; grid-template-columns: 320px minmax(0, 1fr); min-height: 100vh; }}
    .sidebar {{
      border-right: 1px solid var(--border);
      background: rgba(251,247,241,.9);
      backdrop-filter: blur(6px);
      padding: 26px 22px 30px;
      position: sticky;
      top: 0;
      height: 100vh;
      overflow: auto;
    }}
    .main {{
      padding: 32px 36px 56px;
      min-width: 0;
    }}
    .sidebar-title {{
      margin: 0 0 10px;
      font-size: 28px;
      line-height: 1.05;
      letter-spacing: -.02em;
    }}
    .sidebar-kicker {{
      margin: 0 0 18px;
      color: var(--text-dim);
      font-size: 13px;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin: 16px 0 26px;
    }}
    .card {{
      background: var(--surface-3);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px 14px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.65);
    }}
    .card strong {{
      display: block;
      margin-bottom: 4px;
      font-size: 22px;
      line-height: 1;
      font-weight: 700;
    }}
    .tabs, .subnav {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 18px; }}
    button {{
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 999px;
      cursor: pointer;
    }}
    .tabs {{
      position: sticky;
      top: 0;
      z-index: 5;
      padding: 10px 0 14px;
      background: linear-gradient(180deg, rgba(239,231,218,.97) 65%, rgba(239,231,218,0));
    }}
    .tabs button {{
      padding: 10px 14px;
      background: rgba(255,253,248,.8);
      box-shadow: 0 8px 20px rgba(35,27,19,.04);
    }}
    .tabs button.active {{
      background: linear-gradient(180deg, rgba(11,110,99,.18), rgba(11,110,99,.08));
      color: #18322d;
      border-color: rgba(11,110,99,.28);
      font-weight: 700;
    }}
    .subnav button {{
      background: transparent;
      border-color: transparent;
      border-radius: 0;
      padding: 4px 0;
      color: var(--text-dim);
      border-bottom: 1px solid transparent;
    }}
    .subnav button:hover,
    .subnav button.active {{
      color: var(--text);
      border-bottom-color: var(--border-strong);
      font-weight: 700;
    }}
    .nav-section {{ margin-top: 18px; }}
    .nav-section h3 {{
      margin: 0 0 10px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--text-dim);
    }}
    .nav-link {{
      display: block;
      width: 100%;
      text-align: left;
      margin-bottom: 4px;
      border-radius: 0;
      border: 0;
      background: transparent;
      padding: 7px 10px 7px 14px;
      border-left: 2px solid transparent;
      color: var(--text-dim);
      box-shadow: none;
    }}
    .nav-link:hover {{
      color: var(--text);
      background: rgba(255,255,255,.45);
    }}
    .nav-link.active {{
      color: var(--text);
      border-left-color: var(--accent);
      background: var(--accent-soft);
      font-weight: 700;
    }}
    .content {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 34px 42px 42px;
      min-height: 60vh;
      box-shadow: var(--shadow);
      max-width: 920px;
      margin: 0 auto;
    }}
    .pdf-panel {{
      margin-top: 18px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 18px;
      box-shadow: var(--shadow);
      max-width: 920px;
      margin-left: auto;
      margin-right: auto;
    }}
    .pdf-panel[hidden] {{ display: none; }}
    .pdf-frame {{
      width: 100%;
      height: 70vh;
      border: 0;
      border-radius: 12px;
      background: #fff;
    }}
    .source-context {{
      margin-top: 12px;
      background: var(--surface-2);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px 16px;
    }}
    .source-context[hidden] {{ display: none; }}
    .source-context h3 {{
      margin: 0 0 10px;
      font-size: 15px;
      text-transform: uppercase;
      letter-spacing: .08em;
      color: var(--text-dim);
    }}
    .source-context p {{
      margin: 0;
      white-space: pre-wrap;
    }}
    .content-meta {{
      margin-bottom: 22px;
      color: var(--text-dim);
      font-size: 12px;
      letter-spacing: .09em;
      text-transform: uppercase;
    }}
    .markdown {{
      line-height: 1.72;
      font-size: 19px;
      max-width: 42rem;
    }}
    .markdown h1, .markdown h2, .markdown h3 {{
      line-height: 1.12;
      letter-spacing: -.02em;
      color: #17110c;
    }}
    .markdown h1 {{
      margin: 0 0 18px;
      font-size: 2.2rem;
    }}
    .markdown h2 {{
      margin: 2.25rem 0 .85rem;
      padding-top: .35rem;
      font-size: 1.32rem;
      border-top: 1px solid rgba(188,168,139,.4);
    }}
    .markdown h3 {{
      margin: 1.6rem 0 .65rem;
      font-size: 1.06rem;
      color: var(--accent-2);
      text-transform: uppercase;
      letter-spacing: .06em;
    }}
    .markdown p, .markdown li {{ line-height: 1.72; }}
    .markdown p {{ margin: 0 0 1.08rem; }}
    .markdown ul {{ padding-left: 1.3rem; margin: 0 0 1.3rem; }}
    .markdown li {{ margin-bottom: .55rem; }}
    .markdown pre {{
      white-space: pre-wrap;
      background: var(--code);
      border-radius: 12px;
      padding: 12px;
      overflow-x: auto;
    }}
    .markdown code {{ background: var(--code); padding: 1px 4px; border-radius: 4px; }}
    .artifact-link {{
      color: var(--accent);
      text-decoration: underline;
      text-decoration-color: rgba(15,118,110,.35);
      text-underline-offset: 3px;
      cursor: pointer;
      font-weight: 600;
    }}
    .inline-link-button {{
      all: unset;
      display: inline;
      vertical-align: baseline;
      text-align: left;
      white-space: normal;
      cursor: pointer;
    }}
    .pdf-link {{
      color: var(--accent-2);
      text-decoration: underline;
      text-decoration-color: rgba(139,94,52,.35);
      text-underline-offset: 3px;
      cursor: pointer;
      font-weight: 600;
    }}
    .simple-lede {{
      margin: 0 0 24px;
      padding: 18px 20px;
      border-radius: 18px;
      border: 1px solid var(--border);
      background: linear-gradient(180deg, rgba(11,110,99,.06), rgba(255,253,248,0));
    }}
    .simple-lede h3 {{
      margin: 0 0 10px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .1em;
      color: var(--text-dim);
    }}
    .simple-lede ul {{ margin: 0; padding-left: 1.2rem; }}
    .simple-lede li {{ margin-bottom: 8px; }}
    .backlinks {{
      margin: 0 0 20px;
      padding: 18px 20px;
      border-radius: 18px;
      border: 1px solid var(--border);
      background: var(--surface-2);
    }}
    .backlinks h3 {{
      margin: 0 0 10px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .1em;
      color: var(--text-dim);
    }}
    .backlinks p {{ margin: 9px 0; }}
    .claim-callout {{
      margin: 0 0 22px;
      padding: 22px 24px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(11,110,99,.08), rgba(255,253,248,.98));
      border: 1px solid rgba(11,110,99,.16);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.7);
    }}
    .claim-callout h3 {{
      margin: 0 0 12px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .1em;
      color: var(--text-dim);
    }}
    .claim-callout blockquote {{
      margin: 0;
      padding: 0;
      border: 0;
      font-size: 1.28rem;
      line-height: 1.45;
      font-weight: 600;
      letter-spacing: -.01em;
      color: #18211d;
    }}
    .pill {{
      display: inline-block;
      background: var(--surface-2);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 4px 8px;
      margin-right: 8px;
      margin-bottom: 8px;
      font-size: 13px;
    }}
    @media (max-width: 900px) {{
      .app {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--border); }}
      .main {{ padding: 18px 16px 30px; }}
      .content, .pdf-panel {{ padding: 22px 20px 24px; border-radius: 18px; }}
      .markdown {{ font-size: 18px; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <p class="sidebar-kicker">Parliament Dossier</p>
      <h1 class="sidebar-title" id="doc-title">Parliament Explorer</h1>
      <div id="doc-stats"></div>
      <div class="nav-section">
        <h3>Views</h3>
        <div id="view-links"></div>
      </div>
      <div class="nav-section">
        <h3>Episodes</h3>
        <div id="episode-links"></div>
      </div>
      <div class="nav-section">
        <h3>Claims</h3>
        <div id="claim-links"></div>
      </div>
      <div class="nav-section">
        <h3>References</h3>
        <div id="reference-links"></div>
      </div>
      <div class="nav-section">
        <h3>Index</h3>
        <div id="index-link"></div>
      </div>
    </aside>
    <main class="main">
      <div class="tabs" id="mode-tabs"></div>
      <div class="subnav" id="subnav"></div>
      <section class="content">
        <div class="content-meta" id="content-meta"></div>
        <div class="markdown" id="content"></div>
      </section>
      <section class="pdf-panel" id="pdf-panel" hidden>
        <div class="content-meta" id="pdf-status">PDF viewer</div>
        <iframe class="pdf-frame" id="pdf-frame" title="Source PDF viewer"></iframe>
        <section class="source-context" id="source-context" hidden>
          <h3>Source context</h3>
          <p id="source-context-text"></p>
        </section>
      </section>
    </main>
  </div>
  <script id="__PARLIAMENT_DATA__" type="application/json">{data_json}</script>
  <script>
    const data = JSON.parse(document.getElementById('__PARLIAMENT_DATA__').textContent);
    const state = {{ mode: 'level-1-simple', kind: 'view', id: 'level-1-simple' }};

    const docTitle = document.getElementById('doc-title');
    const docStats = document.getElementById('doc-stats');
    const modeTabs = document.getElementById('mode-tabs');
    const subnav = document.getElementById('subnav');
    const contentMeta = document.getElementById('content-meta');
    const content = document.getElementById('content');
    const pdfPanel = document.getElementById('pdf-panel');
    const pdfFrame = document.getElementById('pdf-frame');
    const pdfStatus = document.getElementById('pdf-status');
    const sourceContext = document.getElementById('source-context');
    const sourceContextText = document.getElementById('source-context-text');

    function slugLabel(value) {{
      return String(value || '')
        .replace(/^[a-z]+-\\d+-/, '')
        .replace(/[-_]+/g, ' ')
        .replace(/\\b\\w/g, char => char.toUpperCase());
    }}

    function escapeHtml(text) {{
      return text
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }}

    function escapeHtmlAttribute(text) {{
      return escapeHtml(String(text || ''))
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }}

    function renderMarkdown(md, currentArtifact) {{
      const escaped = escapeHtml(md);
      const rendered = escaped
        .replace(/^### (.*)$/gm, '<h3>$1</h3>')
        .replace(/^## (.*)$/gm, '<h2>$1</h2>')
        .replace(/^# (.*)$/gm, '<h1>$1</h1>')
        .replace(/^- (.*)$/gm, '<li>$1</li>')
        .replace(/(?:<li>.*<\\/li>\\n?)+/g, match => '<ul>' + match + '</ul>')
        .replace(/\\n\\n+/g, '</p><p>')
        .replace(/^(?!<h|<ul|<li|<p)(.+)$/gm, '<p>$1</p>')
        .replace(/<p><\\/p>/g, '');
      return linkPdfMarkers(linkArtifactMentions(rendered, currentArtifact));
    }}

    function navigateToArtifact(kind, id) {{
      const changedArtifact = state.kind !== kind || state.id !== id;
      state.kind = kind;
      state.id = id;
      if (kind === 'view') state.mode = id;
      if (changedArtifact) resetPdfPreview();
      window.location.hash = routeForArtifact(kind, id);
      render();
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    function routeForArtifact(kind, id) {{
      return '#' + encodeURIComponent(kind) + '/' + encodeURIComponent(id);
    }}

    function applyHashRoute() {{
      const raw = window.location.hash.replace(/^#/, '');
      if (!raw || !raw.includes('/')) return false;
      const [kindPart, ...idParts] = raw.split('/');
      const kind = decodeURIComponent(kindPart || '');
      const id = decodeURIComponent(idParts.join('/') || '');
      if (!kind || !id) return false;
      state.kind = kind;
      state.id = id;
      if (kind === 'view') state.mode = id;
      return true;
    }}

    function normalizeWhitespace(text) {{
      return (text || '').replace(/\\s+/g, ' ').trim();
    }}

    function parsePageNumbers(text) {{
      const source = String(text || '');
      const pages = [];
      [...source.matchAll(/(\\d+)\\s*[-–]\\s*(\\d+)/g)].forEach(match => {{
        const start = Number(match[1]);
        const end = Number(match[2]);
        if (!start || !end) return;
        const low = Math.min(start, end);
        const high = Math.max(start, end);
        for (let page = low; page <= high; page += 1) pages.push(page);
      }});
      const singles = source.match(/\\d+/g) || [];
      singles.forEach(value => pages.push(Number(value)));
      return [...new Set(pages.filter(Boolean))].sort((a, b) => a - b);
    }}

    function extractParagraphs(pageText) {{
      return String(pageText || '')
        .split(/\\n+/)
        .map(line => line.trim())
        .filter(line =>
          line &&
          !/^#/.test(line) &&
          !/^\\*\\*/.test(line) &&
          !/^_.*_$/.test(line) &&
          !/^\\d+$/.test(line) &&
          line.length > 40
        );
    }}

    function scoreParagraph(paragraph, queryTerms) {{
      const haystack = normalizeWhitespace(paragraph).toLowerCase();
      return queryTerms.reduce((score, term) => score + (haystack.includes(term) ? 1 : 0), 0);
    }}

    function pickSourceContext(pages, query) {{
      if (!pages.length) return null;
      const queryTerms = normalizeWhitespace(query)
        .toLowerCase()
        .split(/[^\\p{{L}}\\p{{N}}]+/u)
        .filter(term => term.length >= 4);
      let best = null;
      pages.forEach(page => {{
        extractParagraphs(page.text).forEach(paragraph => {{
          const score = scoreParagraph(paragraph, queryTerms);
          if (!best || score > best.score || (score === best.score && paragraph.length > best.paragraph.length)) {{
            best = {{ page_number: page.page_number, paragraph, score }};
          }}
        }});
      }});
      if (best && (best.score > 0 || pages.length === 1)) return best;
      const fallbackPage = pages[0];
      const fallbackParagraph = extractParagraphs(fallbackPage.text)[0] || normalizeWhitespace(fallbackPage.text).slice(0, 700);
      return fallbackParagraph ? {{ page_number: fallbackPage.page_number, paragraph: fallbackParagraph, score: 0 }} : null;
    }}

    function showSourceContext(page, label, query) {{
      const targetPage = Number(page);
      const pageNumbers = [targetPage];
      const pages = data.document.pages.filter(item => pageNumbers.includes(Number(item.page_number)));
      const match = pickSourceContext(pages, query || label || '');
      if (!match) {{
        sourceContext.hidden = true;
        sourceContextText.textContent = '';
        return;
      }}
      sourceContext.hidden = false;
      sourceContextText.textContent = `Page ${{match.page_number}} · ${{match.paragraph}}`;
    }}

    function resetPdfPreview() {{
      pdfPanel.hidden = true;
      pdfFrame.removeAttribute('src');
      pdfStatus.textContent = 'PDF viewer';
      sourceContext.hidden = true;
      sourceContextText.textContent = '';
    }}

    function openPdfAtPage(page, label, query) {{
      if (!data.document.source_pdf) return;
      pdfFrame.src = data.document.source_pdf + '#page=' + page + '&zoom=page-width&navpanes=0&toolbar=0&pagemode=none';
      pdfStatus.textContent = 'PDF · page ' + page + (label ? ' · ' + label : '');
      showSourceContext(page, label, query);
      pdfPanel.hidden = false;
      pdfPanel.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    }}

    function escapeForRegExp(value) {{
      return value.replace(/[.*+?^$()|[\\]\\\\]/g, '\\\\$&');
    }}

    function shortIdForClaim(id) {{
      const match = id.match(/^(clm-\\d{{4}})/);
      return match ? match[1] : id;
    }}

    function renderInlineCitationClusters(rawBody) {{
      return rawBody
        .replace(/\\((claims?|references?)\\s+([^)]+)\\)/gi, (match, kind, inner) => {{
          const cleaned = inner.replace(/\\s*;\\s*/g, ', ').trim();
          return `(Fontes: ${{cleaned}})`;
        }})
        .replace(/\\((claims?)\\s+de\\s+([^)]+)\\)/gi, (match, kind, inner) => {{
          return `(Afirmações mencionadas: ${{inner.trim()}})`;
        }});
    }}

    function linkArtifactMentions(html, currentArtifact) {{
      const replacements = [];
      data.claims.forEach(item => replacements.push({{ mention: item.id, targetId: item.id, kind: 'claim', label: item.title }}));
      data.claims.forEach(item => replacements.push({{ mention: shortIdForClaim(item.id), targetId: item.id, kind: 'claim', label: item.title }}));
      data.claims.forEach(item => replacements.push({{ mention: item.title, targetId: item.id, kind: 'claim', label: item.title }}));
      data.references.forEach(item => replacements.push({{ mention: item.id, targetId: item.id, kind: 'reference', label: item.title }}));
      data.references.forEach(item => replacements.push({{ mention: item.title, targetId: item.id, kind: 'reference', label: item.title }}));
      data.episodes.forEach(item => replacements.push({{ mention: item.id, targetId: item.id, kind: 'episode', label: item.title }}));
      data.episodes.forEach(item => replacements.push({{ mention: item.title, targetId: item.id, kind: 'episode', label: item.title }}));
      replacements.sort((a, b) => b.mention.length - a.mention.length);
      let linked = html;
      replacements.forEach(({{ mention, targetId, kind, label: rawLabel }}) => {{
        if (currentArtifact && currentArtifact.kind === kind && currentArtifact.id === targetId) return;
        const label = escapeHtml(rawLabel || mention);
        const pattern = new RegExp('(^|[^\\\\w-])(' + escapeForRegExp(mention) + ')(?=[^\\\\w-]|$)', 'g');
        linked = linked.replace(pattern, (match, prefix) => {{
          return `${{prefix}}<button type="button" class="artifact-link inline-link-button" data-kind="${{kind}}" data-id="${{targetId}}">${{label}}</button>`;
        }});
      }});
      return linked;
    }}

    function buildSimpleLede(rawBody) {{
      const cleaned = rawBody
        .split('\\n')
        .filter(line => !line.startsWith('#'))
        .join('\\n')
        .split(/\\n\\s*\\n/)
        .map(part => part.trim())
        .filter(Boolean)
        .slice(0, 3)
        .map(part => part.replace(/^[-*]\\s+/, '').replace(/\\s+/g, ' ').trim())
        .map(part => part.length > 220 ? part.slice(0, 217).trim() + '…' : part);
      if (!cleaned.length) return '';
      return `<section class="simple-lede"><h3>Quick Take</h3><ul>${{cleaned.map(item => `<li>${{escapeHtml(item)}}</li>`).join('')}}</ul></section>`;
    }}

    function linkPdfMarkers(html) {{
      return html.replace(/\\[\\[pdf:(\\d+)\\|([^\\]|]+)(?:\\|([^\\]]+))?\\]\\]/g, (match, page, label, query) => {{
        const labelAttr = escapeHtmlAttribute(label);
        const queryAttr = escapeHtmlAttribute(query || '');
        return `<button type="button" class="pdf-link inline-link-button" data-page="${{page}}" data-label="${{labelAttr}}" data-query="${{queryAttr}}">${{label}}</button>`;
      }});
    }}

    function renderImportantClaimsSection(rawBody) {{
      const match = rawBody.match(/## Important claims\\n+([\\s\\S]*?)(\\n## |$)/);
      if (!match) return rawBody;
      const block = match[1].trim();
      const items = [...block.matchAll(/'claim': '([^']+)'(?:, 'by': '([^']+)')?(?:, 'importance': '([^']+)')?(?:, 'evidence_pointers': '([^']+)')?/g)]
        .map(matchItem => {{
          return {{
            claim: matchItem[1] || '',
            by: matchItem[2] || '',
            evidence: matchItem[4] || '',
          }};
        }})
        .filter(item => item.claim);
      if (!items.length) return rawBody;
      const listMarkdown = items.map(item => {{
        const meta = [item.by, item.evidence].filter(Boolean).join(' · ');
        return '- ' + item.claim + (meta ? ' (' + meta + ')' : '');
      }}).join('\\n');
      const tail = match[2].startsWith('\\n## ') ? match[2].slice(1) : '';
      return rawBody.replace(match[0], `## Important claims\\n\\n${{listMarkdown}}\\n\\n${{tail}}`);
    }}

    function renderEvidencePointersSection(rawBody) {{
      const match = rawBody.match(/## Evidence pointers\\n+([\\s\\S]*?)(\\n## |$)/);
      if (!match) return rawBody;
      const lines = match[1]
        .split('\\n')
        .map(line => line.trim())
        .filter(Boolean)
        .map(line => {{
          const text = line.replace(/^-\\s*/, '');
          const pageMatch = text.match(/(?:pp?\\.?|Page)\\s*(\\d+)/i);
          if (!pageMatch) return '- ' + text;
          const query = text.includes(':') ? text.split(':').slice(1).join(':').trim() : text;
          return '- [[pdf:' + pageMatch[1] + '|' + text + '|' + query + ']]';
        }})
        .join('\\n');
      const tail = match[2].startsWith('\\n## ') ? match[2].slice(1) : '';
      return rawBody.replace(match[0], `## Evidence pointers\\n\\n${{lines}}\\n\\n${{tail}}`);
    }}

    function renderExternalReferencesSection(rawBody) {{
      const match = rawBody.match(/## External references to check\\n+([\\s\\S]*?)(\\n## |$)/);
      if (!match) return rawBody;
      const items = match[1]
        .split(';')
        .map(item => item.trim())
        .filter(Boolean)
        .map(item => '- ' + item)
        .join('\\n');
      const tail = match[2].startsWith('\\n## ') ? match[2].slice(1) : '';
      return rawBody.replace(match[0], `## External references to check\\n\\n${{items}}\\n\\n${{tail}}`);
    }}

    function renderPartyPositionsSection(rawBody) {{
      const match = rawBody.match(/## Party positions or reactions\\n+([\\s\\S]*?)(\\n## |$)/);
      if (!match) return rawBody;
      const raw = match[1].trim();
      const dictItems = [...raw.matchAll(/([A-Z-]+):\\s*\\{{'temas':\\s*\\[([^\\]]*)\\]\\}}/g)];
      const items = dictItems.length
        ? dictItems
            .map(([, party, themes]) => {{
              const cleanedThemes = themes
                .split(/',\\s*'|",\\s*"/)
                .map(item => item.replace(/^['"]|['"]$/g, '').trim())
                .filter(Boolean);
              return cleanedThemes.length
                ? '- ' + party + ': ' + cleanedThemes.join('; ')
                : '- ' + party;
            }})
            .join('\\n')
        : raw
            .split(';')
            .map(item => item.trim())
            .filter(Boolean)
            .map(item => '- ' + item)
            .join('\\n');
      const tail = match[2].startsWith('\\n## ') ? match[2].slice(1) : '';
      return rawBody.replace(match[0], `## Party positions or reactions\\n\\n${{items}}\\n\\n${{tail}}`);
    }}

    function renderSourceMentionSection(rawBody, query) {{
      const match = rawBody.match(/## Source mention\\n+([\\s\\S]*?)(\\n## |$)/);
      if (!match) return rawBody;
      const text = match[1].trim();
      const pageMatch = text.match(/(?:pp?\\.?|Page)\\s*(\\d+)/i);
      const rendered = pageMatch ? `[[pdf:${{pageMatch[1]}}|${{text}}|${{query || text}}]]` : text;
      const tail = match[2].startsWith('\\n## ') ? match[2].slice(1) : '';
      return rawBody.replace(match[0], `## Source mention\\n\\n${{rendered}}\\n\\n${{tail}}`);
    }}

    function removeMarkdownSection(rawBody, title) {{
      const pattern = new RegExp(`## ${{title}}\\n+[\\s\\S]*?(?=\\n## |$)`, 'm');
      return rawBody.replace(pattern, '').replace(/\\n{{3,}}/g, '\\n\\n').trim();
    }}

    function extractMarkdownSection(rawBody, title) {{
      const pattern = new RegExp(`## ${{title}}\\n+([\\s\\S]*?)(?=\\n## |$)`, 'm');
      const match = rawBody.match(pattern);
      return match ? match[1].trim() : '';
    }}

    function buildClaimBacklinks(current) {{
      if (state.kind !== 'claim') return '';
      const metadata = current.metadata || {{}};
      const bits = [];
      const attribution = [metadata.speaker, metadata.party]
        .filter(Boolean)
        .filter(value => String(value).trim().toLowerCase() !== 'none');
      if (attribution.length) {{
        bits.push(`<p><strong>Attribution</strong>: ${{
          attribution.map(escapeHtml).join(' · ')
        }}</p>`);
      }}
      if (metadata.episode && metadata.episode.id) {{
        bits.push(`<p><strong>Episode</strong>: <button type="button" class="artifact-link inline-link-button" data-kind="episode" data-id="${{metadata.episode.id}}">${{escapeHtml(metadata.episode.id)}}</button></p>`);
      }}
      if (Array.isArray(metadata.references) && metadata.references.length) {{
        const refs = metadata.references
          .map(ref => `<button type="button" class="artifact-link inline-link-button" data-kind="reference" data-id="${{ref.id}}">${{escapeHtml(ref.id)}}</button>`)
          .join(', ');
        bits.push(`<p><strong>References</strong>: ${{refs}}</p>`);
      }}
      if (!bits.length) return '';
      return `<section class="backlinks"><h3>Attribution & Backlinks</h3>${{bits.join('')}}</section>`;
    }}

    function buildClaimSourcePreview(current) {{
      if (state.kind !== 'claim') return '';
      const context = current.metadata?.source_context;
      if (!context?.page_number) return '';
      const query = [current.title, current.metadata?.speaker].filter(Boolean).join(' ');
      const excerptBlock = context.excerpt
        ? `<p>${{escapeHtml(context.excerpt)}}</p>`
        : `<p><em>Exact claim sentence not found in the extracted text for ${{escapeHtml(context.source_mention || 'this page range')}}. Open the PDF to inspect the original passage.</em></p>`;
      return `
        <section class="backlinks">
          <h3>Claim Context</h3>
          <p><button type="button" class="pdf-link inline-link-button" data-page="${{context.page_number}}" data-label="${{escapeHtmlAttribute(context.source_mention || 'Source mention')}}" data-query="${{escapeHtmlAttribute(query)}}">Open page ${{context.page_number}} in PDF</button></p>
          ${{excerptBlock}}
        </section>
      `;
    }}

    function buildClaimStatement(current) {{
      if (state.kind !== 'claim') return '';
      const claimText = extractMarkdownSection(current.body || '', 'Claim');
      if (!claimText) return '';
      return `
        <section class="claim-callout">
          <h3>Claim</h3>
          <blockquote>${{escapeHtml(claimText.replace(/\\s+/g, ' ').trim())}}</blockquote>
        </section>
      `;
    }}

    function setButtons(container, items, onClick) {{
      container.innerHTML = '';
      items.forEach(item => {{
        const button = document.createElement('button');
        button.className = 'nav-link';
        button.textContent = item.title;
        if (state.kind === item.kind && state.id === item.id) {{
          button.classList.add('active');
        }}
        button.onclick = () => onClick(item);
        container.appendChild(button);
      }});
    }}

    function setMode(modeId) {{
      const changedArtifact = state.kind !== 'view' || state.id !== modeId;
      state.mode = modeId;
      state.kind = 'view';
      state.id = modeId;
      if (changedArtifact) resetPdfPreview();
      render();
    }}

    function findCurrent() {{
      const maps = {{
        view: data.views,
        episode: data.episodes,
        claim: data.claims,
        reference: data.references,
        index: [data.index],
      }};
      return (maps[state.kind] || []).find(item => item.id === state.id);
    }}

    function render() {{
      docTitle.textContent = data.document.title || data.document.document_id;
      docStats.innerHTML = `
        <div class="card"><strong>${{data.document.page_count || 0}}</strong><br>pages</div>
        <div class="card"><strong>${{data.counts.episodes}}</strong><br>episodes</div>
        <div class="card"><strong>${{data.counts.claims}}</strong><br>claims</div>
        <div class="card"><strong>${{data.counts.references}}</strong><br>references</div>
      `;

      modeTabs.innerHTML = '';
      [
        ['level-1-simple', 'Simple'],
        ['level-2-standard', 'Standard'],
        ['level-3-detailed', 'Detailed'],
      ].forEach(([id, label]) => {{
        const button = document.createElement('button');
        button.textContent = label;
        button.className = state.mode === id && state.kind === 'view' && state.id === id ? 'active' : '';
        button.onclick = () => setMode(id);
        modeTabs.appendChild(button);
      }});

      subnav.innerHTML = '';
      [
        ['Overview', () => {{ state.kind='view'; state.id=state.mode; render(); }}],
        ['Episodes', () => {{ if (data.episodes[0]) {{ state.kind='episode'; state.id=data.episodes[0].id; render(); }} }}],
        ['Claims', () => {{ if (data.claims[0]) {{ state.kind='claim'; state.id=data.claims[0].id; render(); }} }}],
        ['References', () => {{ if (data.references[0]) {{ state.kind='reference'; state.id=data.references[0].id; render(); }} }}],
        ['Index', () => {{ state.kind='index'; state.id='index'; render(); }}],
      ].forEach(([label, handler]) => {{
        const button = document.createElement('button');
        button.textContent = label;
        const active =
          (label === 'Overview' && state.kind === 'view') ||
          (label === 'Episodes' && state.kind === 'episode') ||
          (label === 'Claims' && state.kind === 'claim') ||
          (label === 'References' && state.kind === 'reference') ||
          (label === 'Index' && state.kind === 'index');
        if (active) button.className = 'active';
        button.onclick = handler;
        subnav.appendChild(button);
      }});

      setButtons(document.getElementById('view-links'), data.views.map(item => ({{ ...item, kind: 'view' }})), item => {{ state.kind='view'; state.id=item.id; render(); }});
      setButtons(document.getElementById('episode-links'), data.episodes.map(item => ({{ ...item, kind: 'episode' }})), item => {{ state.kind='episode'; state.id=item.id; render(); }});
      setButtons(document.getElementById('claim-links'), data.claims.map(item => ({{ ...item, kind: 'claim' }})), item => {{ state.kind='claim'; state.id=item.id; render(); }});
      setButtons(document.getElementById('reference-links'), data.references.map(item => ({{ ...item, kind: 'reference' }})), item => {{ state.kind='reference'; state.id=item.id; render(); }});
      setButtons(document.getElementById('index-link'), [{{ ...data.index, kind: 'index' }}], item => {{ state.kind='index'; state.id=item.id; render(); }});

      const current = findCurrent() || data.views[0] || data.index;
      const currentArtifact = {{ kind: state.kind, id: current.id }};
      const metaBits = [slugLabel(current.type || state.kind), slugLabel(current.id)];
      if (current.generation && current.generation.estimated_cost_usd !== undefined) {{
        metaBits.push(`cost $${{Number(current.generation.estimated_cost_usd).toFixed(4)}}`);
      }}
      contentMeta.textContent = metaBits.filter(Boolean).join(' · ');
      const rawBody = state.kind === 'episode'
        ? renderInlineCitationClusters(renderPartyPositionsSection(renderExternalReferencesSection(renderEvidencePointersSection(renderImportantClaimsSection(current.body || '')))))
        : state.kind === 'claim'
          ? renderInlineCitationClusters(renderSourceMentionSection(current.body || '', [current.title, current.metadata?.speaker].filter(Boolean).join(' ')))
          : renderInlineCitationClusters(current.body || '');
      const cleanedBody = state.kind === 'claim'
        ? removeMarkdownSection(removeMarkdownSection(rawBody, 'Claim'), 'Source mention')
        : rawBody;
      const simpleLede = state.kind === 'view' && state.id === 'level-1-simple' ? buildSimpleLede(rawBody) : '';
      const backlinks = buildClaimBacklinks(current);
      const claimStatement = buildClaimStatement(current);
      const claimSourcePreview = buildClaimSourcePreview(current);
      content.innerHTML = backlinks + claimStatement + claimSourcePreview + simpleLede + renderMarkdown(cleanedBody, currentArtifact);
      content.querySelectorAll('.artifact-link').forEach(link => {{
        link.addEventListener('click', event => {{
          event.preventDefault();
          navigateToArtifact(link.dataset.kind, link.dataset.id);
        }});
      }});
      content.querySelectorAll('.pdf-link').forEach(link => {{
        link.addEventListener('click', event => {{
          event.preventDefault();
          openPdfAtPage(link.dataset.page, link.dataset.label, link.dataset.query || '');
        }});
      }});
    }}

    window.addEventListener('hashchange', () => {{
      applyHashRoute();
      render();
    }});

    applyHashRoute();
    render();
  </script>
</body>
</html>
"""


def write_explorer_html(document_root: Path) -> Path:
    payload = build_explorer_payload(document_root)
    output_path = document_root / "explorer.html"
    output_path.write_text(build_explorer_html(payload))
    return output_path


def _artifact_record(
    path: Path,
    *,
    id_key: str,
    source_pages: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    frontmatter, body = _split_frontmatter(path.read_text())
    metadata = yaml.safe_load(frontmatter) or {}
    if metadata.get("artifact_type") == "claim" and source_pages:
        context = _claim_source_context(metadata, body, source_pages)
        if context:
            metadata["source_context"] = context
    return {
        "id": metadata.get(id_key, path.stem),
        "title": metadata.get("title", path.stem),
        "type": metadata.get("artifact_type", ""),
        "body": body.strip(),
        "metadata": metadata,
        "generation": metadata.get("generation", {}),
        "path": path.name,
    }


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _source_pdf_relpath(document_root: Path) -> str | None:
    pdfs = sorted((document_root / "source").glob("*.pdf"))
    if not pdfs:
        return None
    return f"source/{pdfs[0].name}"


def _split_frontmatter(raw: str) -> tuple[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid markdown artifact frontmatter: {raw[:80]!r}")
    return match.group(1), match.group(2)


def _claim_source_context(
    metadata: dict[str, object],
    body: str,
    source_pages: list[dict[str, object]],
) -> dict[str, object] | None:
    match = re.search(r"^## Source mention\n(.*?)(?:\n## |\Z)", body, re.DOTALL | re.MULTILINE)
    if not match:
        return None
    source_mention = match.group(1).strip()
    page_numbers = _parse_page_numbers(source_mention)
    if not page_numbers:
        return None
    pages = [
        page for page in source_pages
        if int(page.get("page_number", 0) or 0) in page_numbers
    ]
    if not pages:
        return None
    claim_text = _claim_text(body) or str(metadata.get("title") or "")
    claim_terms = _query_terms(claim_text)
    speaker_terms = _query_terms(str(metadata.get("speaker") or ""))
    excerpt_page, excerpt, claim_score, total_score = _pick_source_excerpt(pages, claim_terms, speaker_terms)
    if not excerpt_page:
        return None
    if not excerpt or claim_score < _minimum_claim_match_score(claim_terms):
        return {
            "page_number": excerpt_page,
            "source_mention": source_mention,
            "excerpt": None,
            "status": "not_found",
        }
    return {
        "page_number": excerpt_page,
        "source_mention": source_mention,
        "excerpt": excerpt,
        "status": "matched",
    }


def _parse_page_numbers(text: str) -> list[int]:
    pages: set[int] = set()
    for start, end in re.findall(r"(\d+)\s*[-–]\s*(\d+)", text):
        low = min(int(start), int(end))
        high = max(int(start), int(end))
        pages.update(range(low, high + 1))
    pages.update(int(match) for match in re.findall(r"\d+", text))
    return sorted(pages)


def _query_terms(text: str) -> list[str]:
    return [term for term in re.split(r"[^\wÀ-ÿ]+", text.lower()) if len(term) >= 4]


def _claim_text(body: str) -> str | None:
    match = re.search(r"^## Claim\n(.*?)(?:\n## |\Z)", body, re.DOTALL | re.MULTILINE)
    if not match:
        return None
    return " ".join(line.strip() for line in match.group(1).splitlines() if line.strip())


def _extract_paragraphs(page_text: str) -> list[str]:
    paragraphs: list[str] = []
    for line in page_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("**") or re.fullmatch(r"\d+", stripped):
            continue
        if stripped.startswith("_") and stripped.endswith("_"):
            continue
        if len(stripped) <= 40:
            continue
        paragraphs.append(stripped)
    return paragraphs


def _minimum_claim_match_score(claim_terms: list[str]) -> int:
    if not claim_terms:
        return 1
    return max(2, min(4, len(set(claim_terms)) // 2 or 1))


def _pick_source_excerpt(
    pages: list[dict[str, object]],
    claim_terms: list[str],
    speaker_terms: list[str],
) -> tuple[int | None, str | None, int, int]:
    best_page: int | None = None
    best_excerpt: str | None = None
    best_score = -1
    best_claim_score = 0
    for page in pages:
        page_number = int(page.get("page_number", 0) or 0)
        for paragraph in _extract_paragraphs(str(page.get("text", ""))):
            haystack = paragraph.lower()
            claim_score = sum(1 for term in claim_terms if term in haystack)
            speaker_score = sum(1 for term in speaker_terms if term in haystack)
            score = claim_score * 10 + speaker_score
            if score > best_score or (score == best_score and best_excerpt and len(paragraph) > len(best_excerpt)):
                best_page = page_number
                best_excerpt = paragraph
                best_score = score
                best_claim_score = claim_score
    if best_page and best_excerpt:
        return best_page, best_excerpt, best_claim_score, best_score
    first_page = pages[0]
    first_page_number = int(first_page.get("page_number", 0) or 0)
    paragraphs = _extract_paragraphs(str(first_page.get("text", "")))
    if paragraphs:
        return first_page_number, paragraphs[0], 0, 0
    return None, None, 0, 0
