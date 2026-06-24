// ---------- DOM references ----------
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

// State 
let lastAnalysisData = null;
const spellErrors = new Map();
const grammarErrorsBySentence = new Map(); // sentenceText -> errors array
const dismissedSuggestions = new Set();    // entries like "hash:type"
let lastCompletedSentences = [];
let debounceTimer = null;
let staleTimer = null;
let grammarCheckTimer = null;

//Helpers 
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

function setsEqual(a, b) {
  if (a.size !== b.size) return false;
  for (const v of a) if (!b.has(v)) return false;
  return true;
}

// Live word/character count
function updateLiveStats() {
  const text = editor.value;
  const charCount = text.length;
  const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
  wordCountEl.textContent = `${wordCount} word${wordCount === 1 ? '' : 's'}`;
  charCountEl.textContent = `${charCount} character${charCount === 1 ? '' : 's'}`;
}

editor.addEventListener('input', updateLiveStats);
updateLiveStats();

//  Spellcheck: detection 
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

editor.addEventListener('keyup', (e) => {
  if (e.key === ' ') {
    const cursorPos = editor.selectionStart;
    const textBeforeCursor = editor.value.slice(0, cursorPos);
    const words = textBeforeCursor.trim().split(/\s+/);
    const lastWord = words[words.length - 1];
    if (lastWord) checkWord(lastWord);
  }
});

// ---------- Grammar-only fast check (LanguageTool, no Ollama) ----------
async function checkGrammarForSentence(sentence) {
  const response = await fetch('/grammar-check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: sentence })
  });
  if (!response.ok) return;

  const data = await response.json();
  if (data.errors && data.errors.length > 0) {
    grammarErrorsBySentence.set(sentence, data.errors);
  } else {
    grammarErrorsBySentence.delete(sentence);
  }
  renderHighlights();
}

// ---------- Combined highlight rendering (spelling + grammar) ----------
function buildMarks(text) {
  const marks = [];

  // Spelling marks
  let pos = 0;
  text.split(/(\s+)/).forEach(token => {
    const cleaned = token.replace(/[^a-zA-Z']/g, '').toLowerCase();
    if (cleaned && spellErrors.has(cleaned)) {
      marks.push({ start: pos, end: pos + token.length, type: 'spelling' });
    }
    pos += token.length;
  });

  // Grammar marks, mapped from sentence-relative offsets to full-text offsets
  let searchFrom = 0;
  for (const [sentence, errors] of grammarErrorsBySentence.entries()) {
    const sentencePos = text.indexOf(sentence, searchFrom);
    if (sentencePos === -1) continue;
    errors.forEach(err => {
      marks.push({
        start: sentencePos + err.offset,
        end: sentencePos + err.offset + err.length,
        type: 'grammar'
      });
    });
    searchFrom = sentencePos + sentence.length;
  }

  return marks;
}

function renderHighlights() {
  const text = editor.value;
  const marks = buildMarks(text);

  const charTypes = Array.from({ length: text.length }, () => new Set());
  marks.forEach(m => {
    for (let i = m.start; i < m.end && i < text.length; i++) {
      charTypes[i].add(m.type);
    }
  });

  let html = '';
  let i = 0;
  while (i < text.length) {
    const types = charTypes[i];
    let j = i;
    while (j < text.length && setsEqual(charTypes[j], types)) j++;
    const chunk = text.slice(i, j);
    if (types.size === 0) {
      html += escapeHtml(chunk);
    } else {
      const classes = Array.from(types).map(t => `mark-${t}`).join(' ');
      html += `<span class="${classes}">${escapeHtml(chunk)}</span>`;
    }
    i = j;
  }

  highlightLayer.innerHTML = html;
}

editor.addEventListener('input', renderHighlights);
editor.addEventListener('scroll', () => {
  highlightLayer.scrollTop = editor.scrollTop;
});

// ---------- Spellcheck: click-to-accept (undo-safe via execCommand) ----------
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

// ---------- Analyze + render sidebar ----------
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
  if (data.document_tone && data.document_tone.length) {
    sentencesStatsE1.textContent += ' . Tone: ' + data.document_tone.join(', ');
  }

  const ds = data.document_stats;
  sentenceStatsEl.textContent = `${ds.total_sentences} total, ${ds.passive_voice_count} passive`;

  cardsEl.innerHTML = '';
  data.sentences.forEach(sentence => cardsEl.appendChild(buildCard(sentence)));
}

function buildCard(sentence) {
  const card = document.createElement('div');
  card.className = 'card';

  const isDismissed = (type) => dismissedSuggestions.has(`${sentence.hash}:${type}`);

  if (sentence.has_error && !isDismissed('corrected_text')) card.classList.add('has-grammar');
  if (formalityToggle.checked && sentence.tone_rewrite && !isDismissed('tone_rewrite')) card.classList.add('has-formality');
  if (sentence.passive_voice && !isDismissed('passive_rewrite')) card.classList.add('has-passive');
  if (sentence.tone_shift && !isDismissed('tone_shift')) card.classList.add('has-tone-shift');

  let html = `<div class="original">${escapeHtml(sentence.original_text)}</div>`;

  if (sentence.top_tones && sentence.top_tones.length) {
    html += `<div class="rewrite" style="font-style:normal;">Tones: ${sentence.top_tones.map(escapeHtml).join(', ')}</div>`;
  }

  function suggestionRow(tag, type, text) {
    if (isDismissed(type)) return '';
    return `<div class="suggestion-row">
              <span class="tag ${tag}">${tag.charAt(0).toUpperCase() + tag.slice(1)}</span>
              <button class="dismiss-btn" data-hash="${sentence.hash}" data-type="${type}" title="Ignore this suggestion">×</button>
            </div>
            <div class="rewrite acceptable" data-sentence-id="${sentence.id}" data-type="${type}">${escapeHtml(text)}</div>`;
  }

  if (sentence.has_error && sentence.corrected_text) {
    html += suggestionRow('grammar', 'corrected_text', sentence.corrected_text);
  }
  if (formalityToggle.checked && sentence.tone_rewrite) {
    html += suggestionRow('formality', 'tone_rewrite', sentence.tone_rewrite);
  }
  if (sentence.passive_voice && sentence.passive_rewrite) {
    html += suggestionRow('passive', 'passive_rewrite', sentence.passive_rewrite);
  }
  if (sentence.clarity_rewrite) {
    html += suggestionRow('clarity', 'clarity_rewrite', sentence.clarity_rewrite);
  }

  if (sentence.tone_shift && !isDismissed('tone_shift')) {
    html += `<div class="suggestion-row">
               <span class="tag tone-shift">Tone Shift</span>
               <button class="dismiss-btn" data-hash="${sentence.hash}" data-type="tone_shift" title="Ignore this note">×</button>
             </div>
             <div class="rewrite">This sentence's tone differs notably from the document's overall tone.</div>`;
  }

  card.innerHTML = html;
  return card;
}

// ---------- Sidebar: dismiss + click-to-accept (undo-safe via execCommand) ----------
cardsEl.addEventListener('click', (e) => {
  const dismissBtn = e.target.closest('.dismiss-btn');
  if (dismissBtn) {
    const key = `${dismissBtn.dataset.hash}:${dismissBtn.dataset.type}`;
    dismissedSuggestions.add(key);
    renderResults(lastAnalysisData);
    return;
  }

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

// ---------- Buttons ----------
analyzeBtn.addEventListener('click', analyzeText);

resetBtn.addEventListener('click', async () => {
  await fetch('/reset', { method: 'POST' });
  cardsEl.innerHTML = '';
  readabilityEl.textContent = '—';
  formalityEl.textContent = '—';
  sentenceStatsEl.textContent = '—';
  dismissedSuggestions.clear();
  grammarErrorsBySentence.clear();
  renderHighlights();
});

formalityToggle.addEventListener('change', () => {
  if (lastAnalysisData) renderResults(lastAnalysisData);
});

// ---------- Sentence-boundary debounce + stale-fallback auto-analysis ----------
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
  clearTimeout(grammarCheckTimer);

  const completed = getCompletedSentences(editor.value);

  // Fast inline grammar highlighting (LanguageTool only, no Ollama)
  grammarCheckTimer = setTimeout(() => {
    completed.forEach(sentence => {
      if (!grammarErrorsBySentence.has(sentence)) checkGrammarForSentence(sentence);
    });
    for (const key of grammarErrorsBySentence.keys()) {
      if (!completed.includes(key)) grammarErrorsBySentence.delete(key);
    }
  }, 400);

  // Full LLM-based analysis, only on newly-completed sentences
  if (sentencesChanged(completed, lastCompletedSentences)) {
    debounceTimer = setTimeout(() => {
      lastCompletedSentences = completed;
      const textToSend = completed.join(' ');
      if (textToSend) runAutoAnalysis(textToSend);
    }, 1800);
  }

  // Safety net for unfinished/unpunctuated text
  staleTimer = setTimeout(() => {
    const fullText = editor.value.trim();
    if (fullText) runAutoAnalysis(fullText);
  }, 5000);
});