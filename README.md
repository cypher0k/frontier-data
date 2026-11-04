# Frontier public data

[Open the app](https://usefrontier.vercel.app) · [Publisher runs](https://github.com/cypher0k/frontier-data/actions/workflows/frontier-daily.yml)

This repository contains public source research, complete AI-written guides and the scheduled updater for frontier /. Personal imports, bookmarks and browser archive data are not uploaded here. The Vercel app is a static frontend that reads this JSON directly; new data does not require an app redeploy.

## Schedule and model

The GitHub Actions workflow runs daily around **09:17 Asia/Dubai (05:17 UTC)**, on publisher changes, or with Run workflow. GitHub can queue scheduled starts. It runs Qwen3.5-4B using a pinned LM Studio community Q4_K_M GGUF conversion through pinned official llama.cpp on a temporary standard GitHub-hosted Ubuntu runner. The download is checksum verified. No model API account/key or always-running server is needed. Model weights and runtime files are temporary and never committed.

The job collects 14 feeds spanning labs, engineering, research, practitioners, releases and discussion. Hacker News is an engagement signal, not the primary evidence source. Candidate selection reserves room for papers, engineering and practitioner reports instead of filling the context with lab announcements. It writes zero or one worthwhile new or substantially revised concepts with a full mechanism, original explanation and suggested POC. There is no manufactured daily quota.

A focused model pass designs a feasible no-API learning exercise, then a separate model call checks drafts against source excerpts, then deterministic validation checks dates, IDs, citations and complete POCs. These are AI checks, not human verification or independent experimental reproduction. POCs are suggestions, not executed results. A guide-generation failure retains previous guides, publishes successfully collected sources and records the failure for display in the app. Failed source collection or publication validation preserves the previous feed.

## Files

- `public/data/publication.json`: cumulative full guides, current source items, health, actual generation time, real run URL, guideStatus and available history dates.
- `public/data/history/YYYY-MM-DD.json`: dated Dubai-calendar-day editions; older editions remain available to the app even if it was closed.
- `public/data/sources.json`: source registry and collection methods.
- `publisher/catalog-index.json`: public guide IDs, names and aliases to avoid duplicates and preserve identity on revisions.
- `publisher/refresh.py`: collection, source selection, model draft/check and atomic publication.
- `publisher/bootstrap-model.sh`: pinned official runtime/model and checksum.

The workflow uses its short-lived repository-scoped GitHub token for release collection and publishing. Never add credentials, private documents, browser data, `.env` files, model binaries or logs to this public repository.

## Checks

`python3 -B -m unittest discover -s tests -p 'publisher_test.py'`

`python3 publisher/validate.py`

Failed runs are visible in Actions. The app labels a publication overdue after 36 hours and keeps the last valid data. Standard public-repository GitHub-hosted runners require no model API key. Changes to GitHub service availability or policy can affect scheduling.

