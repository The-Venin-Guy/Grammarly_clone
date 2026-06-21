const editor = document.getElementById('editor');
const wordCountEl = document.getElementById('word-count');
const charCountEl = document.getElementById('char-count');
const analyzeBtn = document.getElementById('analyze-btn');
const resetBtn = document.getElementById('reset-btn');
const cardsEl = document.getElementById('cards');
const readabilityEl = document.getElementById('readability-value');
const formalityEl = document.getElementById('formality-value');
const sentenceStatsEl = document.getElementById('sentence-stats');
const formalityToggle = document.getElementById('formality-toggle');
const highlightLayer = document.getElementById('highlight-layer');

let lastAnalysisData = null;
const spellErrors = new Map();
let lastCompletedSentences = [];
let debounceTimer = null;
let staleTimer = null;

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function matchCase(original, suggestion) {
  if (original[0] && original[0] === original[0].toUpperCase() && original[0] !== original[0].toLowerCase()) {
    return suggestion.charAt(0).toUpperCase() + suggestion.slice(1);
  }
  return suggestion;
}

function updateLiveStats() {
  const text = editor.value;
  const charCount = text.length;
  const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
  wordCountEl.textContent = `${wordCount} word${wordCount === 1 ? '' : 's'}`;
  charCountEl.textContent = `${charCount} character${charCount === 1 ? '' : 's'}`;
}

editor.addEventListener('input', updateLiveStats);
updateLiveStats();

async function checkWord(word) {
  const cleaned = word.replace(/[^a-zA-Z']/g, '');
  if (!cleaned) return;

  const response = await fetch('/spellcheck', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ word: cleaned })
  });
  if (!response.ok) return;

  const result = await response.json();
  if (!result.is_correct) {
    spellErrors.set(cleaned.toLowerCase(), result.suggestion);
  } else {
    spellErrors.delete(cleaned.toLowerCase());
  }
  renderHighlights();
}

function renderHighlights() {
  const text = editor.value;
  const tokens = text.split(/(\s+)/);

  const html = tokens.map(token => {
    const cleaned = token.replace(/[^a-zA-Z']/g, '').toLowerCase();
    if (cleaned && spellErrors.has(cleaned)) {
      return `<span class="misspelled" data-word="${escapeHtml(cleaned)}">${escapeHtml(token)}</span>`;
    }
    return escapeHtml(token);
  }).join('');

  highlightLayer.innerHTML = html;
}

editor.addEventListener('keyup', (e) => {
  if (e.key === ' ') {
    const cursorPos = editor.selectionStart;
    const textBeforeCursor = editor.value.slice(0, cursorPos);
    const words = textBeforeCursor.trim().split(/\s+/);
    const lastWord = words[words.length - 1];
    if (lastWord) checkWord(lastWord);
  }
});

editor.addEventListener('input', renderHighlights);
editor.addEventListener('scroll', () => {
  highlightLayer.scrollTop = editor.scrollTop;
});

editor.addEventListener('click', () => {
  const cursorPos = editor.selectionStart;
  const text = editor.value;

  let start = cursorPos;
  let end = cursorPos;
  while (start > 0 && /\S/.test(text[start - 1])) start--;
  while (end < text.length && /\S/.test(text[end])) end++;

  const word = text.slice(start, end);
  const cleaned = word.replace(/[^a-zA-Z']/g, '').toLowerCase();

  if (!cleaned || !spellErrors.has(cleaned)) return;

  const rawSuggestion = spellErrors.get(cleaned);
  if (!rawSuggestion) return;
  const suggestion = matchCase(word, rawSuggestion);

  editor.setSelectionRange(start, end);
  document.execCommand('insertText', false, suggestion);

  spellErrors.delete(cleaned);
});

async function analyzeText() {
  const text = editor.value.trim();
  if (!text) return;

  const response = await fetch('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });

  if (!response.ok) {
    console.error('Analyze failed:', response.status);
    return;
  }

  const data = await response.json();
  lastAnalysisData = data;
  renderResults(data);
}

function renderResults(data) {
  readabilityEl.textContent = `${data.readability.readability_label} (Grade ${data.readability.grade_level.toFixed(1)})`;

  const scores = data.sentences.map(s => s.formality_score);
  const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0.5;
  let label = 'Neutral';
  if (avg >= 0.7) label = 'Formal';
  else if (avg <= 0.35) label = 'Informal';
  formalityEl.textContent = `${label} (${avg.toFixed(2)})`;

  const ds = data.document_stats;
  sentenceStatsEl.textContent = `${ds.total_sentences} total, ${ds.passive_voice_count} passive`;

  cardsEl.innerHTML = '';
  data.sentences.forEach(sentence => cardsEl.appendChild(buildCard(sentence)));
}

function buildCard(sentence) {
  const card = document.createElement('div');
  card.className = 'card';

  if (sentence.has_error) card.classList.add('has-grammar');
  if (formalityToggle.checked && sentence.tone_rewrite) card.classList.add('has-formality');
  if (sentence.passive_voice) card.classList.add('has-passive');

  let html = `<div class="original">${escapeHtml(sentence.original_text)}</div>`;

  if (sentence.has_error && sentence.corrected_text) {
    html += `<span class="tag grammar">Grammar</span>
              <div class="rewrite acceptable" data-sentence-id="${sentence.id}" data-type="corrected_text">${escapeHtml(sentence.corrected_text)}</div>`;
  }

  if (formalityToggle.checked && sentence.tone_rewrite) {
    html += `<span class="tag formality">Formality</span>
              <div class="rewrite acceptable" data-sentence-id="${sentence.id}" data-type="tone_rewrite">${escapeHtml(sentence.tone_rewrite)}</div>`;
  }

  if (sentence.passive_voice && sentence.passive_rewrite) {
    html += `<span class="tag passive">Passive</span>
              <div class="rewrite acceptable" data-sentence-id="${sentence.id}" data-type="passive_rewrite">${escapeHtml(sentence.passive_rewrite)}</div>`;
  }

  if (sentence.clarity_rewrite) {
    html += `<span class="tag clarity">Clarity</span>
              <div class="rewrite acceptable" data-sentence-id="${sentence.id}" data-type="clarity_rewrite">${escapeHtml(sentence.clarity_rewrite)}</div>`;
  }

  card.innerHTML = html;
  return card;
}

// ---------- Sidebar rewrite: click-to-accept (undo-safe via execCommand) ----------
cardsEl.addEventListener('click', (e) => {
  const target = e.target.closest('.rewrite.acceptable');
  if (!target) return;

  const sentenceId = parseInt(target.dataset.sentenceId, 10);
  const type = target.dataset.type;
  const sentenceData = lastAnalysisData.sentences.find(s => s.id === sentenceId);
  if (!sentenceData) return;

  const replacementText = sentenceData[type];
  if (!replacementText) return;

  const text = editor.value;
  const index = text.indexOf(sentenceData.original_text);
  if (index === -1) return; // original sentence already replaced/edited away

  editor.focus();
  editor.setSelectionRange(index, index + sentenceData.original_text.length);
  document.execCommand('insertText', false, replacementText);

  const card = target.closest('.card');
  card.querySelectorAll('.rewrite.acceptable').forEach(el => {
    el.classList.remove('acceptable');
    el.classList.add('stale');
  });
  target.classList.remove('stale');
  target.classList.add('applied');
});

analyzeBtn.addEventListener('click', analyzeText);

resetBtn.addEventListener('click', async () => {
  await fetch('/reset', { method: 'POST' });
  cardsEl.innerHTML = '';
  readabilityEl.textContent = '—';
  formalityEl.textContent = '—';
  sentenceStatsEl.textContent = '—';
});

formalityToggle.addEventListener('change', () => {
  if (lastAnalysisData) renderResults(lastAnalysisData);
});

function getCompletedSentences(text) {
  const matches = text.match(/[^.!?]+[.!?]+/g);
  return matches ? matches.map(s => s.trim()) : [];
}

function sentencesChanged(a, b) {
  if (a.length !== b.length) return true;
  return a.some((s, i) => s !== b[i]);
}

async function runAutoAnalysis(textOverride) {
  const text = textOverride !== undefined ? textOverride : editor.value.trim();
  if (!text) return;

  const response = await fetch('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });

  if (!response.ok) return;

  const data = await response.json();
  lastAnalysisData = data;
  renderResults(data);
}

editor.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  clearTimeout(staleTimer);

  const completed = getCompletedSentences(editor.value);

  if (sentencesChanged(completed, lastCompletedSentences)) {
    debounceTimer = setTimeout(() => {
      lastCompletedSentences = completed;
      const textToSend = completed.join(' ');
      if (textToSend) runAutoAnalysis(textToSend);
    }, 1800);
  }

  staleTimer = setTimeout(() => {
    const fullText = editor.value.trim();
    if (fullText) runAutoAnalysis(fullText);
  }, 5000);
});