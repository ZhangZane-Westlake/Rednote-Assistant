/* ═════════════════════════════════════════════════════════
   XHS Assistant — Frontend Logic
   ═════════════════════════════════════════════════════════ */

// ── Tabs ─────────────────────────────────────────────────

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'analytics') loadAnalytics();
    if (btn.dataset.tab === 'profile') loadProfile();
    if (btn.dataset.tab === 'create') loadContentHistory();
    if (btn.dataset.tab === 'settings') loadSettings();
  });
});

// ── Toast ────────────────────────────────────────────────

function toast(msg) {
  let el = document.getElementById('toast');
  if (!el) { el = document.createElement('div'); el.id = 'toast'; document.body.appendChild(el); }
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), 2500);
}

// ── Simple markdown → HTML ───────────────────────────────

function md2html(md) {
  if (!md) return '';
  let html = md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^---$/gm, '<hr>')
    .replace(/^[*-] (.+)$/gm, '<li>$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/\n{2,}/g, '\n\n')
    .split('\n\n').map(para => {
      para = para.trim();
      if (!para) return '';
      if (para.match(/^<h[1-4]>/) || para === '<hr>' || para.match(/^<li>/) || para.match(/^<blockquote>/)) return para;
      if (para.match(/^<li>/)) return '<ul>' + para + '</ul>';
      return '<p>' + para + '</p>';
    }).join('\n')
    .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
    .replace(/<\/ul>\s*<ul>/g, '');

  return html;
}


// ═══════════════════════════════════════════════════════════
//  Notes CRUD
// ═══════════════════════════════════════════════════════════

async function loadNotes() {
  const resp = await fetch('/api/notes');
  const notes = await resp.json();
  document.getElementById('note-count').textContent = `共 ${notes.length} 篇`;

  const list = document.getElementById('notes-list');
  if (!notes.length) {
    list.innerHTML = '<div class="card" style="text-align:center;color:var(--text-light)">还没有笔记，点击「＋ 添加笔记」开始吧 📕</div>';
    return;
  }

  list.innerHTML = notes.map(n => `
    <div class="note-item">
      <div class="note-info">
        <div class="title">${esc(n.title)}</div>
        <div class="meta">
          ${n.topics ? n.topics.split(/[#,，]/).map(t => t.trim()).filter(Boolean).map(t => `<span class="badge">${esc(t)}</span>`).join(' ') : ''}
          <span>${n.content_type === 'video' ? '🎬 视频' : '🖼️ 图文'}</span>
          <span>${n.publish_date || '无日期'}</span>
        </div>
        <div class="note-stats">
          <span>阅读 ${fmt(n.views)}</span>
          <span>👍 ${fmt(n.likes)}</span>
          <span>⭐ ${fmt(n.saves)}</span>
          <span>💬 ${fmt(n.comments)}</span>
        </div>
      </div>
      <div class="note-actions">
        <button onclick="editNote(${n.id})">✏️ 编辑</button>
        <button onclick="deleteNote(${n.id})" style="color:#e03131;border-color:#e03131">🗑</button>
      </div>
    </div>
  `).join('');
}

function esc(s) { return String(s).replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function fmt(n) { return n >= 10000 ? (n/10000).toFixed(1)+'w' : n; }

document.getElementById('btn-add-note').addEventListener('click', () => {
  document.getElementById('form-title').textContent = '添加笔记';
  document.getElementById('note-id').value = '';
  clearForm();
  document.getElementById('note-form').style.display = 'block';
  document.getElementById('f-title').focus();
});

document.getElementById('btn-cancel-note').addEventListener('click', () => {
  document.getElementById('note-form').style.display = 'none';
});

document.getElementById('btn-save-note').addEventListener('click', async () => {
  const id = document.getElementById('note-id').value;
  const data = {
    title: document.getElementById('f-title').value.trim(),
    topics: document.getElementById('f-topics').value.trim(),
    content_type: document.getElementById('f-type').value,
    publish_date: document.getElementById('f-date').value,
    text_content: document.getElementById('f-text').value.trim(),
    image_description: document.getElementById('f-images').value.trim(),
    views: parseInt(document.getElementById('f-views').value) || 0,
    likes: parseInt(document.getElementById('f-likes').value) || 0,
    saves: parseInt(document.getElementById('f-saves').value) || 0,
    comments: parseInt(document.getElementById('f-comments').value) || 0,
    shares: parseInt(document.getElementById('f-shares').value) || 0,
    notes: document.getElementById('f-notes').value.trim(),
  };

  if (!data.title) { toast('标题不能为空'); return; }

  const url = id ? `/api/notes/${id}` : '/api/notes';
  const method = id ? 'PUT' : 'POST';
  const resp = await fetch(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });

  if (!resp.ok) { toast('保存失败'); return; }

  document.getElementById('note-form').style.display = 'none';
  toast(id ? '已更新' : '已添加');
  loadNotes();
});

async function editNote(id) {
  const resp = await fetch('/api/notes');
  const notes = await resp.json();
  const n = notes.find(x => x.id === id);
  if (!n) return;

  document.getElementById('form-title').textContent = '编辑笔记';
  document.getElementById('note-id').value = n.id;
  document.getElementById('f-title').value = n.title;
  document.getElementById('f-topics').value = n.topics;
  document.getElementById('f-type').value = n.content_type;
  document.getElementById('f-date').value = n.publish_date;
  document.getElementById('f-text').value = n.text_content;
  document.getElementById('f-images').value = n.image_description;
  document.getElementById('f-views').value = n.views;
  document.getElementById('f-likes').value = n.likes;
  document.getElementById('f-saves').value = n.saves;
  document.getElementById('f-comments').value = n.comments;
  document.getElementById('f-shares').value = n.shares;
  document.getElementById('f-notes').value = n.notes;
  document.getElementById('note-form').style.display = 'block';
  document.getElementById('f-title').focus();
}

async function deleteNote(id) {
  if (!confirm('确定删除这篇笔记吗？')) return;
  await fetch(`/api/notes/${id}`, { method: 'DELETE' });
  toast('已删除');
  loadNotes();
}

function clearForm() {
  ['f-title','f-topics','f-date','f-text','f-images','f-notes'].forEach(x => document.getElementById(x).value = '');
  ['f-views','f-likes','f-saves','f-comments','f-shares'].forEach(x => document.getElementById(x).value = '0');
  document.getElementById('f-type').value = 'photo';
  const noteFiles = document.getElementById('note-image-files');
  if (noteFiles) noteFiles.value = '';
}

async function describeSelectedImages(fileInputId, targetTextareaId, buttonId) {
  const input = document.getElementById(fileInputId);
  const target = document.getElementById(targetTextareaId);
  const btn = document.getElementById(buttonId);
  if (!input || !target || !btn) return;
  if (!input.files || input.files.length === 0) {
    toast('请先选择图片');
    return;
  }

  const form = new FormData();
  Array.from(input.files).forEach(file => form.append('images', file));

  const originalText = btn.textContent;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>识图中…';

  try {
    const resp = await fetch('/api/vision/describe', { method: 'POST', body: form });
    const data = await resp.json();
    if (!resp.ok || data.error) {
      toast(data.error || '识图失败');
      return;
    }
    const combined = data.combined || '';
    if (!combined) {
      toast('未生成图片描述');
      return;
    }
    const current = target.value.trim();
    target.value = current ? `${current}\n\n${combined}` : combined;
    target.focus();
    toast('图片描述已生成');
  } catch (e) {
    toast('识图请求失败: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

document.getElementById('btn-describe-note-images').addEventListener('click', () => {
  describeSelectedImages('note-image-files', 'f-images', 'btn-describe-note-images');
});


// ═══════════════════════════════════════════════════════════
//  Profile
// ═══════════════════════════════════════════════════════════

async function loadProfile() {
  const resp = await fetch('/api/profile');
  const data = await resp.json();
  const el = document.getElementById('profile-display');
  if (data.content) {
    el.innerHTML = md2html(data.content);
  } else {
    el.innerHTML = '暂无画像，请先添加笔记后点击「重新生成」。';
  }
}

document.getElementById('btn-gen-profile').addEventListener('click', async () => {
  const btn = document.getElementById('btn-gen-profile');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>生成中…';

  const extra = document.getElementById('profile-extra-prompt').value.trim();

  try {
    const resp = await fetch('/api/profile/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ extra_prompt: extra }),
    });
    const data = await resp.json();
    if (data.error) { toast(data.error); return; }
    document.getElementById('profile-display').innerHTML = md2html(data.content);
    toast('画像已生成');
  } catch (e) {
    toast('请求失败: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '🔄 重新生成';
  }
});

document.getElementById('btn-edit-profile').addEventListener('click', async () => {
  const resp = await fetch('/api/profile');
  const data = await resp.json();
  document.getElementById('profile-textarea').value = data.content || '';
  document.getElementById('profile-display').style.display = 'none';
  document.getElementById('profile-editor').style.display = 'block';
});

document.getElementById('btn-cancel-profile').addEventListener('click', () => {
  document.getElementById('profile-editor').style.display = 'none';
  document.getElementById('profile-display').style.display = 'block';
});

document.getElementById('btn-save-profile').addEventListener('click', async () => {
  const content = document.getElementById('profile-textarea').value;
  await fetch('/api/profile', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ content }),
  });
  document.getElementById('profile-display').innerHTML = md2html(content);
  document.getElementById('profile-editor').style.display = 'none';
  document.getElementById('profile-display').style.display = 'block';
  toast('画像已保存');
});


// ═══════════════════════════════════════════════════════════
//  Suggestions
// ═══════════════════════════════════════════════════════════

document.getElementById('btn-gen-suggest').addEventListener('click', async () => {
  const btn = document.getElementById('btn-gen-suggest');
  const disp = document.getElementById('suggestions-display');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>生成中…';
  disp.innerHTML = '';

  const extra = document.getElementById('suggest-extra-prompt').value.trim();

  try {
    const resp = await fetch('/api/suggestions', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ extra_prompt: extra }),
    });
    const data = await resp.json();
    if (data.error) { toast(data.error); return; }
    disp.innerHTML = md2html(data.content);
  } catch (e) {
    toast('请求失败: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '✨ 生成选题建议';
  }
});


// ═══════════════════════════════════════════════════════════
//  Analytics
// ═══════════════════════════════════════════════════════════

let chartInstances = {};

function destroyCharts() {
  Object.values(chartInstances).forEach(c => c.destroy());
  chartInstances = {};
}

async function loadAnalytics() {
  const resp = await fetch('/api/analytics/stats');
  const stats = await resp.json();

  // Show persisted deep analysis (if any)
  const analysisDisplay = document.getElementById('deep-analysis-display');
  if (stats.analysis_md) {
    analysisDisplay.innerHTML = md2html(stats.analysis_md);
    analysisDisplay.style.display = 'block';
  } else {
    analysisDisplay.innerHTML = '';
    analysisDisplay.style.display = 'none';
  }

  if (!stats.total_notes) {
    document.getElementById('stats-overview').innerHTML =
      '<div class="card" style="text-align:center;color:var(--text-light)">暂无数据</div>';
    return;
  }

  // Stats cards
  document.getElementById('stats-overview').innerHTML = `
    <div class="stat-card"><div class="val">${stats.total_notes}</div><div class="lbl">笔记总数</div></div>
    <div class="stat-card"><div class="val">${fmt(stats.total_views)}</div><div class="lbl">总阅读</div></div>
    <div class="stat-card"><div class="val">${fmt(stats.total_likes)}</div><div class="lbl">总点赞</div></div>
    <div class="stat-card"><div class="val">${fmt(stats.total_saves)}</div><div class="lbl">总收藏</div></div>
    <div class="stat-card"><div class="val">${fmt(stats.total_comments)}</div><div class="lbl">总评论</div></div>
    <div class="stat-card"><div class="val">${stats.photo_count} / ${stats.video_count}</div><div class="lbl">图文 / 视频</div></div>
  `;

  destroyCharts();

  // Interactions chart
  const cd = stats.chart_data.slice().reverse();
  const ctx1 = document.getElementById('chart-interactions').getContext('2d');
  chartInstances.interactions = new Chart(ctx1, {
    type: 'bar',
    data: {
      labels: cd.map(d => d.title.length > 10 ? d.title.slice(0,10)+'…' : d.title),
      datasets: [
        { label: '点赞', data: cd.map(d => d.likes), backgroundColor: '#ff6b6b', borderRadius: 4 },
        { label: '收藏', data: cd.map(d => d.saves), backgroundColor: '#ffd93d', borderRadius: 4 },
        { label: '评论', data: cd.map(d => d.comments), backgroundColor: '#6bcb77', borderRadius: 4 },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'top' } },
      scales: { y: { beginAtZero: true } },
    },
  });

  // Content type comparison
  const ctx2 = document.getElementById('chart-type').getContext('2d');
  chartInstances.type = new Chart(ctx2, {
    type: 'bar',
    data: {
      labels: ['图文', '视频'],
      datasets: [{ label: '平均点赞', data: [stats.photo_avg_likes, stats.video_avg_likes], backgroundColor: ['#ff6b6b', '#ff8e8e'] }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  // Topic chart
  const topics = stats.topic_stats.slice(0, 10);
  const ctx3 = document.getElementById('chart-topics').getContext('2d');
  chartInstances.topics = new Chart(ctx3, {
    type: 'bar',
    data: {
      labels: topics.map(t => t.topic),
      datasets: [{ label: '发文数', data: topics.map(t => t.count), backgroundColor: topics.map((_,i) => `hsl(${i*36},70%,70%)`), borderRadius: 4 }],
    },
    options: {
      responsive: true,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } },
    },
  });
}

document.getElementById('btn-deep-analyze').addEventListener('click', async () => {
  const btn = document.getElementById('btn-deep-analyze');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>分析中…';

  const extra = document.getElementById('analyze-extra-prompt').value.trim();

  try {
    const resp = await fetch('/api/analytics/deep', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ extra_prompt: extra }),
    });
    const data = await resp.json();
    if (data.error) { toast(data.error); return; }
    const display = document.getElementById('deep-analysis-display');
    display.innerHTML = md2html(data.content);
    display.style.display = 'block';
    display.scrollIntoView({ behavior: 'smooth' });
    toast('分析已生成并保存');
  } catch (e) {
    toast('请求失败: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '🤖 LLM 深度分析';
  }
});

// Edit / Save deep analysis (like profile)
document.getElementById('btn-edit-analysis').addEventListener('click', async () => {
  const display = document.getElementById('deep-analysis-display');
  const rawText = display.innerText || '';
  document.getElementById('analysis-textarea').value =
    display.style.display === 'none' ? '' : rawText;
  display.style.display = 'none';
  document.getElementById('deep-analysis-editor').style.display = 'block';
});

document.getElementById('btn-cancel-analysis').addEventListener('click', () => {
  document.getElementById('deep-analysis-editor').style.display = 'none';
  document.getElementById('deep-analysis-display').style.display = 'block';
});

document.getElementById('btn-save-analysis').addEventListener('click', async () => {
  const content = document.getElementById('analysis-textarea').value;
  await fetch('/api/analytics/deep', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ content }),
  });
  const display = document.getElementById('deep-analysis-display');
  display.innerHTML = md2html(content);
  display.style.display = 'block';
  document.getElementById('deep-analysis-editor').style.display = 'none';
  toast('分析已保存');
});


// ═══════════════════════════════════════════════════════════
//  Content Creation
// ═══════════════════════════════════════════════════════════

document.getElementById('btn-gen-content').addEventListener('click', async () => {
  const description = document.getElementById('content-description').value.trim();
  if (!description) { toast('请描述你的照片/视频内容'); return; }

  const extra = document.getElementById('content-extra-prompt').value.trim();
  const btn = document.getElementById('btn-gen-content');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>生成中…';

  try {
    const resp = await fetch('/api/content/create', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ description, extra_prompt: extra }),
    });
    const data = await resp.json();
    if (data.error) { toast(data.error); return; }

    const stylePanel = document.getElementById('content-style-panel');
    const styleDisplay = document.getElementById('content-style-display');
    styleDisplay.innerHTML = md2html(data.style_advice);
    stylePanel.style.display = 'block';

    const bodyPanel = document.getElementById('content-body-panel');
    const bodyDisplay = document.getElementById('content-body-display');
    if (data.body_text) {
      bodyDisplay.innerHTML = md2html(data.body_text);
      bodyPanel.style.display = 'block';
      document.getElementById('btn-copy-body').style.display = 'inline-flex';
      bodyDisplay.dataset.raw = data.body_text;
    } else {
      bodyPanel.style.display = 'none';
      document.getElementById('btn-copy-body').style.display = 'none';
    }

    toast('内容已生成');
    document.getElementById('content-result').scrollIntoView({ behavior: 'smooth' });
    loadContentHistory(); // refresh history
  } catch (e) {
    toast('请求失败: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '✨ 生成内容';
  }
});

document.getElementById('btn-copy-body').addEventListener('click', () => {
  const bodyDisplay = document.getElementById('content-body-display');
  const raw = bodyDisplay.dataset.raw || bodyDisplay.innerText;
  navigator.clipboard.writeText(raw).then(() => toast('正文已复制到剪贴板 📋'));
});

document.getElementById('btn-describe-content-images').addEventListener('click', () => {
  describeSelectedImages('content-image-files', 'content-description', 'btn-describe-content-images');
});

// Content creation history
async function loadContentHistory() {
  const resp = await fetch('/api/content/history');
  const data = await resp.json();
  const list = document.getElementById('content-history-list');

  if (!data.items || !data.items.length) {
    list.innerHTML = '<div class="card" style="text-align:center;color:var(--text-light);padding:20px">暂无历史记录</div>';
    return;
  }

  list.innerHTML = data.items.map((item, idx) => `
    <div class="history-item">
      <div class="history-info" onclick="viewContentHistory(${idx})" style="cursor:pointer">
        <div class="history-desc">${esc(item.description)}</div>
        <div class="history-time">${item.timestamp}</div>
      </div>
      <button class="btn-ghost" style="font-size:12px;padding:4px 12px" onclick="deleteContentHistory(${idx})">🗑</button>
    </div>
  `).join('');
}

async function viewContentHistory(idx) {
  const resp = await fetch('/api/content/history');
  const data = await resp.json();
  const item = data.items[idx];
  if (!item) return;

  // Show in the result panels
  const stylePanel = document.getElementById('content-style-panel');
  document.getElementById('content-style-display').innerHTML = md2html(item.style_advice);
  stylePanel.style.display = 'block';

  const bodyPanel = document.getElementById('content-body-panel');
  const bodyDisplay = document.getElementById('content-body-display');
  if (item.body_text) {
    bodyDisplay.innerHTML = md2html(item.body_text);
    bodyDisplay.dataset.raw = item.body_text;
    bodyPanel.style.display = 'block';
    document.getElementById('btn-copy-body').style.display = 'inline-flex';
  }

  // Restore input
  document.getElementById('content-description').value = item.description;
  document.getElementById('content-result').scrollIntoView({ behavior: 'smooth' });
}

async function deleteContentHistory(idx) {
  if (!confirm('确定删除这条记录吗？')) return;
  await fetch(`/api/content/history/${idx}`, { method: 'DELETE' });
  loadContentHistory();
  toast('已删除');
}


// ═══════════════════════════════════════════════════════════
//  AI Chat (with persistence, AbortController, copy)
// ═══════════════════════════════════════════════════════════

let chatHistory = [];
let chatAbortController = null;

async function loadChatHistory() {
  try {
    const resp = await fetch('/api/chat/history');
    const data = await resp.json();
    chatHistory = data.messages || [];
    renderChatMessages();
  } catch (e) {
    // Silently fail — chat works without persistence
  }
}

async function saveChatHistory() {
  // Strip placeholder messages before saving
  const clean = chatHistory.filter(m => m.content !== '思考中…');
  try {
    await fetch('/api/chat/history', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ messages: clean }),
    });
  } catch (e) { /* ignore */ }
}

function renderChatMessages() {
  const container = document.getElementById('chat-messages');
  const defaultMsg = chatHistory.length === 0
    ? `<div class="chat-msg assistant">
         <div class="chat-bubble">你好！我是你的小红书运营 AI 顾问。我可以帮你解答内容创作、运营策略、数据分析等方面的问题。尽管问吧 📕</div>
       </div>`
    : '';
  container.innerHTML = defaultMsg + chatHistory.map(m => {
    const copyBtn = m.role === 'assistant' && m.content && m.content !== '思考中…'
      ? `<button class="btn-copy-msg" onclick="copyChatMsg(this)" title="复制">📋</button>`
      : '';
    return `
    <div class="chat-msg ${m.role}">
      <div class="chat-bubble">${md2html(m.content)}${copyBtn}</div>
    </div>`;
  }).join('');
  container.scrollTop = container.scrollHeight;
}

function copyChatMsg(btn) {
  const bubble = btn.closest('.chat-bubble');
  const clone = bubble.cloneNode(true);
  const cb = clone.querySelector('.btn-copy-msg');
  if (cb) cb.remove();
  const text = clone.innerText || clone.textContent || '';
  navigator.clipboard.writeText(text.trim()).then(() => toast('已复制 📋'));
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  chatHistory.push({ role: 'user', content: text });
  renderChatMessages();
  await saveChatHistory();

  const sendBtn = document.getElementById('btn-send-chat');
  const cancelBtn = document.getElementById('btn-cancel-chat');
  sendBtn.style.display = 'none';
  cancelBtn.style.display = 'inline-flex';

  const thinkingIdx = chatHistory.length;
  chatHistory.push({ role: 'assistant', content: '思考中…' });
  renderChatMessages();

  chatAbortController = new AbortController();

  try {
    const cleanMessages = chatHistory
      .filter(m => m.content !== '思考中…')
      .slice(-20);

    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ messages: cleanMessages }),
      signal: chatAbortController.signal,
    });
    const data = await resp.json();
    if (data.error) {
      chatHistory[thinkingIdx] = { role: 'assistant', content: `❌ ${data.error}` };
    } else {
      chatHistory[thinkingIdx] = { role: 'assistant', content: data.reply };
    }
  } catch (e) {
    if (e.name === 'AbortError') {
      chatHistory.pop(); // remove thinking + cancelled
      toast('已取消');
    } else {
      chatHistory[thinkingIdx] = { role: 'assistant', content: `❌ 请求失败: ${e.message}` };
    }
  } finally {
    chatAbortController = null;
    await saveChatHistory();
    renderChatMessages();
    sendBtn.style.display = 'inline-flex';
    cancelBtn.style.display = 'none';
    input.focus();
  }
}

function cancelChat() {
  if (chatAbortController) {
    chatAbortController.abort();
    chatAbortController = null;
  }
}

document.getElementById('btn-send-chat').addEventListener('click', sendChat);
document.getElementById('btn-cancel-chat').addEventListener('click', cancelChat);

document.getElementById('btn-clear-chat').addEventListener('click', async () => {
  if (chatHistory.length > 0 && !confirm('确定清空所有对话记录吗？')) return;
  chatHistory = [];
  try { await fetch('/api/chat/history', { method: 'DELETE' }); } catch(e) {}
  renderChatMessages();
  toast('对话已清空');
});


// ═══════════════════════════════════════════════════════════
//  Settings
// ═══════════════════════════════════════════════════════════

async function loadSettings() {
  const resp = await fetch('/api/settings');
  const data = await resp.json();
  document.getElementById('s-apikey').value = data.deepseek_api_key || '';
  document.getElementById('s-baseurl').value = data.deepseek_base_url || 'https://api.deepseek.com/v1';
  document.getElementById('s-model').value = data.deepseek_model || 'deepseek-chat';
  document.getElementById('s-temperature').value = data.deepseek_temperature || '0.7';
  document.getElementById('s-max-tokens').value = data.deepseek_max_tokens || '4096';
  document.getElementById('s-vision-apikey').value = data.vision_api_key || '';
  document.getElementById('s-vision-baseurl').value = data.vision_base_url || '';
  document.getElementById('s-vision-model').value = data.vision_model || 'gemma-4';
  document.getElementById('s-vision-temperature').value = data.vision_temperature || '0.2';
  document.getElementById('s-vision-max-tokens').value = data.vision_max_tokens || '2048';
  document.getElementById('s-vision-prompt').value = data.vision_prompt || '';
  document.getElementById('s-bio').value = data.blogger_bio || '';
}

document.getElementById('btn-save-settings').addEventListener('click', async () => {
  const payload = {
    deepseek_api_key: document.getElementById('s-apikey').value.trim(),
    deepseek_base_url: document.getElementById('s-baseurl').value.trim(),
    deepseek_model: document.getElementById('s-model').value.trim(),
    deepseek_temperature: document.getElementById('s-temperature').value.trim(),
    deepseek_max_tokens: document.getElementById('s-max-tokens').value.trim(),
    vision_api_key: document.getElementById('s-vision-apikey').value.trim(),
    vision_base_url: document.getElementById('s-vision-baseurl').value.trim(),
    vision_model: document.getElementById('s-vision-model').value.trim(),
    vision_temperature: document.getElementById('s-vision-temperature').value.trim(),
    vision_max_tokens: document.getElementById('s-vision-max-tokens').value.trim(),
    vision_prompt: document.getElementById('s-vision-prompt').value.trim(),
    blogger_bio: document.getElementById('s-bio').value.trim(),
  };
  await fetch('/api/settings', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  toast('设置已保存');
});

// Clear per-module data
document.querySelectorAll('.btn-clear').forEach(btn => {
  btn.addEventListener('click', async () => {
    const module = btn.dataset.module;
    const labels = {
      profile: '博主画像', analysis: '数据分析',
      content_history: '内容创作历史', all: '以上全部数据'
    };
    const label = labels[module] || module;
    if (!confirm(`确定清除「${label}」吗？此操作不可撤销。`)) return;

    const resp = await fetch('/api/settings/clear', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ module }),
    });
    const data = await resp.json();
    if (data.ok) {
      toast(`「${label}」已清除`);
      if (module === 'profile' || module === 'all') loadProfile();
      if (module === 'analysis' || module === 'all') loadAnalytics();
      if (module === 'content_history' || module === 'all') loadContentHistory();
    } else {
      toast(data.error || '清除失败');
    }
  });
});


// ═══════════════════════════════════════════════════════════
//  Account Management
// ═══════════════════════════════════════════════════════════

async function loadAccounts() {
  const resp = await fetch('/api/accounts');
  const data = await resp.json();
  const select = document.getElementById('account-select');
  select.innerHTML = data.accounts.map(a =>
    `<option value="${a.id}" ${a.id === data.current_id ? 'selected' : ''}>${esc(a.name)}</option>`
  ).join('');
  // Also update account list in settings
  renderAccountList(data);
}

function renderAccountList(data) {
  const list = document.getElementById('account-list');
  if (!list) return;
  list.innerHTML = data.accounts.map(a => `
    <div class="account-item ${a.id === data.current_id ? 'current' : ''}">
      <span class="account-name">${esc(a.name)}</span>
      <span class="account-time">${a.created_at}</span>
      <div class="account-actions">
        ${a.id !== data.current_id ? `<button onclick="switchAccount('${a.id}')" class="btn-ghost" style="font-size:11px;padding:3px 10px">切换</button>` : '<span class="current-badge">当前</span>'}
        ${a.id !== data.current_id ? `<button onclick="deleteAccount('${a.id}','${esc(a.name)}')" class="btn-ghost" style="font-size:11px;padding:3px 10px;color:#e03131">删除</button>` : ''}
      </div>
    </div>
  `).join('');
}

async function switchAccount(accountId) {
  const resp = await fetch('/api/accounts/switch', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ account_id: accountId }),
  });
  const data = await resp.json();
  if (data.ok) {
    toast('已切换账号');
    loadAccounts();
    loadNotes();
    loadChatHistory();
    // Reload current tab data
    const activeTab = document.querySelector('.tab.active');
    if (activeTab) {
      const tab = activeTab.dataset.tab;
      if (tab === 'analytics') loadAnalytics();
      if (tab === 'profile') loadProfile();
      if (tab === 'create') loadContentHistory();
      if (tab === 'settings') loadSettings();
    }
  } else {
    toast(data.error || '切换失败');
  }
}

document.getElementById('btn-add-account').addEventListener('click', async () => {
  const input = document.getElementById('new-account-name');
  const name = input.value.trim();
  if (!name) { toast('请输入账号名称'); return; }
  const resp = await fetch('/api/accounts', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ name }),
  });
  const data = await resp.json();
  if (data.error) { toast(data.error); return; }
  input.value = '';
  toast('账号已添加');
  loadAccounts();
});

async function deleteAccount(accountId, name) {
  if (!confirm(`确定删除账号「${name}」吗？\n该账号的所有数据将被永久删除，不可恢复。`)) return;

  const resp = await fetch(`/api/accounts/${accountId}`, { method: 'DELETE' });
  const data = await resp.json();
  if (data.error) { toast(data.error); return; }
  toast('账号已删除');
  loadAccounts();
  loadNotes();
  // Reload current tab
  const activeTab = document.querySelector('.tab.active');
  if (activeTab) {
    const tab = activeTab.dataset.tab;
    if (tab === 'analytics') loadAnalytics();
    if (tab === 'profile') loadProfile();
    if (tab === 'create') loadContentHistory();
    if (tab === 'settings') loadSettings();
  }
}


// ═══════════════════════════════════════════════════════════
//  Init
// ═══════════════════════════════════════════════════════════

loadAccounts();
loadNotes();
loadChatHistory();
