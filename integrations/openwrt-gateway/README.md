# OpenWrt Gateway

Read-only router health, traffic deltas, CPU/memory, real ping and eight clients per page. Wi-Fi associated, reachable, seen and DHCP-only differ. Cached neighbors and leases are not proof of connectivity; LAN neighbors do not claim physically wired transport.

Self-contained Python 3.10+ standard-library collector: no sibling imports, Docker socket, or additional Python dependencies. [Installation](INSTALL.md).

## Contents

- `collector.py`: fixed read-only route service on default port 18087.
- Adapter module: upstream reading, cache and field allowlist.
- `collector_http.py`: vendored bearer/peer authentication, no-store JSON and response-size bound.
- `widget.json`: credential-free custom-widget-v2 UI; requires a compatible Homarr native custom-widget runtime (ordinary upstream builds may not provide it).
- `configure_widget.py`: changes example origins without embedding credentials.
- `config.env.example`, `collector.service.example`: deployment templates.
- `test_*.py`: offline tests; no account/network access required.

```sh
python3 -m unittest discover -v
python3 -m compileall -q .
```

Collectors poll on request with short caching. Widgets refresh manually or when Homarr re-queries; no scheduler is included. GET of known routes only; unknown paths return 404, write methods 405, failed upstream reads 503.

## Privacy

Keep credentials in private files and Homarr encrypted server-side bindings, never JSON templates, browser code, query strings or Git. The exact TCP peer allowlist and bearer authorization are both required. Forwarded headers do not override peer identity. HTTP carries the bearer unencrypted: use a trusted private network/VPN, or a trusted TLS reverse proxy between hosts. Firewall access to the Homarr server; never publish the collector directly to the Internet. Review dashboard viewer permissions because infrastructure metadata is deliberately displayed.
