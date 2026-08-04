# AGENTS.md

## What this repo is

VerifiCuba: a Cuban business directory ("negocios verificados"). Four components that share the `negocios` concept but are NOT in sync:

- `~/verificuba/landing/index.html` — single static `index.html` (inline CSS/JS, no build step). Deployed to Netlify at `https://verificuba.netlify.app`. The `#regForm` submits directly to PocketBase REST API (`/api/collections/negocios/records`) via CORS (configured with `--origins="https://verificuba.netlify.app"`). No build step.
- `~/verificuba-new/telegram-bot/` — Node ESM (telegraf + axios + express), runs in Docker/podman. Queries **PocketBase** (not NocoDB) via REST API at `http://localhost:8090/api/collections/...` with admin token. Does NOT touch NocoDB.
- `~/verificuba/mcp_server.py` — Python FastMCP (stdio) talking to **PocketBase** REST at `http://localhost:8090`.
- `~/verificuba/pocketbase` binary + `~/verificuba/pb_data/` + `~/verificuba/pb_migrations/` — the local backend that is actually live.

**Two backends exist in parallel but ONLY PocketBase is live:** PocketBase (binary, live on :8090 with SQLite). NocoDB (docker) is NOT running. Changes to one do not affect the other. Ask before assuming which store a task targets.

## Commands

- PocketBase (the live backend): `./pocketbase serve --http=0.0.0.0:8090 --dir=./pb_data --origins="https://verificuba.netlify.app,http://localhost:8000"` → API on :8090, admin UI at `http://localhost:8090/_/`. JS migrations in `pb_migrations/` auto-apply on serve.

- **Public exposure = Cloudflare quick tunnel (working, auto-repairing).** `cloudflared tunnel --url http://localhost:8090` exposes PocketBase at a random `https://<id>.trycloudflare.com`. `scripts/tunnel-sync.sh` runs as systemd user service `verificuba-tunnel`, detects the new URL on each restart, updates `PB_URL` in `~/verificuba-new/landing/index.html`, commits and pushes → Netlify redeploys. Log: `~/verificuba/logs/tunnel.log`. Restart: `systemctl --user restart verificuba-tunnel`; status: `systemctl --user status verificuba-tunnel`. Linger enabled, survives reboot. **The quick-tunnel URL is random per restart — never hardcode it; let the script manage it.**

- **Tailscale Funnel is NOT working in this network.** `tailscale funnel --bg 8090` configures OK, but DERP relay fails through Cloudflare WARP (UDP blocked, DERP resets, no IPv4, netcheck shows DERP unknown). The fwmark fix (pref 5199) routes tailscaled traffic through WARP but does NOT fix DERP relay. Funnel URL `https://fedora.taile44d23.ts.net` is configured but not publicly reachable. Keep as potential future option if network changes.

- **Critical networking quirk (Cuba/ETECSA + Cloudflare WARP):** WARP (`warp-svc`, always on) provides internet access. ISP blocks direct Tailscale control plane/DERP. WARP routes non-marked traffic (`fwmark 0x100cf` bypass) through its tunnel. tailscaled marks its own traffic `0x80000` → routed via main table → direct → blocked. Fix `ip rule add fwmark 0x80000/0xff0000 lookup 65743 pref 5199` routes tailscaled traffic through WARP (allows control plane auth), but **does not fix DERP relay** (DERP still resets). `warp-keepalive.service` (root) re-adds rule every 30s + keeps WARP connected, survives reboots.

- If cloudflare tunnel breaks: check `systemctl --user status verificuba-tunnel`, `~/verificuba/scripts/tunnel-sync.sh` manually, `curl <current_trycloudflare_url>/api/health`.
- To get a fresh tunnel URL: `pkill cloudflared; cloudflared tunnel --url http://localhost:8090 --no-autoupdate` → wait for URL → run `~/verificuba/scripts/tunnel-sync.sh` or wait for service.

- MCP server: `python3 mcp_server.py` (needs `pip install mcp httpx`; both already installed). Env: `POCKETBASE_URL` (default `http://localhost:8090`), `POCKETBASE_ADMIN_EMAIL`, `POCKETBASE_ADMIN_PASSWORD`. Runs on stdio.

- Telegram bot: `cd ~/verificuba-new && podman build -t verificuba-telegram-bot ./telegram-bot && podman run -d --name verificuba-telegram-bot --network host -e BOT_TOKEN=... -e CHAT_ID=... -e PB_URL=http://localhost:8090 -e PB_ADMIN_EMAIL=... -e PB_ADMIN_PASS=... verificuba-telegram-bot`

- Docker stack (not currently used): `docker compose up` would start NocoDB (:8080) + telegram-bot but NocoDB is NOT running.

- `scripts/backup-now.sh` is **stale/broken**: it `docker compose exec postgres pg_dump`s, but PocketBase uses SQLite (single file `pb_data/data.db`). Backup = `cp pb_data/data.db pb_data/data.db.bak`. Fix before using.

## Data model (PocketBase)

Collections (from `pb_migrations/`): `categorias`, `negocios`, `facturas`, `obligaciones_fiscales`, `resenas`, `transacciones`.

`negocios` key fields: `nombre`, `tipo_actor` (TCP/MIPYME/CNA/Estatal), `categoria` (relation → `categorias`), `provincia`/`municipio`, `whatsapp`, `plan` (Básico/Verificado/Destacado/Proveedor B2B), `estado` (Pendiente/Verificado/Activo/Suspendido), `slug` (unique), `indice_confianza`, `fecha_verificacion`.

Access rules: `negocios.listRule` exposes only `estado = 'Verificado' || estado = 'Activo'`; `createRule` is open (public pre-registration); update/delete closed.

## Git / hygiene

- Never commit `pocketbase`, `*.zip`, `pb_data/` (live DB), `uploads/`, `nocodb-data/`. `.env` is gitignored.
- `pb_migrations/` is source of truth for schema but is currently **untracked** (commit `2618e89` removed it). Re-add the migration files when modifying schema.
- Schema changes go in `pb_migrations/*.js` (generated by PocketBase), not by editing `pb_data/data.db` directly.
- Landing page deployed to Netlify (`https://verificuba.netlify.app`) via GitHub (`github.com/robe9312/verificuba`), auto-deploys on push. **IMPORTANT: the repo that is actually pushed/deployed is `~/verificuba-new`** (its `origin/main` matches the remote); `~/verificuba` is a local copy with **divergent git history** (`db1ce67/2618e89`) that must NOT be pushed (would need force-push/merge). To get a landing edit live: sync the file into `~/verificuba-new/landing/index.html`, commit and push there.
- Telegram bot code at `~/verificuba-new/telegram-bot/` (Dockerfile, package.json, index.js).
- MCP server at `~/verificuba/mcp_server.py` (FastMCP, stdio transport).
- PocketBase binary at `~/verificuba/pocketbase`, data at `~/verificuba/pb_data/`.

## Conventions

- All user-facing copy is Spanish (Cuba context: ONAT, ETECSA, CUP). Keep it in `es`.
- `mcp_server.py` hardcodes a default admin email (`arangorobe380@gmail.com`) and requires the password via env — override both via env in non-local runs.
- No tests, no lint config, no root package.json. Verification is manual (start PocketBase, hit its API / run the MCP tools).
- Form submits from Netlify (`https://verificuba.netlify.app`) → PocketBase (`http://localhost:8090/api/collections/negocios/records`) via CORS (configured with `--origins="https://verificuba.netlify.app,http://localhost:8000,http://localhost:8090"`).
- Telegram bot code at `~/verificuba-new/telegram-bot/` (Dockerfile, package.json, index.js) uses PocketBase REST API, NOT NocoDB.
- MCP server at `~/verificuba/mcp_server.py` (FastMCP, stdio) talks to PocketBase REST API.
- NocoDB is NOT running. Only PocketBase is live.

## Network / troubleshooting quick reference

```
# Check cloudflare tunnel status
systemctl --user status verificuba-tunnel
tail -f ~/verificuba/logs/tunnel.log

# Check current PB_URL in deployed landing
curl -s https://verificuba.netlify.app | grep PB_URL

# Manual tunnel refresh (if auto-sync stuck)
pkill cloudflared
cloudflared tunnel --url http://localhost:8090 --no-autoupdate > /tmp/cf.log 2>&1 &
sleep 8
grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/cf.log | head -1

# Check PocketBase health via current tunnel
curl -s $(curl -s https://verificuba.netlify.app | grep -oE "PB_URL\s*=\s*['\"][^'\"]*" | cut -d"'" -f2)/api/health

# WARP/DERP diagnostics (if debugging Tailscale)
warp-cli status
tailscale netcheck
tailscale status
```

## Admin credentials

PocketBase admin: `arangorobe380@gmail.com` / password in `~/.hermes/skills/offline-first/pocketbase-business-directory/scripts/seed-categories.sh` (rotate after exposing admin via any public tunnel).