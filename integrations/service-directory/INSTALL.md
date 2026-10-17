# Installation

Requires Python 3.10+, Linux/systemd for the example service, and custom-widget-v2 support in Homarr.

```sh
sudo useradd --system --no-create-home --shell /usr/sbin/nologin homarr-services
sudo install -d -m 755 /opt/homarr/service-directory
sudo cp collector.py collector_http.py inventory_health.py /opt/homarr/service-directory/
sudo install -d -m 750 -o root -g homarr-services /etc/homarr-services
sudo install -m 640 -o root -g homarr-services catalog.example.json /etc/homarr-services/catalog.json
sudo install -m 600 collector.env.example /etc/homarr-services/collector.env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
sudoedit /etc/homarr-services/collector.env
sudoedit /etc/homarr-services/catalog.json
python3 -m unittest discover -s . -p 'test_*.py'
sudo install -m 644 service.example.systemd /etc/systemd/system/homarr-services.service
sudo systemctl daemon-reload
sudo systemctl enable --now homarr-services
```

Insert the generated token in `COLLECTOR_TOKEN`. Set bind address to an interface reachable by the **Homarr server**, and `COLLECTOR_ALLOWED_CLIENTS` to its exact source IPs (comma-separated); loopback works only when Homarr reaches the collector from the same network namespace. Restrict the port by firewall to those IPs. Use an HTTPS private proxy across untrusted networks. The collector is intentionally read-only; no router/Docker/root access is needed.

Catalog `url` must exactly equal the displayed widget URL; optional `checkUrl` checks a meaningful health path while preserving the display link. Change both `catalog.json` and widget option `catalog` consistently. Restart collector after catalog changes. Optional frontdoor address/domain settings override DNS only for specified domains while preserving TLS hostname verification; omit to use normal DNS.

Edit `widget.json` source URL to the collector and its option catalog to your own services, keeping `Category|Name|URL|Tabler-icon-name|Description` format. Update the category selector in the template if adding categories beyond Apps. In Homarr import/preview the custom widget, bind source `default` to the collector bearer credential through private authentication settings, execute the `health` preview query and save only on success. No token belongs in JSON/template/browser. Apply `widget.css` as optional scoped board custom CSS for compact styling; append to existing CSS rather than replace it.

Verify `/services/status` rejects missing/wrong bearer tokens and a fresh check produces your expected statuses. Responses older than three polling intervals show stale; polling is every 60s and each URL times out after 4s per request/redirect. Empty/failed reads do not claim services online.

Uninstall by removing the widget/scoped CSS, `sudo systemctl disable --now homarr-services`, deleting the unit and reloading systemd. Archive/delete the private catalog/env as desired. This does not change any monitored application.
