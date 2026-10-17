# Install Codex usage

1. On the host where `codex` is already signed in, install Python 3.10+ and confirm the CLI works as that same OS user. Copy this entire folder to a persistent private directory. No administrator or NAS account access is required.
2. Copy `config.env.example` to `config.env`, run `chmod 600 config.env`, and replace `COLLECTOR_TOKEN` with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` output. This is a new metadata-only token, not an account credential. Set `USAGE_CACHE_DIR` to a private cache directory. For network use, set `COLLECTOR_BIND` to the collector's private address and `COLLECTOR_ALLOWED_CLIENTS` to the exact Homarr server/container peer address (comma separated); enforce a host firewall. Defaults are loopback only. Protect transport using HTTPS or a private encrypted network across hosts.
3. Load the file as trusted shell configuration, then run in this folder:

```sh
set -a
. ./config.env
set +a
python3 usage_collector.py
```

The first Codex poll may take up to 25 seconds. `curl -H "Authorization: Bearer $COLLECTOR_TOKEN" http://127.0.0.1:18088/usage/status` tests a loopback configuration. Unauthorized calls must return 401. Do not paste the token into a URL or browser code.

5. Run `python3 configure_widget.py --collector-url http://collector.example.net:18088` with your reachable collector origin and actual port. In Homarr's custom-widget authoring UI import `widget.configured.json`, create a server-side bearer secret containing `COLLECTOR_TOKEN`, bind it to source `default`, run the native preview/query validation, then save/add the widget. The token must never be embedded in JSON/template/browser JavaScript. `networkScope` is private; configure Homarr's server-side private-network policy for exactly this origin.
6. Optional macOS persistence: fill every uppercase placeholder in `launch-agent.plist.example`, including absolute Python/folder/env-file paths. Install as `~/Library/LaunchAgents/org.example.homarr.codex-usage.plist`, `chmod 600` it, and `launchctl bootstrap gui/$(id -u) PATH_TO_PLIST`. Shell config is loaded from the private file; never put tokens in the plist. Logs must be private. Check `launchctl print gui/$(id -u)/org.example.homarr.codex-usage`. The logged-in user must match the CLI owner.

## Remove / rollback

Remove the Homarr widget and secret, stop the foreground process or `launchctl bootout gui/$(id -u) PATH_TO_PLIST`, remove the installed plist and integration folder/private config/cache.  Existing CLI account login is untouched.

## Checks

`python3 -m unittest discover -p 'test_*.py'` runs quota allowlisting, invalid/expired-window, stale timestamp and cache permission checks. Runtime configuration must be validated on your own host; local client API availability is not guaranteed by these offline tests.
