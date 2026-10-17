# Install OpenWrt Gateway

## Upstream requirements

Set OPENWRT_HOST and OPENWRT_SSH_DIR. Install the dedicated forced-command key and pinned host-key file as described below. No existing administrator key is copied. Requires existing ubus, jsonfilter, jshn, ip, ping and SSH; Wi-Fi data requires hostapd/iwinfo ubus, leases require luci-rpc. Missing telemetry is reported partial/unknown.

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
python3 -c 'import os,urllib.request,json; u="http://127.0.0.1:"+os.environ["COLLECTOR_PORT"]+"/openwrt/status"; r=urllib.request.Request(u,headers={"Authorization":"Bearer "+os.environ["COLLECTOR_TOKEN"]}); v=urllib.request.urlopen(r,timeout=30); print(v.status, sorted(json.load(v)))'
```

Known routes: `/openwrt/status`. No arbitrary URL or client-selected upstream is accepted.

To connect from Homarr, set COLLECTOR_BIND to the intended private interface and COLLECTOR_ALLOWED_CLIENTS to the actual TCP source address of the Homarr server. Docker/NAT may change this address; allow exact peers, comma-separated, no CIDR. Retain 127.0.0.1 for local tests if desired. Restrict the firewall to those peers. Restart only this collector after changes.

## Optional systemd

Create an unprivileged `homarr-collector` user, install this entire folder under `/opt/homarr-openwrt-gateway`, and store `collector.env` under `/etc/homarr-openwrt-gateway`. Set private files readable only by the collector user/root, mode 600. Review `collector.service.example`, then install it as `/etc/systemd/system/homarr-openwrt-gateway.service`:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now homarr-openwrt-gateway.service
sudo systemctl status homarr-openwrt-gateway.service
```

Adjust paths/users for your operating system. No root collector or container control is required.

## Native Homarr preview and save

```sh
python3 configure_widget.py --collector-url http://collector.example.net:18087 --app-url https://app.example.net
```

Replace the example URLs with your actual collector and app origins. Output `widget.configured.json` is ignored by Git and contains no token. Keep networkScope private for LAN/VPN sources; choose HTTPS when using a TLS proxy.

Import this JSON in a compatible native custom-widget editor as a **preview**. Source `default` uses bearer auth: enter COLLECTOR_TOKEN in its **encrypted server-side source credential binding**, never in JSON or browser code. Test every real request through native preview and check returned data/errors. Persist only after these pass: previewCreate, previewQuery for every request, then updateFromPreview for existing definitions or the supported create-from-preview action for new ones. No direct database persistence bypass is supported. Add the saved widget to your board and check desktop/mobile layout.

## Verification, backup and removal

Check authenticated known routes return 200; unauthenticated GET is 401; an unallowed TCP peer is 403; POST is 405; upstream failure is 503 rather than cached success. Do not interrupt real production networking to test failures. Logs intentionally omit secrets and bodies. Keep private backups of env/credentials/keys separately from this public folder. Rotate by updating env and the encrypted Homarr binding, then restarting only this service. Remove the widget, stop/disable its service, and remove only its dedicated keys/files; preserve unrelated daemon and account settings.

## Dedicated forced-command SSH setup

Generate a new key on the collector host, not an existing admin key:

```sh
ssh-keygen -t ed25519 -f ./openwrt-readonly -N '' -C homarr-readonly
chmod 600 openwrt-readonly
```

Using a separate trusted admin session, review and install `openwrt-snapshot.sh` on the router as `/usr/libexec/homarr-readonly-snapshot`, root-owned mode 700. The fixed `network.interface.lan` command supplies the JSON `lab` field. If your logical LAN has a different name, edit that literal during installation; never accept an interface argument from client input. The fixed ping target is 1.1.1.1, one probe per snapshot, timeout two seconds. To change it, review both the script literal and adapter pingTarget label.

Append the dedicated public key to `/etc/dropbear/authorized_keys` without overwriting existing keys, with these restrictions on ONE line:

```text
command="/usr/libexec/homarr-readonly-snapshot",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty PUBLIC_KEY_TYPE_AND_VALUE homarr-readonly
```

Replace PUBLIC_KEY_TYPE_AND_VALUE with the generated key type and base64 value. The script ignores SSH_ORIGINAL_COMMAND. Test from another session: asking this key for arbitrary commands must still yield only snapshot JSON; forwarding must be denied. Stop if the router SSH implementation cannot enforce these restrictions.

Verify the router host-key fingerprint through your trusted router console/admin connection. Write its matching known-hosts entry to `openwrt-known-hosts`; ssh-keyscan alone is not verification. Install the dedicated private key and pinned known-hosts file under OPENWRT_SSH_DIR, readable by the unprivileged collector. Set OPENWRT_HOST to the exact pinned hostname/address. SSH uses strict host checking, explicit identity and no user SSH config. Test a snapshot before starting the service.

No router config writes, package installs, daemon restarts, network scans or speed tests happen during collection. Rate/CPU counters need two samples; reset/interface-change periods show Sampling. Removal means deleting only the dedicated public-key line and script after stopping this collector, not removing administrator access.
