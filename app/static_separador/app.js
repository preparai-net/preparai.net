// Separador de PDF — front-end
// Modo híbrido: arquivo pequeno → backend Python; grande → processado no navegador.

const $ = (id) => document.getElementById(id);

let MAX_BACKEND_BYTES = 100 * 1024 * 1024;
let currentFile = null;
let detected = { method: '—', total_pages: 0, chapters: [] };
let processingMode = 'auto';

// pdf.js worker
if (window.pdfjsLib) {
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}

// ----------- bootstrap -----------
async function loadConfig() {
  try {
    const res = await fetch('/api/separador/limits');
    const data = await res.json();
    if (data.max_backend_bytes) MAX_BACKEND_BYTES = data.max_backend_bytes;
    $('limitMb').textContent = Math.round(MAX_BACKEND_BYTES / 1024 / 1024);
  } catch (e) { /* keep default */ }
}

async function loadUser() {
  try {
    const res = await fetch('/auth/me');
    if (!res.ok) {
      location.href = '/login?next=' + encodeURIComponent(location.pathname);
      return;
    }
    const u = await res.json();
    const box = $('userBox');
    if (u.picture) box.innerHTML = `<img src="${u.picture}" alt=""><span>${escapeHtml(u.email)}</span>`;
    else box.innerHTML = `<span>${escapeHtml(u.email)}</span>`;
    if (u.is_admin) $('adminLink').style.display = 'inline-block';
  } catch (e) {
    location.href = '/login?next=' + encodeURIComponent(location.pathname);
  }
}

// ----------- helpers -----------
function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function fmtBytes(n) {
  if (n < 1024) return n + ' B';
  if (n < 1024*1024) return (n/1024).toFixed(1) + ' KB';
  if (n < 1024*1024*1024) return (n/1024/1024).toFixed(1) + ' MB';
  return (n/1024/1024/1024).toFixed(2) + ' GB';
}
function setStatus(id, msg, type) {
  const el = $(id);
  el.textContent = msg;
  el.className = 'status show ' + (type || 'info');
  if (!msg) el.classList.remove('show');
}
function clearStatus(id) { $(id).classList.remove('show'); }
function setProgress(id, pct) {
  const wrap = $(id);
  if (pct == null) { wrap.classList.remove('show'); return; }
  wrap.classList.add('show');
  $(id + 'Bar').style.width = Math.max(0, Math.min(100, pct)) + '%';
}

// ----------- file selection -----------
function showFile(file) {
  const box = $('fileBox');
  box.style.display = 'block';
  box.innerHTML = `
    <div class="file-info">
      <div>
        <div class="name">${escapeHtml(file.name)}</div>
        <div class="meta">${fmtBytes(file.size)}${file.size > MAX_BACKEND_BYTES ? ' • <b style="color:#fbbf24">processamento local (mais rápido)</b>' : ''}</div>
      </div>
      <button id="clearFileBtn">Remover</button>
    </div>`;
  $('clearFileBtn').onclick = resetAll;
  $('optionsCard').style.display = 'block';
  clearStatus('status');
}

function resetAll() {
  currentFile = null;
  detected = { method: '—', total_pages: 0, chapters: [] };
  $('fileBox').style.display = 'none';
  $('fileBox').innerHTML = '';
  $('optionsCard').style.display = 'none';
  $('previewCard').style.display = 'none';
  $('fileInput').value = '';
  clearStatus('status');
  clearStatus('genStatus');
  setProgress('progress', null);
  setProgress('genProgress', null);
}

// ----------- analyze -----------
function getMethod() {
  return document.querySelector('input[name=method]:checked').value;
}
function getProc() {
  // Sempre automático: PDFs grandes processam localmente, pequenos no servidor.
  return 'auto';
}

async function analyze() {
  if (!currentFile) return;
  const method = getMethod();
  const proc = getProc();
  let useClient;
  if (proc === 'client') useClient = true;
  else if (proc === 'server') useClient = false;
  else useClient = currentFile.size > MAX_BACKEND_BYTES;

  $('analyzeBtn').disabled = true;
  setStatus('status', 'Analisando capítulos…', 'info');
  setProgress('progress', 5);

  try {
    if (useClient) {
      detected = await analyzeClient(currentFile, method);
    } else {
      detected = await analyzeServer(currentFile, method);
    }
    setProgress('progress', 100);
    if (!detected.chapters.length) {
      setStatus('status', 'Nenhum capítulo detectado. Tente outro método ou edite manualmente abaixo.', 'error');
    } else {
      setStatus('status', `${detected.chapters.length} capítulos detectados via ${detected.method}.`, 'success');
    }
    renderPreview();
  } catch (e) {
    console.error(e);
    setStatus('status', 'Erro: ' + (e.message || e), 'error');
  } finally {
    $('analyzeBtn').disabled = false;
    setTimeout(() => setProgress('progress', null), 800);
  }
}

async function analyzeServer(file, method) {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('method', method);
  const res = await fetch('/api/separador/preview', { method: 'POST', body: fd });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || ('HTTP ' + res.status));
  return { method: data.method, total_pages: data.total_pages, chapters: data.chapters };
}

async function analyzeClient(file, method) {
  const buf = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: buf }).promise;
  const total_pages = pdf.numPages;

  let chapters = [];
  let usedMethod = method;

  async function fromBookmarks() {
    const out = [];
    const outline = await pdf.getOutline();
    if (!outline) return out;
    async function walk(items, depth) {
      for (const it of items) {
        const m = (it.title || '').match(/^(\d+)\s+(.+)$/);
        if (m && depth <= 2) {
          let pageIdx = -1;
          try {
            const dest = typeof it.dest === 'string'
              ? await pdf.getDestination(it.dest)
              : it.dest;
            if (dest && dest[0]) {
              pageIdx = await pdf.getPageIndex(dest[0]);
            }
          } catch (e) {}
          if (pageIdx >= 0) {
            out.push({ num: parseInt(m[1]), title: m[2].trim(), start: pageIdx + 1 });
          }
        }
        if (it.items && it.items.length) await walk(it.items, depth + 1);
      }
    }
    await walk(outline, 0);
    out.sort((a, b) => a.start - b.start);
    const seen = new Set();
    return out.filter(c => seen.has(c.num) ? false : (seen.add(c.num), true));
  }

  async function fromText() {
    const found = [];
    let lastNum = 0;
    const patterns = [
      /^\s*CHAPTER\s+(\d+)\s*[\.\-:]?\s*(.+)$/i,
      /^\s*Capítulo\s+(\d+)\s*[\.\-:]?\s*(.+)$/i,
      /^\s*(\d+)\s+([A-Z][A-Za-z][^\n]{2,80})$/,
    ];
    for (let i = 0; i < total_pages; i++) {
      if (i % 50 === 0) setProgress('progress', 5 + (i / total_pages) * 80);
      try {
        const page = await pdf.getPage(i + 1);
        const tc = await page.getTextContent();
        const text = tc.items.map(it => it.str).join('\n');
        const lines = text.split('\n').map(l => l.trim()).filter(Boolean).slice(0, 6);
        for (const ln of lines) {
          let matched = false;
          for (const pat of patterns) {
            const m = ln.match(pat);
            if (m) {
              const num = parseInt(m[1]);
              if (num !== lastNum + 1) continue;
              const title = m[2].trim().replace(/[\.,:]+$/, '').trim();
              if (title.length >= 2 && title.length <= 200) {
                found.push({ num, title, start: i + 1 });
                lastNum = num;
                matched = true;
                break;
              }
            }
          }
          if (matched) break;
        }
      } catch (e) {}
    }
    return found;
  }

  if (method === 'bookmarks' || method === 'auto') {
    chapters = await fromBookmarks();
    usedMethod = 'bookmarks';
    if (method === 'auto' && chapters.length < 2) {
      chapters = await fromText();
      usedMethod = 'regex';
    }
  } else {
    chapters = await fromText();
    usedMethod = 'regex';
  }

  for (let i = 0; i < chapters.length; i++) {
    chapters[i].end = (i + 1 < chapters.length) ? chapters[i+1].start - 1 : total_pages;
  }
  return { method: usedMethod, total_pages, chapters };
}

// ----------- preview render -----------
function renderPreview() {
  $('previewCard').style.display = 'block';
  $('usedMethod').textContent = detected.method;
  $('totalPages').textContent = detected.total_pages;
  $('chaptersCount').textContent = detected.chapters.length;

  const tbody = $('chaptersBody');
  tbody.innerHTML = '';
  detected.chapters.forEach((c, idx) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><input type="checkbox" data-idx="${idx}" class="ch-check" checked></td>
      <td class="num">${c.num}</td>
      <td><input type="text" class="title-input" data-idx="${idx}" value="${escapeHtml(c.title)}"></td>
      <td class="pages">${c.start}-${c.end} <span class="small">(${c.end - c.start + 1}p)</span></td>`;
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll('.title-input').forEach(inp => {
    inp.addEventListener('input', e => {
      detected.chapters[+e.target.dataset.idx].title = e.target.value;
      updateFilenamePreview();
    });
  });
  tbody.querySelectorAll('.ch-check').forEach(chk => {
    chk.addEventListener('change', updateSelectedCount);
  });
  updateSelectedCount();
  updateFilenamePreview();
  $('previewCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function updateSelectedCount() {
  const n = document.querySelectorAll('.ch-check:checked').length;
  $('selectedCount').textContent = n;
}

function updateFilenamePreview() {
  const prefix = $('prefixInput').value || 'Livro';
  const maxTitle = parseInt($('maxTitleLen').value) || 80;
  const c = detected.chapters[0];
  if (!c) { $('filenamePreview').textContent = '—'; return; }
  $('filenamePreview').textContent = buildFilename(prefix, c.num, c.title, c.start, c.end, maxTitle);
}

function sanitize(name, maxLen) {
  let s = (name || '').replace(/\*/g, '');
  s = s.replace(/[\/\\:?\*"<>|]/g, '');
  s = s.replace(/\s+/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
  if (s.length > maxLen) {
    let cut = s.slice(0, maxLen);
    if (cut.includes('_')) cut = cut.slice(0, cut.lastIndexOf('_'));
    s = cut.replace(/_+$/g, '');
  }
  return s;
}
function buildFilename(prefix, num, title, start, end, maxTitle) {
  return `${sanitize(prefix, 40)}_cap${num}_${sanitize(title, maxTitle)}_pag${start}-${end}.pdf`;
}

// ----------- generate ZIP -----------
async function generateZip() {
  const selected = [];
  document.querySelectorAll('.ch-check:checked').forEach(chk => {
    selected.push(detected.chapters[+chk.dataset.idx]);
  });
  if (!selected.length) {
    setStatus('genStatus', 'Selecione ao menos um capítulo.', 'error');
    return;
  }
  const prefix = $('prefixInput').value || 'Livro';
  const maxTitle = parseInt($('maxTitleLen').value) || 80;
  const proc = getProc();
  let useClient;
  if (proc === 'client') useClient = true;
  else if (proc === 'server') useClient = false;
  else useClient = currentFile.size > MAX_BACKEND_BYTES;

  $('generateBtn').disabled = true;
  setStatus('genStatus', 'Gerando ZIP com os capítulos…', 'info');
  setProgress('genProgress', 5);

  try {
    if (useClient) {
      await generateClient(selected, prefix, maxTitle);
    } else {
      await generateServer(selected, prefix, maxTitle);
    }
    setProgress('genProgress', 100);
    setStatus('genStatus', '✅ ZIP gerado com sucesso!', 'success');
  } catch (e) {
    console.error(e);
    setStatus('genStatus', 'Erro: ' + (e.message || e), 'error');
  } finally {
    $('generateBtn').disabled = false;
    setTimeout(() => setProgress('genProgress', null), 1200);
  }
}

async function generateServer(chapters, prefix, maxTitle) {
  const fd = new FormData();
  fd.append('file', currentFile);
  fd.append('prefix', prefix);
  fd.append('max_title_len', String(maxTitle));
  fd.append('chapters_json', JSON.stringify(chapters));
  setProgress('genProgress', 30);
  const res = await fetch('/api/separador/split', { method: 'POST', body: fd });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || ('HTTP ' + res.status));
  }
  setProgress('genProgress', 80);
  const blob = await res.blob();
  download(blob, `${sanitize(prefix, 40)}_capitulos.zip`);
}

async function generateClient(chapters, prefix, maxTitle) {
  const buf = await currentFile.arrayBuffer();
  const { PDFDocument } = PDFLib;
  const src = await PDFDocument.load(buf, { ignoreEncryption: true });
  const total = src.getPageCount();
  const zip = new JSZip();

  for (let i = 0; i < chapters.length; i++) {
    const c = chapters[i];
    const start = Math.max(1, c.start);
    const end = Math.min(total, c.end);
    if (end < start) continue;
    const out = await PDFDocument.create();
    const idxs = [];
    for (let p = start - 1; p < end; p++) idxs.push(p);
    const pages = await out.copyPages(src, idxs);
    pages.forEach(p => out.addPage(p));
    const bytes = await out.save();
    const fname = buildFilename(prefix, c.num, c.title, start, end, maxTitle);
    zip.file(fname, bytes);
    setProgress('genProgress', 5 + ((i + 1) / chapters.length) * 90);
    await new Promise(r => setTimeout(r, 0));
  }

  const blob = await zip.generateAsync({ type: 'blob', compression: 'DEFLATE' });
  download(blob, `${sanitize(prefix, 40)}_capitulos.zip`);
}

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

// ----------- events -----------
function setupEvents() {
  const dz = $('dropZone');
  const inp = $('fileInput');
  dz.addEventListener('click', () => inp.click());
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('dragover'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', e => {
    e.preventDefault(); dz.classList.remove('dragover');
    const f = e.dataTransfer.files[0];
    if (f && f.type === 'application/pdf') { currentFile = f; showFile(f); }
  });
  inp.addEventListener('change', e => {
    const f = e.target.files[0];
    if (f) { currentFile = f; showFile(f); }
  });
  $('analyzeBtn').addEventListener('click', analyze);
  $('generateBtn').addEventListener('click', generateZip);
  $('resetBtn').addEventListener('click', resetAll);
  $('selectAllBtn').addEventListener('click', () => {
    document.querySelectorAll('.ch-check').forEach(c => c.checked = true);
    updateSelectedCount();
  });
  $('deselectAllBtn').addEventListener('click', () => {
    document.querySelectorAll('.ch-check').forEach(c => c.checked = false);
    updateSelectedCount();
  });
  $('prefixInput').addEventListener('input', updateFilenamePreview);
  $('maxTitleLen').addEventListener('input', updateFilenamePreview);
}

(async () => {
  await loadConfig();
  await loadUser();
  setupEvents();
})();
