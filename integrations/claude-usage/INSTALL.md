# Install Claude usage

1. On the host where `claude` is already signed in, install Python 3.10+ and confirm the CLI works as that same OS user. Copy this entire folder to a persistent private directory. No administrator or NAS account access is required.
2. Copy `config.env.example` to `config.env`, run `chmod 600 config.env`, and replace `COLLECTOR_TOKEN` with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` output. This is a new metadata-only token, not an account credential. Set `USAGE_CACHE_DIR` to a private cache directory. For network use, set `COLLECTOR_BIND` to the collector's private address and `COLLECTOR_ALLOWED_CLIENTS` to the exact Homarr server/container peer address (comma separated); enforce a host firewall. Defaults are loopback only. Protect transport using HTTPS or a private encrypted network across hosts.
3. Load the file as trusted shell configuration, then run in this folder:

```sh
set -a
. ./config.env
set +a
python3 usage_collector.py
```

The feed remains unavailable until an active Claude Code session invokes the configured status-line hook. `curl -H "Authorization: Bearer $COLLECTOR_TOKEN" http://127.0.0.1:18089/usage/status` tests a loopback configuration. Unauthorized calls must return 401. Do not paste the token into a URL or browser code.

4. In Claude Code `~/.claude/settings.json`, merge (do not overwrite other settings) a `statusLine` command using absolute paths:

```json
{"statusLine":{"type":"command","command":"/absolute/path/to/python3 /absolute/path/to/claude-usage/usage_collector.py hook"}}
```

Set the same `USAGE_CACHE_DIR` for the hook and collector, or retain the default in both. The hook receives Claude Code's JSON via stdin. It keeps only `rate_limits.five_hour` and `rate_limits.seven_day` fields, and outputs a short status line. This replaces an existing statusLine unless you explicitly chain your existing hook. Keep a settings backup. Claude Code must support those fields; older versions or accounts without them remain waiting. Run an active CLI session to populate the first snapshot. No silent polling of Claude account endpoints is used.

5. Run `python3 configure_widget.py --collector-url http://collector.example.net:18089` with your reachable collector origin and actual port. In Homarr's custom-widget authoring UI import `widget.configured.json`, create a server-side bearer secret containing `COLLECTOR_TOKEN`, bind it to source `default`, run the native preview/query validation, then save/add the widget. The token must never be embedded in JSON/template/browser JavaScript. `networkScope` is private; configure Homarr's server-side private-network policy for exactly this origin.
6. Optional macOS persistence: fill every uppercase placeholder in `launch-agent.plist.example`, including absolute Python/folder/env-file paths. Install as `~/Library/LaunchAgents/org.example.homarr.claude-usage.plist`, `chmod 600` it, and `launchctl bootstrap gui/$(id -u) PATH_TO_PLIST`. Shell config is loaded from the private file; never put tokens in the plist. Logs must be private. Check `launchctl print gui/$(id -u)/org.example.homarr.claude-usage`. The logged-in user must match the CLI owner.

## Remove / rollback

Remove the Homarr widget and secret, stop the foreground process or `launchctl bootout gui/$(id -u) PATH_TO_PLIST`, remove the installed plist and integration folder/private config/cache. Restore/remove only the `statusLine` addition in Claude Code settings. Existing CLI account login is untouched.

## Checks

`python3 -m unittest discover -p 'test_*.py'` runs quota allowlisting, invalid/expired-window, stale timestamp and cache permission checks. Runtime configuration must be validated on your own host; local client API availability is not guaranteed by these offline tests.
