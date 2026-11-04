# Frontier data

Public source feed and daily guide publisher for https://usefrontier.vercel.app. This repository contains public research and updater code, never personal bookmarks, imports or browser history.

The scheduled GitHub Actions job runs daily at 09:17 Asia/Dubai (05:17 UTC). It collects 14 source families, then runs the open Qwen3-4B model on the temporary GitHub-hosted runner. No model API account or key is required. The model and llama.cpp revisions are pinned; the model download is checked with SHA-256. Nothing runs on the user's computer. The application stays a static frontend on Vercel.

The writer chooses up to two reusable new concepts or substantive revisions, preserving IDs and first addition dates. Each full guide contains a definition, mechanism, relevance, example, limitations and a suggested POC with ordered steps and success checks. A separate AI review pass and schema validation precede the atomic Git commit. AI review does not establish correctness or replace expert review; POCs are not executed by the publisher. A day with no worthwhile additions may publish zero new guides. Failed generation or validation preserves the previous publication.

Sources include OpenAI, Anthropic engineering/research, Google DeepMind/Research, Hugging Face blog/papers, LangChain, Cursor, Simon Willison, Latent Space, arXiv, official releases and Hacker News. Original source excerpts are limited to 25 words each; full explanations are original drafts with citations. Source failures retain the prior source snapshot and timestamp.

Feed: public/data/publication.json. History: public/data/history/YYYY-MM-DD.json. The feed includes its last successful timestamp, source health and a link to its actual workflow run. Daily history is retained without automatic deletion.

Model: Qwen/Qwen3-4B-GGUF, Apache-2.0, https://huggingface.co/Qwen/Qwen3-4B-GGUF. Runtime: ggml-org/llama.cpp, MIT, https://github.com/ggml-org/llama.cpp. Runtime downloads remain on the ephemeral runner and are not committed. Only public source data is sent to this local model.
