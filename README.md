# pi local model config

Configuration and utilities for running the [pi coding agent](https://pi.dev) with any
local MLX model served by [oMLX](https://github.com/jundot/omlx) on Apple Silicon.

One oMLX daemon discovers every model in its configured directories and Hugging Face
cache, then loads the model requested by pi. The `--model` option changes pi's default;
it does not limit which models oMLX can serve.

## Included presets

| Alias | oMLX model ID | Input |
|---|---|---|
| `qwen` | `lmstudio-community--Qwen3.8-27B-MLX-8bit` | text, image |
| `laguna-fast` | `mlx-community--Laguna-S-2.1-oQ4e-fast` | text |
| `laguna` | `mlx-community--Laguna-S-2.1-oQ4e` | text |
| `glm` | `mlx-community--GLM-4.5-Air-8bit` | text |

Qwen is the shipped default. Running `omlx-start`, `omlx-start-bg`, `omlx-restart`, or
`omlx-model` without a model argument selects Qwen and the `omlx` pi provider. Aliases
are conveniences, not a closed list: any model ID returned by `GET /v1/models` can be
selected after its metadata is added to pi.

## oMLX or mlx-vlm?

The Qwen model card recommends `mlx-vlm` because Qwen3.8-27B is a vision-language
model. Use **oMLX for pi**: oMLX includes `mlx-vlm`, exposes VLMs through an
OpenAI-compatible API, and adds multi-model serving, caching, memory management, and a
managed macOS service. Direct `mlx-vlm.generate` remains useful for one-off image
prompts, but it is not the daemon configured here.

Use oMLX `0.5.7` or newer for current Qwen VLM support:

```sh
omlx --version
brew update && brew upgrade omlx
```

## Quick start

Follow [docs/SETUP.md](docs/SETUP.md) once, then after LM Studio finishes downloading:

```sh
python3 tools/link_lmstudio_to_hf.py lmstudio-community/Qwen3.8-27B-MLX-8bit
omlx-start-bg --model qwen
omlx-status
pi -p "Reply with OK"
```

The default headless command needs no provider or model override:

```sh
pi -p "Your prompt"
```

Switch pi's default without restarting the multi-model daemon:

```sh
omlx-model laguna-fast
omlx-model glm
omlx-model qwen
```

Restart only when the server itself needs restarting:

```sh
omlx-restart --model qwen
```

Full oMLX IDs work too:

```sh
omlx-model mlx-community--Laguna-S-2.1-oQ4e
omlx-start-bg --model my-org--my-model
python3 tools/bench_omlx.py --model my-org--my-model --no-nativ
```

## macOS service

`omlx-start-bg` runs `omlx start`, which delegates a Homebrew installation to
`brew services`. The daemon is oMLX, not standalone `mlx-vlm`.

```sh
omlx-start-bg --model qwen  # managed background service
omlx-start --model qwen     # foreground server
omlx-restart --model qwen   # force-stop and relaunch
omlx-stop
omlx-status
```

Service logs are in `$(brew --prefix)/var/log/omlx.log` and
`~/.omlx/logs/server.log`. `omlx-restart` writes `/tmp/omlx.log`.

## Verified installation

Verified on August 15, 2026:

- oMLX `0.5.7` discovers Qwen as `qwen3_5`, VLM engine, 262,144-token context.
- LM Studio's six weight shards are hardlinked into Hugging Face cache revision
   `241ebb5f1d60b122fd653da658836a55feb9e2b0` with no duplicated model storage.
- The API returned HTTP 200 and exact content `QWEN_OK`.
- Headless pi, using its configured defaults, returned exact content `PI_QWEN_OK`.
- The Homebrew service was loaded and running as `homebrew.mxcl.omlx`.

Qwen thinking is disabled in `configs/omlx-model-settings.json` and pi's default thinking
level is `off`; this avoids reasoning text leaking into short responses.

## Disaster recovery

[docs/PROMPT.md](docs/PROMPT.md) is the normal rebuild prompt when this repository is
available. [docs/CONTINUITY.md](docs/CONTINUITY.md) is self-contained and instructs an
agent to recreate the repository, scripts, configs, linking behavior, daemon, and tests
when no repository files survive.

## Adding another model

1. Download an MLX model with LM Studio, Hugging Face, or the oMLX dashboard.
2. For LM Studio, run `link_lmstudio_to_hf.py <org/repo>`.
3. Confirm its API ID with `omlx-status`.
4. Add its metadata under the `omlx` provider in `configs/pi-models.json` and reinstall
   that file to `~/.pi/agent/models.json`.
5. Select it with `omlx-model <api-model-id>`.

The linker accepts multiple model IDs. With no IDs, it links every complete MLX model
under `~/.lmstudio/models`.

## Layout

```text
configs/  oMLX and pi configuration
scripts/  model selection and oMLX lifecycle commands
tools/    LM Studio cache linker, benchmarks, and diagnostic proxies
docs/     setup and rebuild notes
```

The shipped cache/context tuning targets a 128 GB Apple Silicon Mac. Lower-memory
systems should reduce the limits in `configs/omlx-settings.json`.