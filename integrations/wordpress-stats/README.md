# WordPress statistics

A site-scoped WordPress.com OAuth connector plus compact native Homarr views/visitors chart. Requests only `stats` for one numeric site ID and verifies the actual issued grant through token-info before saving it. Uses the canonical `/rest/v1/sites/{id}/stats/visits` endpoint. No post editing or account-wide grant is accepted.

The Unix socket requires an injected private proxy token, and the read endpoint requires a **different** server-side bearer token. OAuth state is single-use, cookie-bound and expires; the setup link is one-time and expires after 24 hours. Returned metadata contains only sanitized analytics. See [INSTALL.md](INSTALL.md). This folder is independently deployable.
