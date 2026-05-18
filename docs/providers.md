# Connecting an LLM provider

deepwolf runs fully offline by default — the built-in `MockProvider` plays
complete games with no network and no keys. To put a *real* model at the table,
you point deepwolf at any endpoint that speaks the OpenAI
`/chat/completions` dialect. This guide covers how.

## The two routes

deepwolf needs three things: a **base URL**, an **API key** and a **model id**.
There are two ways to supply the base URL.

### Route 1 — a named preset

If your provider is well known, name it with `DEEPWOLF_PROVIDER`:

| `DEEPWOLF_PROVIDER` | Base URL |
|---------------------|----------|
| `openai`            | `https://api.openai.com/v1` |
| `deepseek`          | `https://api.deepseek.com/v1` |
| `mimo`              | `https://api.xiaomimimo.com/v1` |
| `mimo-token-plan`   | `https://token-plan-cn.xiaomimimo.com/v1` |
| `groq`              | `https://api.groq.com/openai/v1` |
| `openrouter`        | `https://openrouter.ai/api/v1` |

### Route 2 — a custom base URL

For anything else — a corporate gateway, a local server — set the URL directly
with `DEEPWOLF_BASE_URL`. It overrides `DEEPWOLF_PROVIDER`.

## The `.env` file

Copy `.env.example` to `.env` (it is git-ignored — never commit real keys) and
fill it in:

```bash
DEEPWOLF_PROVIDER=deepseek
DEEPWOLF_API_KEY=sk-your-key-here
DEEPWOLF_MODEL=deepseek-chat
# DEEPWOLF_TEMPERATURE=0.8
# DEEPWOLF_MAX_TOKENS=600
```

Then run any command with `--provider env`:

```bash
deepwolf simulate --provider env --players 7
deepwolf leaderboard --provider env --model deepseek --games 10
```

## Worked example — a local server

Tools like **Ollama**, **llama.cpp** and **vLLM** all expose an OpenAI-compatible
server. Point deepwolf at it with a custom base URL:

```bash
# Ollama, for example, serves on port 11434
DEEPWOLF_BASE_URL=http://localhost:11434/v1
DEEPWOLF_API_KEY=ollama          # most local servers ignore the key, but one is required
DEEPWOLF_MODEL=llama3.1
```

```bash
deepwolf simulate --provider env
```

## Worked example — Xiaomi MiMo

MiMo is OpenAI-compatible. Use the `mimo` preset (or `mimo-token-plan` if your
key is a Token Plan key, which usually starts with `tp-`):

```bash
DEEPWOLF_PROVIDER=mimo
DEEPWOLF_API_KEY=your-mimo-key
DEEPWOLF_MODEL=mimo-v2-flash
```

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `401 Invalid API Key` | Wrong key, an expired key, or the key does not match the base URL. Token-plan keys must use the token-plan endpoint. |
| `missing LLM config` | One of `DEEPWOLF_API_KEY` / `DEEPWOLF_MODEL` / base URL is unset. |
| `unknown DEEPWOLF_PROVIDER` | The preset name is not in the table above — use `DEEPWOLF_BASE_URL` instead. |
| Connection refused | A local server is not running, or the port is wrong. |

A model that occasionally returns malformed output is *not* a problem:
`LLMAgent` validates every decision and falls back to a legal move, so a game
can never be corrupted by a bad reply.

## How it fits together

`LLMConfig.from_env()` reads these variables (loading `.env` first); the
`OpenAICompatProvider` uses that config to call the endpoint. See
[`architecture.md`](architecture.md) for the wider picture.
