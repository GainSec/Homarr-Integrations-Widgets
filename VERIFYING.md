# Verification

Run `python3 tools/verify.py` from the repository root with Python 3.10+ and Node installed. Each package's tests run in a separate process to avoid same-named module collisions. Some Mac collectors additionally require the Python dependencies listed in their own requirements files. No test needs production credentials or live services.

This checks package tests, Python/JavaScript/shell syntax, JSON parsing and documentation presence. It does not prove upstream access, browser rendering, OAuth consent, model streaming, privileged edits or compatibility with future Homarr versions. Follow each package's live verification steps on a test deployment before use.

For native widget schema/JSX validation against a local compatible Homarr checkout with dependencies installed, use Bun and `tools/validate-widgets.ts` with `HOMARR_SOURCE=/absolute/path/to/homarr`. This uses the pinned upstream validator without importing any production configuration. For the guest Assistant patch, run `git apply --check` in a clean checkout at its pinned commit and run its documented policy tests, typecheck and build separately.

Before publication run `gitleaks dir . --redact`, inspect staged files and review for private domains, addresses and inventory that a generic secret scanner cannot detect. Runtime configs, state, generated widget exports and backups must stay outside Git.

Workshop submission validation: `HOMARR_SOURCE=/path/to/homarr bun tools/validate-workshop.ts` checks the ten prepared listings through the official input/content/screenshots schema. Exporter safety tests run in the root suite and cover untracked private files, path traversal, existing destinations and committed symlinks.
