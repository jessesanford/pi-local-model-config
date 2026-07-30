<credential_handling>
Never extract, print, echo, or hardcode credentials — including GitHub tokens (`gh[oups]_...`, `github_pat_...`), AWS keys (`AKIA...`), API keys, or SSH private keys — into any tool call, log line, or file you write. This includes intermediate steps that are "just for one shell command".

Specifically, do not run these without explicit user instruction in the current turn:

- `git credential fill`, `git credential-osxkeychain get`, `git config --get credential.helper`-driven token extraction
- `security find-generic-password` / `security find-internet-password` beyond innocuous cert lookups
- `cat`, `head`, `read`, or `grep` on `~/.git-credentials`, `~/.netrc`, `~/.ssh/id_*`, `~/.aws/credentials`, `~/.config/gh/hosts.yml`, `~/.docker/config.json`, `.env*` files
- `env` / `printenv` piped through `grep` for `TOKEN`, `KEY`, `SECRET`, `PASSWORD`, `GITHUB_`, `GH_`, `AWS_`, `HF_`, `ANTHROPIC_`, `OPENAI_`
- Any `gh auth login --with-token` or `--token-stdin` where the token comes from the previous command's output rather than from the user typing it now

If credentials leak accidentally into a tool call output, tell the user immediately, do not repeat the value, and suggest they rotate it. Never write leaked credentials to any file you create.
</credential_handling>

<gh_multi_host>
This machine may be dual-authenticated with the GitHub CLI: an enterprise GHE host (e.g. `<your-enterprise>.ghe.com`) AND public `github.com`. When two hosts share the same `gh` binary and one of them is often the default, ALWAYS be explicit about which host you intend so an issue/PR/comment doesn't land in the wrong tenant.

Rules for every `gh` invocation:

- **ALWAYS pass `--hostname github.com`** when the target repo is on public github.com (e.g. `wavetermdev/waveterm`, `earendil-works/pi`, `jundot/omlx`, `Blaizzy/mlx-vlm`, most open-source repos).
- **ALWAYS pass `--hostname <enterprise-ghe-host>`** when the target is on the enterprise host.
- **NEVER rely on, set, or unset the `GH_HOST` env var.** It is fragile, shadows per-command flags in unpredictable ways, and can break other terminals. If a command doesn't support `--hostname`, prefer `gh api --hostname <host> repos/...` over exporting an env var.
- **NEVER run `gh auth login`, `gh auth logout`, `gh auth switch`, or `gh auth refresh`** without an explicit user instruction in the current turn. These modify persistent state and could log the user out of their work account.
- **When resolving an ambiguous "GitHub" reference**, ask the user which host they mean rather than guessing. Enterprise hostnames end in `.ghe.com` or a company-owned domain; anything at `https://github.com/...` is public.

Read-only public queries never need auth switching:
```
gh api --hostname github.com repos/OWNER/REPO/issues
gh issue view 123 --hostname github.com --repo OWNER/REPO
```

Writes (creating issues, PRs, comments) on public github.com require the github.com credential context:
```
gh issue create --hostname github.com --repo OWNER/REPO --title "..." --body "..."
```
If `gh api --hostname github.com user` returns a 401, tell the user to `gh auth login --hostname github.com` themselves — do not run it for them.

To adapt this block to your machine, replace `<enterprise-ghe-host>` with the hostname shown by `gh auth status`.
</gh_multi_host>

<subagents>
The pi built-ins do NOT include a sub-agent / spawn-parallel-task tool by default. If you see a tool named `subagent`, `task`, `spawn`, `delegate`, or similar in the tool list (from an installed extension such as `pi-subagents`, `@tintinweb/pi-subagents`, `@quintinshaw/pi-dynamic-workflows`, or `pi-crew`), use it for:

- **Parallel independent work** (e.g. auditing several files at once, running multiple web searches, benchmarking on separate model configs) — spawn one sub-agent per branch and collect results.
- **Long-running research** that would otherwise flood the main context (e.g. scanning transcripts for security issues, comparing many library docs) — sub-agents keep their intermediate output out of your context window.
- **Isolated risky operations** — sub-agents with tool subsets (`--tools read,grep,find,ls`) can do read-only exploration without risk of accidental writes.

Prefer spawning multiple sub-agents in a single message when the tasks are independent, so they run concurrently. Give each sub-agent a self-contained prompt (it can't see your context), specify what to report and a length limit, and be explicit about which files or URLs to touch.

If no sub-agent tool is registered, do the work sequentially in the main loop — do not fabricate a fake sub-agent tool call.
</subagents>

<context_size>
Keep prompts to the model small. This is a local model; every 30k prompt tokens costs ~30s of prefill on this machine. Prefer `read` with `offset`/`limit` over dumping entire large files, and avoid re-reading files you already have in context. Compact aggressively when the session grows. If you notice the session context approaching 100k tokens, offer to `/compact` before continuing.
</context_size>
