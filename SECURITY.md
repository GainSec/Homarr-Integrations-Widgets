# Private configuration

Keep actual passwords, API tokens, OAuth client secrets, peer inventories, analytics caches, Caddyfiles, SSH keys and runtime state outside this checkout. Examples identify the fields and private file paths where values belong. Create credentials on the host that runs the relevant collector/helper; use file mode 600 and private directories. Configure Homarr's server-side source credential separately. Browser bundles and widget JSON must never contain a bearer token.

Collectors enforce a bearer token and exact connecting-peer allowlist. Put them behind encrypted transport or a trusted encrypted network; do not expose them openly. Your proxy/container networking can change the observed peer address. Follow each package's checks rather than weakening its allowlist.

Dashboard visibility controls who can see returned data. Tailscale peer names, gateway clients, repository metadata and WordPress stats can be personal information even when upstream credentials stay hidden. The Hermes bridge must be protected by an authenticated private dashboard/proxy; anyone who can use it can request the owner's permitted Hermes actions. The guest Assistant patch is a different, text-only integration.

Domain manager is privileged: review its Docker/Caddy/Technitium access, scoped DNS token and password setup before installing. Backups can contain secrets; keep them private. Caddy changes use validation and graceful reload, not a compose down/up cycle.

Before publishing local changes, review staged files and run a secret scanner such as `gitleaks dir . --redact`. The ignore rules are a convenience, not a substitute for review. If a credential is committed, revoke it immediately and clean history before further distribution. Report sensitive vulnerabilities privately through your hosting provider's private reporting channel when available; do not paste credentials into issues.
