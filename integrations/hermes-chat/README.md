# Hermes chat

Chat-only iframe bridge for a **private** Homarr dashboard. Uses the existing personal Hermes profile and common session database: separate dashboard conversations can be found by Discord Hermes through `session_search`. It does not mirror a Discord channel or start a second Discord listener.

Browser assets contain no gateway tokens or credentials. A server-side same-origin proxy injects a new narrow bridge bearer token; the bridge enforces exact peer IP, POST Origin and custom header. Hermes API stays loopback-only behind a separate token. The UI supports streaming, Stop, New chat, local transcript and shared session ID copying, and renders text via `textContent`.

This is an adapter for an **existing managed Hermes installation**, not a self-contained Hermes distribution. It depends on internal `hermes_bootstrap`, `gateway.config.PlatformConfig`, and `gateway.platforms.api_server.APIServerAdapter` interfaces. Initially validated against Hermes commit `c57331677d7fc46298a7159cf3a650853f0966c5`; revalidate compatibility after upgrades. Existing model configuration, permissions and API-platform tool policy apply. The API toolset can differ from Discord's; do not bypass that policy.

See [INSTALL.md](INSTALL.md). Do not expose the proxy on a public/guest dashboard: any user allowed to open it can submit requests to the owner's Hermes and use its permitted tools. The bridge is not a privilege sandbox. Revoke access at the dashboard/proxy authentication layer.

Offline tests: `python3 -m unittest discover -p 'test_*.py'`; `node --check chat.js`.
