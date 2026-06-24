# Writing Assistant — Grammar Checker (Ollama Variant)

A locally-run, GPU-accelerated writing assistant that analyzes text for grammar, tone, readability, and spelling — entirely on-device, with no external API calls. Built as a deep learning course internship project, demonstrating practical integration of transformer models, classical NLP, and backend architecture.

---

## 1. Project Context

This project demonstrates:
- Practical application of transformer models for both classification and generation
- NLP preprocessing (sentence segmentation, dependency parsing)
- A gated architecture that mixes cheap classical checks with expensive LLM calls, invoked only when necessary
- Sentence-level caching and change-tracking
- A full FastAPI backend with an interactive, debounced frontend

**Core design philosophy:** *Classify cheaply, generate expensively only when needed.* A lightweight classifier or rule-based checker decides whether a sentence needs LLM intervention; the LLM (Ollama, running locally) is only invoked when a gate actually triggers. This avoids running a 3.8B-parameter model on every sentence regardless of need.

---

## 2. Hardware & Environment

- **GPU:** NVIDIA GeForce GTX 1660 Ti, 6GB VRAM, CUDA-enabled
- **OS:** Windows
- **Python:** 3.14.3
- **Java:** 26 (required by LanguageTool)
- **LLM runtime:** Ollama (local server, port 11434)

---

## 3. Architecture Overview

```
Frontend (HTML/CSS/Vanilla JS)
         |
         V
   FastAPI Server (port 8000)
         |
         V
  Request Validation (Pydantic)
         |
         V
   spaCy Sentence Splitting
   (single source of truth for sentence boundaries)
         |
         V
   Sentence Hashing (hashlib) + Cache Check
         |
         V
   Unchanged sentences → return cached result
   Changed sentences → run full pipeline, concurrently per sentence:
         |
    _____|_____________________________
    |                                  |
    V                                  V
LanguageTool                    ToneRouter (3 parallel gates,
Error Detection                  run on ORIGINAL sentence text)
    |                                  |
    V                          ____________________
GrammarRouter                  |         |          |
(if errors found)           Gate 1    Gate 2     Gate 3
    |                      Formality  Passive   Clarity
    V                       (ranker)  (spaCy)   (Flesch<50)
Ollama phi3.5                   |         |          |
Grammar Correction          Ollama if   Ollama if  Ollama if
                             informal   passive    doc Flesch<50
    |____________________________|_________|__________|
                         |
                         V
                TextStat Readability
                (document level only)
                         |
                         V
                  Response Formatter
                         |
                         V
                      Frontend
                         ^
                         |
               Ollama Server (port 11434)
               [separate process, managed by start.bat]
```

**Why classifiers + LLM, not LLM alone:** A classifier runs in milliseconds and is highly accurate for narrow binary/scalar tasks (formal/informal, passive/active). An LLM call takes 1–10+ seconds. Running the LLM to *check* every sentence before deciding whether to *rewrite* it would be wasteful. The gates classify cheaply; Ollama is only invoked when a gate actually fires.

---

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI + Uvicorn |
| Request/response validation | Pydantic |
| Async HTTP (Ollama calls) | httpx (`AsyncClient`) |
| LLM runtime | Ollama, model: `phi3.5:latest` |
| Formality scoring | `s-nlp/roberta-base-formality-ranker` (HuggingFace Transformers, GPU) |
| Passive voice detection | spaCy `en_core_web_sm` (`nsubjpass` dependency label) |
| Sentence segmentation | spaCy (single source of truth — no other splitter used anywhere) |
| Grammar error detection | LanguageTool (`language-tool-python`) |
| Readability metrics | `textstat` (Flesch Reading Ease, Flesch-Kincaid Grade) |
| Word-level spellcheck | `pyspellchecker` |
| Sentence hashing/caching | `hashlib` (SHA-256), in-memory dict cache |
| Concurrency | `asyncio.gather` — both across sentences and across gates within a sentence |
| Frontend | Vanilla HTML/CSS/JS — no framework |

---

## 5. File Structure

```
Grammar_Checker/
│
├── grammar_model.py        # ollama_generate() helper + correct()
├── grammar_service.py      # LanguageTool + GrammarRouter logic
├── tone_model.py           # formality ranker + 3 Ollama rewrite functions
├── tone_service.py         # ToneRouter (all 3 gates, run concurrently)
├── readability_service.py  # textstat wrapper + get_flesch()
├── spellcheck_service.py   # pyspellchecker wrapper
├── hashing.py               # SHA-256 sentence hashing
├── sentence_tracker.py     # in-memory cache: hash → analysis result
├── schemas/
│   ├── request.py          # AnalyzeRequest, SpellCheckRequest
│   └── response.py         # AnalyzeResponse, SentenceResult, etc.
├── routes/
│   ├── analyze.py          # POST /analyze
│   ├── reset.py            # POST /reset
│   ├── spellcheck.py       # POST /spellcheck
│   └── grammar_check.py    # POST /grammar-check (fast, LanguageTool-only)
├── main.py                 # FastAPI app, lifespan health check, static file mount
├── start.bat                # single-command startup script
└── static/
    ├── index.html
    ├── style.css
    └── app.js
```

---

## 6. Setup

```bash
pip install fastapi uvicorn pydantic transformers torch torchvision torchaudio spacy language-tool-python textstat httpx sentencepiece pyspellchecker --break-system-packages
python -m spacy download en_core_web_sm
```

Install Ollama from [ollama.com/download](https://ollama.com/download), then pull the model:

```bash
ollama pull phi3.5
```

Confirm Java is installed (required by LanguageTool):

```bash
java -version
```

---

## 7. Running the App

```bash
start.bat
```

This single script:
1. Checks if port 11434 is already in use; starts Ollama if not
2. Sets `OLLAMA_NUM_PARALLEL=4` and `OLLAMA_KEEP_ALIVE=30m` for the session
3. Sends a throwaway warmup prompt to phi3.5, forcing it into VRAM before any real request arrives (avoids the user-facing ~30s cold-start cost)
4. Starts FastAPI/Uvicorn, which runs a startup health check confirming Ollama is reachable before accepting requests

Visit `http://localhost:8000/` for the app, or `http://localhost:8000/docs` for the interactive API explorer.

**Note:** `start.bat` currently runs Uvicorn with `--reload`, intended for active development. This causes models to load twice (once for the file-watcher process, once for the actual app process), roughly doubling startup VRAM/RAM use temporarily. Drop `--reload` for a final, single-load run before a live demo.

---

## 8. API Endpoints

### `POST /analyze`
**Input:**
```json
{ "text": "Your text here." }
```

**Output:**
```json
{
  "sentences": [
    {
      "id": 1,
      "original_text": "...",
      "corrected_text": "...",
      "formality_score": 0.89,
      "tone_rewrite": "...",
      "passive_rewrite": "...",
      "clarity_rewrite": "...",
      "has_error": true,
      "errors": [
        { "message": "...", "offset": 4, "length": 5, "replacements": ["does", "did"], "rule_id": "HE_VERB_AGR" }
      ],
      "passive_voice": false,
      "hash": "...",
      "analyzed": true,
      "modified": true
    }
  ],
  "readability": {
    "flesch_reading_ease": 72.4,
    "grade_level": 8.1,
    "readability_label": "Fairly Easy"
  },
  "document_stats": {
    "total_sentences": 5,
    "sentences_reanalyzed": 2,
    "sentences_cached": 3,
    "passive_voice_count": 1
  }
}
```

### `POST /reset`
Clears the in-memory sentence cache. Input: none. Output:
```json
{ "status": "cleared" }
```

### `POST /spellcheck`
**Input:**
```json
{ "word": "teh" }
```
**Output:**
```json
{ "is_correct": false, "suggestion": "the" }
```

### `POST /grammar-check`
Fast, LanguageTool-only check with no Ollama call — used for inline highlighting before the full analysis pipeline runs.

**Input:**
```json
{ "text": "She dont know." }
```
**Output:**
```json
{
  "errors": [
    { "message": "...", "offset": 4, "length": 4, "replacements": ["doesn't", "don't"], "rule_id": "..." }
  ]
}
```

---

## 9. Gated Router Logic

### GrammarRouter
LanguageTool runs on every sentence (fast, deterministic, no GPU). If one or more errors are found, Ollama is called to correct it.

**Extended trigger (heuristic fallback):** LanguageTool has real recall gaps — it misses missing-article errors and short-token typos that happen to form a different valid word (e.g. "o" instead of "of"). To catch some of these without adding a new model, two cheap heuristics run on the existing spaCy parse (already computed for passive-voice detection) whenever LanguageTool finds nothing:
- **Suspicious short token:** any 1–2 letter alphabetic token not in a small whitelist of legitimate short words (a, I, an, to, of, ...).
- **Missing determiner:** a singular common noun (`NN`) with no `det` child in the dependency tree.

If either heuristic fires, Ollama is still called — but the result is only treated as a real correction if Ollama's output actually differs from the input. This guards against heuristic false positives (e.g. "Honesty matters." has no determiner but is correct English; if Ollama returns it unchanged, no error is flagged).

**Current prompt** (tuned after observing over-rewriting):
> "Fix only the spelling and grammatical errors in this sentence. Make the smallest possible change... Do not rephrase, restructure, or change the meaning of any part of the sentence." + one-shot example + the sentence.

**Defensive output cleanup (`clean_llm_output`):** despite the prompt, Ollama occasionally appends commentary or disclaimers (e.g. "(No changes needed...)"), sometimes malformed or cut off mid-sentence. Before trusting any LLM response, it's checked for: text after a double newline, unbalanced parentheses, or being suspiciously longer than the input. If any of these trip, the function falls back to the original sentence unchanged rather than risking a garbled or fabricated result reaching the user.

### ToneRouter — Three Independent, Concurrent Gates
All three gates run on the **original** sentence text (not the grammar-corrected version — see Section 11 for why), concurrently via `asyncio.gather`.

- **Gate 1 — Formality:** `s-nlp/roberta-base-formality-ranker` returns a continuous 0–1 score. If `score < 0.5`, Ollama rewrites the sentence formally.
- **Gate 2 — Passive Voice:** spaCy dependency parse checks for the `nsubjpass` label. If found, Ollama rewrites the sentence in active voice.
- **Gate 3 — Clarity:** Triggered if the **document-level** Flesch Reading Ease score is below 50. If triggered, Ollama simplifies the sentence.

---

## 10. Frontend Features

- **Live word/character count** — computed entirely client-side in JS, no backend call, updates on every keystroke.
- **Manual Analyze button** — always available, forces a full `/analyze` call regardless of automatic timers.
- **Reset button** — calls `/reset`, clears displayed results and backend cache.
- **Formality toggle** — checkbox that hides/shows the formality tag and rewrite suggestion on each sentence card. Re-renders immediately on toggle, without requiring a new `/analyze` call (uses the last cached response).
- **Sidebar per-sentence cards** — color-coded left border by issue type: clay (grammar), ochre (formality), slate (passive voice). Shows original text, corrected text, and any triggered rewrites.
- **Document-level formality reading** — computed client-side by averaging each sentence's `formality_score` from the response (not a separate backend call).
- **Spacebar-triggered spellcheck** — on each spacebar press, the just-typed word is sent to `/spellcheck`. Misspelled words get a wavy underline via a transparent overlay `<div>` positioned exactly behind the textarea (mirrors font/line-height/padding so text aligns pixel-for-pixel).
- **Click-to-accept spellcheck suggestions** — clicking anywhere in the textarea detects the word under the cursor (expanding to nearest whitespace) and, if it's a known misspelling, replaces it with the suggested correction. Casing is preserved (e.g. "Teh" → "The", not "the") by matching the original word's capitalization pattern.
- **Fast inline grammar highlighting** — a separate, ~400ms-debounced check against `/grammar-check` (LanguageTool only, no Ollama call) marks grammar errors with a solid underline as soon as a sentence is completed — well before the full `/analyze` pipeline (with formality/passive/clarity) finishes a few seconds later. Spelling and grammar marks render simultaneously and combine visually if they overlap on the same character.
- **Click-to-accept rewrites from the sidebar** — clicking any suggested rewrite (grammar, formality, passive, or clarity) in a sentence card replaces that sentence in the textarea. Once one rewrite is accepted for a sentence, the other rewrite options on that card are visually disabled (they were computed against text that no longer exists verbatim). Both this and the spellcheck acceptance use `document.execCommand('insertText', ...)` rather than directly setting `.value`, so the browser's native undo (Ctrl+Z) works on every accepted suggestion.
- **Per-suggestion dismiss** — each suggestion in a card has a small dismiss control. Dismissing it is tracked by a `sentence_hash:suggestion_type` key, so it stays hidden across re-renders (including from the debounce/stale timers) as long as the sentence text doesn't change. Editing the sentence produces a new hash, naturally clearing the dismissal.
- **Sentence-boundary debounce** — a lightweight regex (`/[^.!?]+[.!?]+/g`) continuously detects newly-completed sentences (ending in `.`, `?`, or `!`). When a new complete sentence appears, a ~1.8s debounce timer starts; if the user keeps typing, it resets. On firing, only completed sentences are sent to `/analyze` — the in-progress fragment is excluded.
- **Stale-fallback timer** — a separate ~5s inactivity timer always resets on every keystroke, regardless of punctuation. If it fires, the entire current text (including any unpunctuated trailing fragment) is sent anyway — catches sentences the user finished but forgot to punctuate.

---

## 11. Known Limitations & Design Decisions (with evidence)

These were discovered through direct testing, not assumed — see the project's model testing log for full before/after examples.

- **LLM over-rewriting:** phi3.5, when asked to "correct grammar," would initially paraphrase far beyond the flagged error (e.g., rewriting "very very very complicated" as "extremely complex" when only a hyphenation issue was flagged). Mitigated with explicit scope-limiting instructions in the prompt; some residual drift remains on more complex sentences.
- **Pronoun-tracking failures in passive→active rewriting:** the model could swap a possessive pronoun's referent (e.g., "my fatigue" → "his fatigue") when restructuring a sentence with multiple actors. Abstract instructions ("preserve who did what") did not fix this; a one-shot example in the prompt did.
- **Typo-induced rephrasing:** a misspelled word inside an idiomatic phrase (e.g., "to be honst") could cause the model to reinterpret the whole phrase's meaning rather than just fix the spelling. Fixed with a targeted one-shot example.
- **Formality scoring reflects presence/absence of casual markers, not a true formal–neutral–informal spectrum.** Any grammatically complete, slang-free sentence tends to score highly "formal," even plain factual statements. This is a property of the classifier's training data, not a bug.
- **Decision: formality/passive/clarity gates score the original sentence, not the grammar-corrected version** — preserves visibility into genuine casualness markers (slang, contractions) that grammar correction would otherwise erase before the tone gates ever see them.
- **LanguageTool can suppress co-occurring grammar errors** when a nearby typo disrupts its tokenizer — a misspelling can cause an adjacent agreement/double-negative error to go unflagged in the same pass.
- **spaCy `en_core_web_sm` passive detection** is reliable on straightforward constructions but may miss passive voice in more complex or nested sentences — a known limitation of the small model variant.
- **`phi4-mini` was tested as a replacement for `phi3.5`** on the strength of better general instruction-following benchmarks (IFEval), but was found to fabricate content (invented pronouns, invented events) on a pronoun-tracking task in two separate test runs. Reverted to phi3.5 — general benchmark performance did not predict reliability on this specific task.
- **`s-nlp/xlmr_formality_classifier`** (originally scoped) was replaced with `s-nlp/roberta-base-formality-ranker` after testing showed it classified nearly all input as formal, with poor sensitivity to genuinely informal text.
- **Heuristic recall extension trades latency for coverage:** the short-token and missing-determiner heuristics added to catch LanguageTool's recall gaps will sometimes fire on perfectly correct sentences (e.g. bare nouns like "Honesty matters"), triggering an Ollama call that returns the text unchanged. This is treated as an acceptable cost — a wasted ~3–4s call — rather than a false positive shown to the user, since the result is only flagged as an error if Ollama's output actually differs from the input.
- **LLM responses occasionally include commentary or disclaimers despite explicit instructions not to** — sometimes malformed or cut off mid-sentence (likely hitting the token limit). A defensive cleanup step checks for these patterns and falls back to the original sentence unchanged rather than risking a garbled result reaching the user.

---

## 12. Performance Notes

- **Concurrency:** Both gate-level (within one sentence) and sentence-level (across a whole document) Ollama calls run via `asyncio.gather`, not sequentially. This reduced a 3-sentence `/analyze` call from ~30 seconds to ~4–10 seconds in warm-state testing.
- **`--reload` duplicate loading:** Uvicorn's `--reload` spawns a watcher process and an app process, both of which import and load models independently — confirmed via `nvidia-smi` to nearly double VRAM usage during development. Not an issue once `--reload` is dropped for production/demo runs.
- **Flash attention tested and reverted:** enabling `OLLAMA_FLASH_ATTENTION=1` caused a 25%/75% CPU/GPU split and increased the model's memory footprint (3.8GB → 5.6GB) on this hardware — not a net benefit, removed.
- **Cold start:** the first Ollama request after the server starts takes ~15–30 seconds while the model loads into VRAM. `start.bat` mitigates user-facing impact by firing a warmup request before FastAPI begins accepting traffic.

---

## 13. Explicitly Out of Scope

Per project scope: no authentication, no databases, no Docker/Redis/WebSockets, no user accounts, no plagiarism detection, no synonym transformers, no custom grammar engines, no custom syllable counters, no per-sentence readability scores, no cloud deployment, no collaborative editing, no streamed Ollama responses.

---

## 14. Version Control

This project is tracked in git, pushed to GitHub. A `.gitignore` excludes `venv/`, `__pycache__/`, and log files from version control.
