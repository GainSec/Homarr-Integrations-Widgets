# Gitea repositories

Compact recent repositories card with a collapsed filter and six repositories per page. It calls Gitea directly; no collector service is needed. Sorting uses repository update time, which includes metadata updates and is not limited to commits. Public repositories work anonymously when your server permits public API search.

See [installation](INSTALL.md). Requires Homarr 2 custom JSX widgets and the Gitea repository search API. No repository contents or credentials are bundled.
