# Homarr integrations and widgets · Workshop release

Independent packages for a self-hosted Homarr dashboard. Copy just the integration folder you need: each contains its own source, configuration examples, README and installation/removal instructions. No personal dashboard export, credentials, device inventory or runtime data is included.

| Package | Provides | Runtime |
|---|---|---|
| [ArcticBase Workbenches](integrations/arcticbase-workbenches/) | Filterable workbench metadata | Python collector |
| [Tailscale](integrations/tailscale/) | Connected peers; optional offline devices | Python + local Tailscale CLI |
| [UniFi gateway](integrations/unifi-gateway/) | Gateway metrics and paginated clients | Python + UniFi OS |
| [OpenWrt gateway](integrations/openwrt-gateway/) | Gateway metrics and paginated clients | Python + restricted SSH snapshot |
| [Gitea repositories](integrations/gitea-repositories/) | Recently updated repositories | Direct Gitea API |
| [Codex usage](integrations/codex-usage/) | Signed-in local account quota windows | Python on signed-in Mac |
| [Claude usage](integrations/claude-usage/) | Local Claude Code status-line quota cache | Python + status-line hook |
| [Hermes chat](integrations/hermes-chat/) | Private chat using an existing Hermes profile | Python bridge + authenticated proxy |
| [Domain manager](integrations/domain-manager/) | Caddy routes + Technitium DNS creation/editing | Privileged Python helper + proxy |
| [Service directory](integrations/service-directory/) | Compact links and HTTP health | Python collector |
| [WordPress stats](integrations/wordpress-stats/) | Selected site's stats-only analytics | Python OAuth helper + proxy |
| [Guest Assistant](integrations/guest-assistant/) | Opt-in public text-only Assistant | Patch against pinned Homarr source |
| [Dashboard theme](integrations/dashboard-theme/) | Green → teal → blue appearance CSS | Board custom CSS |

## Setup

Start with the selected package's `INSTALL.md`. JSON cards require Homarr's **custom-widget-v2 / custom JSX** runtime; they are not legacy Homarr 0.x or iframe templates. Source compatibility was checked against Homarr commit `ebbe134c5e9fa3400266fc8c0199ff54e903634b`. Some packages are iframe applications, a source patch or CSS instead of native widgets.

Examples use reserved documentation addresses and `.example.net` domains. Replace the documented placeholders in a private working copy; examples are intentionally not ready to run with real credentials. Configure Homarr bearer credentials separately from widget JSON. Do not commit configured exports. Loopback inside a Docker container refers to that container: a host collector needs an address reachable from Homarr and an allowlist matching the actual connecting peer. HTTPS or a trusted encrypted network is required for remote bearer traffic.

No package installs automatically or updates your live services. Test against your versions and export/back up the current dashboard/config first. See [security and private configuration](SECURITY.md) and [verification](VERIFYING.md).

## Licensing

Original integration code and documentation in this release use the [MIT license](LICENSE). The guest Assistant patch modifies Homarr; its upstream Apache-2.0 license and notices apply as described in [THIRD_PARTY.md](THIRD_PARTY.md). No upstream service, proprietary software, logo, font or personal background is bundled.

## Workshop and standalone releases

See the [screenshot gallery](SCREENSHOTS.md) for real Homarr previews of all nine native widgets and the theme, populated entirely with fictional data. Each candidate includes its own `screenshots/overview.png` for manual Workshop upload.

This publication copy includes ten validated Workshop submission candidates and three source-only packages. Read [Workshop preparation](WORKSHOP.md) for requirements, per-package status and remaining authenticated publication steps. To generate independent repositories from the committed public packages, see [Splitting](SPLITTING.md). No Workshop listings have been published automatically.
