# Install UniFi Gateway

## Upstream requirements

Use a dedicated local UniFi View Only account with no console OS management. Set UNIFI_ORIGIN, UNIFI_SITE (default: default), and UNIFI_CREDENTIALS_FILE. The adapter targets UniFi OS /api/auth/login and /proxy/network/api/s/<site>/stat/...; legacy standalone controllers are unsupported. TLS verification stays enabled; install a trusted private CA if required.

## Configure and test

From this folder:

```sh
cp config.env.example collector.env
chmod 600 collector.env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Edit `collector.env`, fill the empty COLLECTOR_TOKEN field with the generated random value, and set the upstream variables. Use simple shell/systemd KEY=value syntax; quote shell metacharacters. Keep account passwords in separate private JSON files. The default bind is loopback.

```sh
set -a
. ./collector.env
set +a
python3 collector.py
```

In a second terminal, load the same private env and test without a token literal in shell history:

```sh
set -a
. ./collector.env
set +a
python3 -c 'import os,urllib.request,json; u="http://127.0.0.1:"+os.environ["COLLECTOR_PORT"]+"/unifi/health"; r=urllib.request.Request(u,headers={"Authorization":"Bearer "+os.environ["COLLECTOR_TOKEN"]}); v=urllib.request.urlopen(r,timeout=30); print(v.status, sorted(json.load(v)))'
```

Known routes: `/unifi/health`, `/unifi/clients`. No arbitrary URL or client-selected upstream is accepted.

To connect from Homarr, set COLLECTOR_BIND to the intended private interface and COLLECTOR_ALLOWED_CLIENTS to the actual TCP source address of the Homarr server. Docker/NAT may change this address; allow exact peers, comma-separated, no CIDR. Retain 127.0.0.1 for local tests if desired. Restrict the firewall to those peers. Restart only this collector after changes.

## Optional systemd

Create an unprivileged `homarr-collector` user, install this entire folder under `/opt/homarr-unifi-gateway`, and store `collector.env` under `/etc/homarr-unifi-gateway`. Set private files readable only by the collector user/root, mode 600. Review `collector.service.example`, then install it as `/etc/systemd/system/homarr-unifi-gateway.service`:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now homarr-unifi-gateway.service
sudo systemctl status homarr-unifi-gateway.service
```

Adjust paths/users for your operating system. No root collector or container control is required.

## Native Homarr preview and save

```sh
python3 configure_widget.py --collector-url http://collector.example.net:18086 --app-url https://app.example.net
```

Replace the example URLs with your actual collector and app origins. Output `widget.configured.json` is ignored by Git and contains no token. Keep networkScope private for LAN/VPN sources; choose HTTPS when using a TLS proxy.

Import this JSON in a compatible native custom-widget editor as a **preview**. Source `default` uses bearer auth: enter COLLECTOR_TOKEN in its **encrypted server-side source credential binding**, never in JSON or browser code. Test every real request through native preview and check returned data/errors. Persist only after these pass: previewCreate, previewQuery for every request, then updateFromPreview for existing definitions or the supported create-from-preview action for new ones. No direct database persistence bypass is supported. Add the saved widget to your board and check desktop/mobile layout.

## Verification, backup and removal

Check authenticated known routes return 200; unauthenticated GET is 401; an unallowed TCP peer is 403; POST is 405; upstream failure is 503 rather than cached success. Do not interrupt real production networking to test failures. Logs intentionally omit secrets and bodies. Keep private backups of env/credentials/keys separately from this public folder. Rotate by updating env and the encrypted Homarr binding, then restarting only this service. Remove the widget, stop/disable its service, and remove only its dedicated keys/files; preserve unrelated daemon and account settings.

## Private UniFi credentials

Write the file named by UNIFI_CREDENTIALS_FILE (collector-owned, mode 600):

```json
{"username":"YOUR_VIEW_ONLY_USERNAME","password":"YOUR_VIEW_ONLY_PASSWORD"}
```

Do not use an administrator cookie or bypass MFA. Gateway counters and historical speed-test metrics vary by controller version.
