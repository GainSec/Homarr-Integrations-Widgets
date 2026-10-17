# Codex usage

Standalone compact Homarr custom widget and a read-only local collector. Uses the already signed-in Codex CLI on its own host. No account login/token is copied to Homarr. Only allowlisted quota percentage, window duration, reset time and capture timestamp leave this host. Not token spending, billing, or a new model session.

Polls `codex app-server` `account/rateLimits/read` every 60 seconds; never requests inference.

Missing/unsupported limits show waiting, not zero. Captures older than five minutes are stale; expired windows disappear until a new reading arrives. The update timestamp remains the actual capture time after failures. Homarr refreshes its server-side feed every 30 seconds.

See [INSTALL.md](INSTALL.md), [config.env.example](config.env.example) and [widget.json](widget.json). Self-contained; no sibling integration imports. Custom widget v2 support is required; ordinary iframe-only Homarr imports are insufficient. `widget.json` contains placeholders and no secret bindings.

Test: `python3 -m unittest discover -p 'test_*.py'`. Client APIs can change; revalidate after CLI upgrades. Never publish generated caches, credential files or configured widget exports with secret bindings.
