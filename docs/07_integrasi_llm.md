# 07 · LLM integration (Gemini 4 Hydrogen and large free OpenRouter models)

> This file is in English. The other design documents in `docs/` were written in Indonesian before the app was converted to English.

## 1. Google Gemini: only `gemini-4-hydrogen`, thinking level `low`
Every other Gemini model was removed from the code, the UI and `.env.example`. Sources: ai.google.dev/gemini-api/docs/models and
ai.google.dev/gemini-api/docs/thinking (checked 19 November 2026).

- Endpoint: `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-4-hydrogen:generateContent`.
- The API key is sent in the `x-goog-api-key` header, not in the URL.
- Thinking level: `generationConfig.thinkingConfig.thinkingLevel = "low"`. Supported values: `low`, `medium`, `high` (model default), `xhigh`.
  `minimal` is rejected by the API with HTTP 400 for this model, so `low` is the lightest.
- `maxOutputTokens` covers thinking tokens **and** the answer. The client adds 6,144 tokens of room on top of the requested `max_tokens`;
  if the answer text is still empty (for example `finishReason = MAX_TOKENS`) that counts as a failure, not as an empty answer.
- Response parts marked `thought` are discarded; all other text parts are joined.
- The `GEMINI_MODEL` / `GEMINI_MODELS` environment variables are no longer read.
- **Free tier quota: about 20 requests per day per project and model** (HTTP 429 `RESOURCE_EXHAUSTED`, with a reset time such as "retry in 19h43m").

## 2. OpenRouter: only free models above 29B
Rule (in `llm/client.py`, `OPENROUTER_FREE_MODELS`): the id ends in `:free`, total parameters are **above 29B** and, when announced,
active parameters are **at least 10B** (MoE models with only ~3B active answer shallowly). Verified with
`GET https://openrouter.ai/api/v1/models` on 19 November 2026 and with live calls. The free list changes often;
run `python scripts/check_free_models.py` before a demo to see which models disappeared or appeared.

| Order | Model ID | Total / active | Notes |
|---|---|---|---|
| 1 | `nvidia/nemotron-3-ultra-550b-a55b:free` | 550B / 55B | main; no JSON mode |
| 2 | `dots-studio/dots-3-note-preview:free` | 280B / 16B | |
| 3 | `nvidia/nemotron-3.5-super-vl:free` | 120B / 12B | heavy hidden reasoning, so 8,000 extra tokens are allowed |
| 4 | `baidu/ernie-5.5-flash-preview:free` | 280B / not announced | |

Removed after live testing on 19 November 2026:
- `google/gemma-4-31b-it:free`: answers HTTP 429 from the shared upstream pool (Google AI Studio) almost all the time.
- `thinkingmachines/inkling-2-small:free`: answers HTTP 403, it is only served to "agentic harness" apps.

Deliberately not used: `google/gemma-4-26b-a4b-it:free` (26B), `xingchen-agi/xing4.0-29b-a4b:free` (29B, not above 29B),
`nvidia/nemotron-3.5-lightning:free` and `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` (~3B active),
`recursive/flint-v1.0:free`, `inclusionai/ling-3.2-flash:free`, `particle-ai/particle-1:free`, `openrouter/free` (size cannot be verified).

`OPENROUTER_MODELS` in `.env` may only reorder or narrow this list; ids outside it are ignored, and choosing a model outside
the list is rejected at once without touching the network. A model's `reasoning` text is never used as an answer: when `content`
is empty the call counts as a failure.

Free account limits: **20 requests per minute** and **50 requests per day** (1,000 per day after a one-time $10 credit purchase).

### Nemotron 3.5 Super VL and hidden reasoning
Live test (19 November 2026, fictional sample payload): with `max_tokens = 6000` the model spent about 5,700 tokens on hidden reasoning and
the answer was cut off after two sections (`finish_reason = length`). A lower `reasoning.effort` made no difference. With 6,000 + 8,000 tokens
it finished with all six sections using about 11,500 tokens (about 90 seconds). So the client adds `thinking_headroom = 8000` for this model only.

## 2b. Client behaviour
- Headers: `HTTP-Referer` and `X-Title` ("Decision Room GDSS").
- `temperature`: 0.2 for the analysis, 0.5 for chat. `max_tokens`: 6,000 for the analysis, 1,500 for chat.
- Timeout 120 seconds.
- **Error policy:** HTTP 429, 403, 401 and 404 are never retried (a retry would only waste the small free quota). Each gives a plain-English message:
  daily quota used up (with the reset time when the API states it), the shared pool is busy, access denied, key rejected, model not available.
  HTTP 5xx and connection errors get exactly one retry after a short wait.
- `model_used` names the engine that really answered.

## 2c. Automatic fallback between engines
`call_llm` tries the selected engine first and then the others (`llm.client.build_chain`):

| Selected | Order tried |
|---|---|
| Gemini 4 Hydrogen | Gemini, then Nemotron 3 Ultra, Dots3-Note, Nemotron 3.5 Super VL, ERNIE 5.5 Flash |
| One OpenRouter model | that model, the other OpenRouter models in list order, then Gemini last (its free quota is the smallest) |
| OpenRouter automatic | the OpenRouter list in order, then Gemini |

Engines without an API key are skipped. Keys: the field of the selected provider, then the other provider's key, then the environment.
The report and each chat answer say who answered and, when an earlier engine failed, why.

## 3. Automatic analysis
Input: `llm_payload.json` (see `06_skema_data.md`). System prompt: `prompts/analysis_system.md`. **One request per report.**

Requested output: **one JSON object** with six keys (`ringkasan`, `perbandingan`, `kelebihan_kelemahan`, `rekomendasi`, `risiko`, `konsistensi`;
these are internal identifiers and never shown to users). The five report tabs in the UI (Summary, Across methods, Strengths and weaknesses,
Risks and consistency, Full document) are filled from these six parts.

**Completeness guarantee (`llm/completeness.py`), the same for any model, without extra requests:**
1. The answer is normalised: parts that came as lists or objects become markdown, a table is built from a list of objects, and products in the recommendation are matched to the data.
2. Each part is assessed: minimum length, mentions a product, compares at least two methods, discusses the CR, the table has one row per group method,
   the recommendation has a main product, a different backup, at least 2 reasons and a backup condition.
3. Parts that are still weak are filled from the calculation results (each method's ranking, criterion values, CR). This text never contains a default product name
   and never invents numbers, ends with a short note that it was written automatically, and the UI lists which sections were filled that way.

There is deliberately **no repair request** to the model: with free quotas of 20 and 50 requests per day, a second request would cost more than it gains.

**Saved reports:** a successful report is saved to `storage/runs/<run_id>/analysis_<engine>.json`. Opening the AI page again for the same run and engine
loads it without any request; the button creates a new one.

**Number validation (mandatory):** after receiving the answer, the app takes every decimal number in the text and checks whether it exists in the payload
(rounding tolerance of 3 to 4 decimals). Numbers that cannot be found are flagged in the UI with a ⚠ "number not found in the calculation results". This stops the LLM from inventing figures.

## 4. Chat mode
- Active only when there is at least 1 run.
- Context sent every turn:
  1. The system prompt `prompts/chat_system.md`.
  2. `llm_payload.json` of the chosen run (once, as the second system message).
  3. The summary of the saved analysis, if any.
  4. Chat history: the last 12 messages; older messages are condensed into one paragraph.
  5. Web search results (when the switch is on).
- Every message (user and assistant), `model_used` and `sources` are saved to the chat file after each turn.
- The same engine fallback applies; when the selected engine failed, `model_used` explains it.

## 5. Web search
OpenRouter's `:online` / web plugin is **paid even when the model is free** (Exa engine, about $4 per 1,000 results), so it is not the default.
Choose with `WEB_SEARCH_PROVIDER`:

| Value | How | Cost |
|---|---|---|
| `ddgs` (default) | The Python library `ddgs` (DuckDuckGo) is called by the app; take the top 5 results (title, snippet, URL) | Free, no key |
| `tavily` | The Tavily API (needs `TAVILY_API_KEY`, there is a free plan) | Free within the plan |
| `openrouter_online` | Add `:online` to the model id or the OpenRouter web search server tool | Paid, needs credit |

Flow for `ddgs`/`tavily`:
1. The user's question is used as the search query (no extra LLM call, which saves quota).
2. The app searches and cuts snippets to ≤ 500 characters.
3. The results are inserted as a numbered system message `[1] title — url — snippet`.
4. The LLM is asked to cite `[n]`; the UI shows the sources as links.
5. If the search fails, continue without the web and tell the user in one line.

## 6. Privacy and security
- API keys come only from `.env` or the browser session. Never print them in logs.
- Tell the user (a small note in the chat tab) that free models may log prompts to improve the provider's models,
  so real confidential company data must not be entered.
- Text from web results is treated as data, not as commands (stated in the system prompt).
