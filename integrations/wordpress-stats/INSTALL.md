# Installation

Requires Linux, Python 3.10+, an existing HTTPS dashboard/Nginx, a WordPress.com-connected site with stats permission, and a Homarr build supporting custom-widget-v2. Register an application at `https://developer.wordpress.com/apps/new/`; website is your HTTPS dashboard, redirect URL exactly `https://YOUR_DASHBOARD/wordpress/oauth/callback`. The app registration itself does not authorize site access.

```sh
sudo install -d -m 755 /opt/homarr/wordpress-stats
sudo cp *.py /opt/homarr/wordpress-stats/
sudo install -d -m 700 /etc/homarr-wordpress /var/lib/homarr-wordpress
sudo install -m 600 config.example.json /etc/homarr-wordpress/config.json
sudo install -m 600 oauth.example.json /etc/homarr-wordpress/oauth.json
python3 -c 'import secrets; print(secrets.token_urlsafe(32)); print(secrets.token_urlsafe(32))'
sudoedit /etc/homarr-wordpress/config.json
sudoedit /etc/homarr-wordpress/oauth.json
```

Insert your app client ID/secret in `oauth.json` only. In config set `site_id` to your WordPress.com numeric blog ID (available from your account's site details or the WordPress API site lookup), `site_label` to a display domain, and `public_base_url` to the HTTPS dashboard origin **without trailing slash or path**. Set distinct random `proxy_token` and `read_token`. Set socket GID to your Nginx worker group; bind mount the socket directory into a containerized proxy at the same path. Never commit these files.

```sh
python3 -m unittest discover -s . -p 'test_*.py'
sudo install -m 644 service.example.systemd /etc/systemd/system/homarr-wordpress.service
sudo systemctl daemon-reload
sudo systemctl enable --now homarr-wordpress
```

Insert the example Nginx location into your dashboard HTTPS server; replace its proxy token with the same `proxy_token` as config. Grant that proxy group traversal of `/run/homarr-wordpress` using a systemd `ExecStartPost=/bin/chgrp YOUR_PROXY_GROUP /run/homarr-wordpress` drop-in if necessary. Run `nginx -t`, reload Nginx. Keep access logging off for this location so OAuth codes/setup links stay private. Preserve Host, Origin and forward-proto headers.

Get your **private, one-time** setup key, then open its link in your browser:

```sh
sudo python3 -c "import json; print(json.load(open('/var/lib/homarr-wordpress/setup.json'))['key'])"
# Open https://YOUR_DASHBOARD/wordpress/connect?key=YOUR_SETUP_KEY
```

Continue to WordPress and approve only stats for your chosen site; cancel broader permissions. Successful callback verifies the token's actual scope/site and permanently consumes the setup link. To reconnect after expiry/revocation: stop service, privately back up state, remove `setup.json` only, start service and obtain the new key; leave token/backups private. Do not share setup URLs.

Edit `widget.json` source base URL to your dashboard HTTPS origin and displayed/link domain to your own site. Import it through Homarr's custom-widget authoring preview, bind source `default` bearer authentication privately to `read_token`, run the `stats` preview query, then save. Homarr's query must send the bearer **server-side**; never put it in the template or JSON. Confirm the feed returns 401 without it. Public dashboard viewers can see the selected analytics; choose board visibility accordingly.

To uninstall remove the widget, disable `homarr-wordpress`, remove proxy location and reload Nginx, revoke the WordPress app under Connected applications, then securely archive/delete `/var/lib/homarr-wordpress` and `/etc/homarr-wordpress`. No posts or site settings are changed.
