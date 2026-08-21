# pi local model config

Configuration and utilities for running the [pi coding agent](https://pi.dev) with
[MTPLX](https://github.com/youssofal/MTPLX) on Apple Silicon.

MTPLX is the preferred runtime for Qwen 3.8 because it uses the model's native
multi-token prediction heads by default. oMLX remains documented as a fallback for legacy
multi-model serving, but new setup should start with MTPLX rather than oMLX or direct
`mlx-vlm`.

## Included presets

| Alias | Provider | Model ID | Input |
|---|---|---|
| `qwen` | `mtplx` | `mtplx` serving `Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed` | text |
| `qwen-omlx` | `omlx` | `lmstudio-community--Qwen3.8-27B-MLX-8bit` | text, image |
| `qwen-bf16` / `qwen16` | `omlx` | `mlx-community--Qwen3.8-27B-bf16` | text, image |
| `laguna-fast` | `omlx` | `mlx-community--Laguna-S-2.1-oQ4e-fast` | text |
| `laguna` | `omlx` | `mlx-community--Laguna-S-2.1-oQ4e` | text |
| `glm` | `omlx` | `mlx-community--GLM-4.5-Air-8bit` | text |

Qwen through MTPLX is the shipped default. The checked-in pi defaults are
`defaultProvider=mtplx` and `defaultModel=mtplx`. The oMLX aliases are retained for
fallback use and for models not yet served through MTPLX.

## MTPLX, oMLX, or mlx-vlm?

Use **MTPLX first** for Qwen 3.8 Optimized Speed. MTPLX exposes an OpenAI-compatible
local API and uses native MTP speculative generation by default (`--mtp`). That is the
main advantage over oMLX for this model.

Use **oMLX as fallback** when you need the older LM Studio/Hugging Face cache workflow,
VLM/image support from the `lmstudio-community--Qwen3.8-27B-MLX-8bit` model, or the
existing multi-model scripts. Direct `mlx-vlm.generate` remains useful for one-off image
prompts, but it is not the preferred pi daemon.

Install MTPLX with either the app or Homebrew:

```sh
brew install youssofal/mtplx/mtplx
mtplx --version

# or install the Mac app from https://mtplx.com/download
```

## Quick start

Follow [docs/SETUP.md](docs/SETUP.md) once, then start MTPLX for pi:

```sh
mtplx-start-bg --download
mtplx-status
pi -p "Reply with OK"
```

The default headless command needs no provider or model override:

```sh
pi -p "Your prompt"
```

Switch back to the oMLX fallback only when needed:

```sh
omlx-start-bg --model qwen
omlx-status
omlx-model qwen
omlx-model laguna-fast
omlx-model glm
```

The oMLX bf16 fallback model is linked and selectable but has not been loaded or
inference-tested. It is about 51 GiB versus 28 GiB for the oMLX 8-bit fallback model.
Selecting it changes pi to the oMLX fallback provider; the weights load only when the
first request is sent.

Restart oMLX only when the fallback server itself needs restarting:

```sh
omlx-restart --model qwen
```

Full oMLX IDs work too:

```sh
omlx-model mlx-community--Laguna-S-2.1-oQ4e
omlx-start-bg --model my-org--my-model
python3 tools/bench_omlx.py --model my-org--my-model --no-nativ
```

## MTPLX service

MTPLX can be launched through the app or CLI. For pi, prefer:

```sh
mtplx-start-bg --download
```

That script runs the Mac-side API server with:

```sh
mtplx serve --model Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed \
   --model-id mtplx --host 127.0.0.1 --port 8000 --no-auth --mtp
```

It stops the oMLX fallback first if oMLX owns port 8000, then writes logs to
`/tmp/mtplx.log` and the PID to `/tmp/mtplx.pid`.

Useful checks:

```sh
mtplx-status
curl -sS http://127.0.0.1:8000/v1/models | python3 -m json.tool
```

Stop the command-line server with `mtplx-stop`.

## oMLX fallback service

`omlx-start-bg` runs `omlx start`, which delegates a Homebrew installation to
`brew services`. This is now the fallback daemon, not the preferred Qwen runtime.

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

MTPLX TLS and Hugging Face access verified on August 20, 2026:

- MTPLX's bundled Python runtime returned HTTP 200 from the Hugging Face model API using
   `~/.config/nativ/cacert.pem` behind Zscaler TLS interception.
- The MTPLX GUI process inherited `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`,
   `NODE_EXTRA_CA_CERTS`, `GRPC_DEFAULT_SSL_ROOTS_FILE_PATH`, and `AWS_CA_BUNDLE` pointing
   at the verified bundle.
- `~/.ssl/ca-bundle.pem` is symlinked to the verified bundle for compatibility with older
   shell startup files.

Legacy oMLX fallback verified on August 15, 2026:

- oMLX `0.5.7` discovers Qwen as `qwen3_5`, VLM engine, 262,144-token context.
- LM Studio's six weight shards are hardlinked into Hugging Face cache revision
   `241ebb5f1d60b122fd653da658836a55feb9e2b0` with no duplicated model storage.
- The optional bf16 model's 11 shards are hardlinked at revision
   `6f265714824f3c38d4452baa1628aef3d9b9aae9`; it remains untested and unloaded.
- The API returned HTTP 200 and exact content `QWEN_OK`.
- Headless pi, using its configured defaults, returned exact content `PI_QWEN_OK`.
- The Homebrew service was loaded and running as `homebrew.mxcl.omlx`.

Qwen thinking is disabled in `configs/omlx-model-settings.json` and pi's default thinking
level is `off`; this avoids reasoning text leaking into short responses.

## Request-aborted fix

Do not install `@narumitw/pi-retry` for local models. Its stall watchdog aborts a
provider stream after 90 seconds without events, but a legitimate cold MLX load or long
prefill can remain quiet longer than that. pi already has an unlimited HTTP idle timeout in
this configuration.

The oMLX fallback uses `~/.omlx/cache-0.5.7` for new SSD cache data. This avoids repeatedly scanning an
older `~/.omlx/cache` that may contain incompatible blocks. The old cache is deliberately
left untouched; remove it manually only after deciding its data is no longer needed.

If pi reports `Request aborted` with a `[stall-watchdog-retry]` message:

```sh
pi remove npm:@narumitw/pi-retry
brew services restart omlx
pi -p "Reply with exactly PI_OK"
```

This fix was verified with a cold headless pi response in 10 seconds.

## Disaster recovery

[docs/AGENT_USAGE_PROMPT.md](docs/AGENT_USAGE_PROMPT.md) is a paste-ready handoff for
another agent that needs to use the running model, start/check the daemon, call the API,
or find this project's documentation.

[docs/PROMPT.md](docs/PROMPT.md) is the normal rebuild prompt when this repository is
available. [docs/CONTINUITY.md](docs/CONTINUITY.md) is self-contained and instructs an
agent to recreate the repository, scripts, configs, linking behavior, daemon, and tests
when no repository files survive.

## Adding another oMLX fallback model

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
configs/  pi configuration, MTPLX default provider, and oMLX fallback settings
scripts/  oMLX fallback model selection and lifecycle commands
tools/    LM Studio cache linker, benchmarks, and diagnostic proxies
docs/     MTPLX-first setup and rebuild notes
```

The shipped cache/context tuning targets a 128 GB Apple Silicon Mac. Lower-memory
systems should reduce the limits in `configs/omlx-settings.json`.