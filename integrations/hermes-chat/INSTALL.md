# Install Hermes chat

## Prerequisites

- An existing functional Hermes managed installation and personal profile. Preserve its Discord gateway, configuration, state database, memories and policies.
- Its actual managed Python interpreter, determined from your installed Hermes launcher/service, with `hermes_bootstrap`, python-dotenv and aiohttp available in the installed dependency generation. A generic Python venv alone is insufficient for `service_runner.py`.
- A private authenticated Homarr dashboard and a same-origin server-side reverse proxy (Nginx example included). This is an iframe integration; no native custom-widget secret import is needed.

## Configure

1. Copy this complete directory to a private location on the **same host and OS user as your personal Hermes**. Back up the existing profile/configuration; do not copy its secrets into this repository.
2. Copy `config.env.example` to `config.env`, `chmod 600 config.env`. Set `HERMES_HOME` to the existing default profile and `HERMES_REPO` to its actual installed source. Set the correct absolute `HERMES_MANAGED_PYTHON` path. Generate two **independent** new random values using `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` and insert them in `API_SERVER_KEY` and `HOMARR_CHAT_TOKEN`. These are bridge/API credentials, not provider tokens.
3. Keep the API on loopback; only `HERMES_API_PORT` is configurable. Leave bridge loopback defaults when Nginx is local. For a remote proxy, set `HOMARR_CHAT_HOST` to your private interface, `HOMARR_CHAT_ALLOWED_IPS` to the exact proxy's connection peer, and use a firewall/encrypted private transport. Do not use `*` origins or allow arbitrary peers. Set `HOMARR_CHAT_ORIGINS` to exact browser origins (comma separated; no trailing slash), e.g. `https://dashboard.example.net`. Set a generic instance label if desired.
4. In two terminals, load the config and start each mode using the existing managed interpreter:

```sh
set -a
. ./config.env
set +a
"$HERMES_MANAGED_PYTHON" ./service_runner.py api
# In another terminal with the same loaded environment:
"$HERMES_MANAGED_PYTHON" ./service_runner.py chat
```

If Hermes internal imports fail, stop and check compatibility. Do not restart/reconfigure the Discord gateway. This runner starts only its API adapter and the chat bridge, not a messaging gateway.
5. Insert `nginx-location.conf.example` inside the private dashboard's actual server block. Replace `PRIVATE_COLLECTOR_HOST` and `INSERT_PRIVATE_HOMARR_CHAT_TOKEN` server-side. Never send `API_SERVER_KEY` to Nginx or either token to the browser. Bind the proxy behind the dashboard's access controls. Keep Origin intact. `nginx -t`, then reload your proxy; no full Docker stack restart is required. If Nginx runs in Docker, loopback addresses refer to that container, so use the host's private address and exact allowed peer.
6. Add a Homarr iframe pointing to `/hermes-chat/`. Preserve the trailing slash for relative assets. No username/password is needed in the iframe. Your private dashboard access controls provide the user authorization.
7. Optional macOS persistence: make **two** copies of `launch-agent.plist.example`; replace every `MODE` with `api` or `chat`, respectively, and replace all absolute path placeholders. Install as `~/Library/LaunchAgents/org.example.homarr-hermes.api.plist` and `.chat.plist`, chmod 600, and `launchctl bootstrap gui/$(id -u) PATH_TO_PLIST`. Run as the existing Hermes owner. The private shell config is read on launch; no tokens belong in the plist.

## Verify

Install `requirements.txt` in a disposable test venv and run `python3 -m unittest discover -p 'test_*.py'` plus `node --check chat.js`. These mock tests do not validate your installed Hermes version. Test live `/health` through the private proxy, reject a direct bridge request without its token, verify a different Origin is rejected, and send a harmless chat. Reload and continue it. Copy the Session ID and ask Discord Hermes to find it using `session_search`; this searches shared history without mirroring messages. Do not send test messages to Discord automatically. Verify browser assets/network responses contain no token.

The bridge and browser have bounded message/history sizes; long chats require New chat. The transcript/session UUID is kept in browser localStorage, so it persists on that browser and should be cleared on shared computers. New chat clears the browser's current conversation; it does not delete persisted Hermes history.

## Remove / rollback

Remove the iframe and proxy location, `nginx -t` and reload. Stop only these two processes or `launchctl bootout gui/$(id -u) PATH_TO_PLIST` for these two agents, remove their plists/private configuration, then remove this directory. Preserve your original Discord gateway, model/provider credentials and state database. Never restore an old database over a running Hermes. Revoke the two new tokens when retiring the bridge.
