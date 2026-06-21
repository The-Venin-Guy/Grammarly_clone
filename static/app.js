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

  const suggestion = spellErrors.get(cleaned);
  if (!suggestion) return;

  editor.value = text.slice(0, start) + suggestion + text.slice(end);
  spellErrors.delete(cleaned);
  renderHighlights();
  updateLiveStats();

  const newPos = start + suggestion.length;
  editor.setSelectionRange(newPos, newPos);
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
              <div class="rewrite">${escapeHtml(sentence.corrected_text)}</div>`;
  }

  if (formalityToggle.checked && sentence.tone_rewrite) {
    html += `<span class="tag formality">Formality</span>
              <div class="rewrite">${escapeHtml(sentence.tone_rewrite)}</div>`;
  }

  if (sentence.passive_voice && sentence.passive_rewrite) {
    html += `<span class="tag passive">Passive</span>
              <div class="rewrite">${escapeHtml(sentence.passive_rewrite)}</div>`;
  }

  card.innerHTML = html;
  return card;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

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

let lastCompletedSentences = [];
let debounceTimer = null;
let staleTimer = null;

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