# Service directory and HTTP health

Standalone fixed-catalog collector and native compact Homarr directory. Real bounded HTTP GET checks distinguish responding, login-required (401/403) and failed (including 502) responses; redirect limits, timeouts and TLS validation apply. A small searchable directory hides its search field until expanded. Icons use built-in Tabler icons; no personal media uploads are required.

The collector is independent of the domain manager and accepts no arbitrary URL from dashboard callers. Its read-only feed requires both an allowed source IP and bearer token. Catalog URLs must be trusted administrator inputs: redirects are followed, so do not accept user-submitted URL catalogs. See [INSTALL.md](INSTALL.md).
