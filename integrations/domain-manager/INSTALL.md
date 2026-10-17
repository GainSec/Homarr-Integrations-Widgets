# Installation

Requires Linux, Python 3.10+, Docker CLI, an existing Caddy container with the same Caddyfile as the host, and Technitium API connectivity. The supplied Caddy adapter expects `wget` inside the container and the local admin API enabled at `127.0.0.1:2019`. Test this before installation. Back up your Caddyfile and Technitium server. Do not install without first reviewing the privileged adapter.

```sh
sudo install -d -m 755 /opt/homarr/domain-manager
sudo cp *.py *.html *.js *.css /opt/homarr/domain-manager/
sudo install -d -m 700 /etc/homarr-domain-manager /var/lib/homarr-domain-manager
sudo install -m 600 config.example.json /etc/homarr-domain-manager/config.json
sudo install -m 600 deployment.env.example /etc/homarr-domain-manager/deployment.env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
sudoedit /etc/homarr-domain-manager/config.json
sudoedit /etc/homarr-domain-manager/deployment.env
sudo python3 /opt/homarr/domain-manager/setup_password.py /etc/homarr-domain-manager/config.json
```

Insert the generated proxy token in `proxy_token` and the Nginx example header. Insert a dedicated Technitium API token in `dns_token`; allow Zones → View and View/Modify/Delete only on desired primary forward zones. Set `dns_url`, `proxy_address` (A-record target), Caddy container name and **host** Caddyfile path. Set exact dashboard `allowed_hosts` and HTTPS `allowed_origins`. Set socket GID to the proxy worker's numeric group. `socket_path` is the path visible to the host; bind mount its parent into a containerized Nginx at the same location. Grant that proxy group directory traversal without making socket/world access public.

Set `DOMAIN_MANAGER_PROXY_ADDRESS` to the same A-record address. Set `DOMAIN_MANAGER_TLS_ZONES` to comma-separated zones whose certificates use an existing Caddy snippet, and `DOMAIN_MANAGER_TLS_SNIPPET` to that snippet name. For example, manually add `(homarr_tls) { tls internal }` on separate lines to your Caddyfile before using that mode, or select Internal Caddy CA in the form. Supply your own DNS challenge configuration when using public certificates. Ownership marker/label settings must stay fixed once entries exist.

```sh
python3 -m unittest discover -s . -p 'test_*.py'
sudo install -m 644 service.example.systemd /etc/systemd/system/homarr-domain-manager.service
sudo systemctl daemon-reload
sudo systemctl enable --now homarr-domain-manager
sudo systemctl status homarr-domain-manager --no-pager
```

Insert `nginx.example.conf` into the dashboard's existing HTTPS server, replacing the header token privately. Ensure proxy workers can traverse `/run/homarr-domain-manager` and open its socket; use a systemd drop-in `ExecStartPost=/bin/chgrp YOUR_PROXY_GROUP /run/homarr-domain-manager` if needed. Validate with `nginx -t` and gracefully reload Nginx. Add a Homarr iframe pointing to `https://YOUR_DASHBOARD/domain-manager/`. The root page should show inventory without raw configuration; wrong edit passwords must fail; preview before applying. The UI is a Caddyfile block editor, not a Caddy JSON editor.

## Password, recovery and removal

Change the password using `setup_password.py` against the private config, then `sudo systemctl restart homarr-domain-manager`. Plaintext files alone do not change the password hash. State/backups may contain Caddy secrets: retain mode 700 directories/600 files and exclude them from Git. If `pending.json` exists, editing is locked; inspect its private journal and backups before restarting or restoring anything. Never delete it merely to bypass recovery. Restore Caddy and DNS consistently.

To uninstall, remove the iframe, disable `homarr-domain-manager`, remove its Nginx location and reload Nginx. Preserve `/var/lib/homarr-domain-manager` and the Caddyfile; uninstalling does not remove routes/DNS. Remove managed domains through the UI first if desired. Delete OAuth/API tokens from Technitium separately when no longer used.
