# Domain manager: Caddy + Technitium

A compact iframe application that lists current Caddy hostnames and upstreams, then unlocks editing with a short password for five minutes. Choose an authorized Technitium forward zone to create a DNS A record and reverse proxy together. Advanced editing accepts one complete **Caddyfile site block** with its original hostnames, including headers and transport options.

This is a privileged administration service. Root access and Docker access are required by the supplied adapter. Caddy is validated and gracefully reloaded; containers do not restart. DNS ownership checks, file/runtime synchronization, revision checks, private backups, locking, journal recovery and rollback protect unrelated entries. Existing raw site blocks are available only after unlocking. Caddyfile imports and unusual dynamic configurations can need manual administration.

See [INSTALL.md](INSTALL.md). No native widget JSON is required: add an iframe at `/domain-manager/`. Never place the Technitium token, proxy token or edit password in the iframe URL or board JSON. This folder is independently deployable.
