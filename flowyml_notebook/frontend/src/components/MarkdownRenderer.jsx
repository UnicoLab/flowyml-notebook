import React, { useMemo } from 'react';
import { marked } from 'marked';
import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import javascript from 'highlight.js/lib/languages/javascript';
import bash from 'highlight.js/lib/languages/bash';
import json from 'highlight.js/lib/languages/json';
import sql from 'highlight.js/lib/languages/sql';
import yaml from 'highlight.js/lib/languages/yaml';
import xml from 'highlight.js/lib/languages/xml';
import css from 'highlight.js/lib/languages/css';
import markdown from 'highlight.js/lib/languages/markdown';
import 'highlight.js/styles/github-dark.min.css';

// Register languages
hljs.registerLanguage('python', python);
hljs.registerLanguage('py', python);
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('js', javascript);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('sh', bash);
hljs.registerLanguage('shell', bash);
hljs.registerLanguage('json', json);
hljs.registerLanguage('sql', sql);
hljs.registerLanguage('yaml', yaml);
hljs.registerLanguage('yml', yaml);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('html', xml);
hljs.registerLanguage('css', css);
hljs.registerLanguage('markdown', markdown);
hljs.registerLanguage('md', markdown);

// Configure marked
marked.setOptions({
  gfm: true,
  breaks: true,
  pedantic: false,
  highlight: (code, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value;
      } catch {}
    }
    try {
      return hljs.highlightAuto(code).value;
    } catch {}
    return code;
  },
});

// Custom renderer for premium styling
const renderer = new marked.Renderer();

renderer.code = function(code, language) {
  // Handle the new marked API where code is an object
  let codeText = typeof code === 'object' ? code.text : code;
  let lang = typeof code === 'object' ? code.lang : language;
  
  let highlighted;
  if (lang && hljs.getLanguage(lang)) {
    try {
      highlighted = hljs.highlight(codeText, { language: lang }).value;
    } catch {
      highlighted = escapeHtml(codeText);
    }
  } else {
    try {
      highlighted = hljs.highlightAuto(codeText).value;
    } catch {
      highlighted = escapeHtml(codeText);
    }
  }
  
  return `<div class="md-code-block">
    <div class="md-code-header">
      <span class="md-code-lang">${lang || 'code'}</span>
      <button class="md-code-copy" onclick="navigator.clipboard.writeText(this.parentElement.nextElementSibling.textContent)">Copy</button>
    </div>
    <pre class="md-pre"><code class="hljs">${highlighted}</code></pre>
  </div>`;
};

renderer.table = function(header, body) {
  // Handle new marked API
  const headerContent = typeof header === 'object' ? header.header : header;
  const bodyContent = typeof header === 'object' ? header.rows : body;
  
  if (typeof header === 'object' && header.header && header.rows) {
    // New marked API - header is the full table object
    let html = '<div class="md-table-wrap"><table class="md-table"><thead><tr>';
    for (const cell of header.header) {
      const align = cell.align ? ` style="text-align:${cell.align}"` : '';
      html += `<th${align}>${cell.text}</th>`;
    }
    html += '</tr></thead><tbody>';
    for (const row of header.rows) {
      html += '<tr>';
      for (const cell of row) {
        const align = cell.align ? ` style="text-align:${cell.align}"` : '';
        html += `<td${align}>${cell.text}</td>`;
      }
      html += '</tr>';
    }
    html += '</tbody></table></div>';
    return html;
  }
  
  return `<div class="md-table-wrap"><table class="md-table"><thead>${headerContent}</thead><tbody>${bodyContent}</tbody></table></div>`;
};

renderer.blockquote = function(quote) {
  const text = typeof quote === 'object' ? quote.text : quote;
  return `<blockquote class="md-blockquote">${text}</blockquote>`;
};

renderer.heading = function(text, level) {
  const content = typeof text === 'object' ? text.text : text;
  const depth = typeof text === 'object' ? text.depth : level;
  return `<h${depth} class="md-heading md-h${depth}">${content}</h${depth}>`;
};

renderer.image = function(href, title, text) {
  const src = typeof href === 'object' ? href.href : href;
  const alt = typeof href === 'object' ? href.text : text;
  const caption = typeof href === 'object' ? href.title : title;
  return `<figure class="md-figure">
    <img src="${src}" alt="${alt || ''}" class="md-image" loading="lazy" />
    ${caption ? `<figcaption class="md-caption">${caption}</figcaption>` : ''}
  </figure>`;
};

renderer.link = function(href, title, text) {
  const url = typeof href === 'object' ? href.href : href;
  const linkText = typeof href === 'object' ? href.text : text;
  const linkTitle = typeof href === 'object' ? href.title : title;
  return `<a href="${url}" class="md-link" target="_blank" rel="noopener"${linkTitle ? ` title="${linkTitle}"` : ''}>${linkText}</a>`;
};

renderer.codespan = function(text) {
  const code = typeof text === 'object' ? text.text : text;
  return `<code class="md-inline-code">${code}</code>`;
};

renderer.list = function(body, ordered) {
  const items = typeof body === 'object' ? body.items : null;
  const isOrdered = typeof body === 'object' ? body.ordered : ordered;
  const tag = isOrdered ? 'ol' : 'ul';
  
  if (items) {
    const content = items.map(item => `<li class="md-li">${item.text}</li>`).join('');
    return `<${tag} class="md-list">${content}</${tag}>`;
  }
  
  const content = typeof body === 'object' ? body.body : body;
  return `<${tag} class="md-list">${content}</${tag}>`;
};

renderer.hr = function() {
  return '<hr class="md-hr" />';
};

renderer.paragraph = function(text) {
  const content = typeof text === 'object' ? text.text : text;
  // Check for LaTeX blocks
  if (content.startsWith('$$') && content.endsWith('$$')) {
    const latex = content.slice(2, -2).trim();
    return `<div class="md-latex-block">${renderLatex(latex, true)}</div>`;
  }
  // Inline LaTeX
  const withLatex = content.replace(/\$([^$]+)\$/g, (_, tex) => renderLatex(tex, false));
  return `<p class="md-p">${withLatex}</p>`;
};

marked.use({ renderer });

function renderLatex(tex, displayMode) {
  try {
    // Dynamic import creates issues, use a simple fallback
    if (typeof window !== 'undefined' && window.katex) {
      return window.katex.renderToString(tex, { displayMode, throwOnError: false });
    }
  } catch {}
  return `<span class="md-latex ${displayMode ? 'block' : 'inline'}">${tex}</span>`;
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export default function MarkdownRenderer({ source }) {
  const html = useMemo(() => {
    try {
      return marked(source || '');
    } catch (e) {
      return `<p>${escapeHtml(source || '')}</p>`;
    }
  }, [source]);

  return (
    <div
      className="markdown-rendered"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
