# Homarr Workshop publication

Checked 2026-10-16 against the live [Workshop guide](https://homarr.dev/docs/workshop/) and official [submission schema](https://github.com/homarr-labs/homarr/blob/main/packages/workshop/src/schema.ts) / [collection constraints](https://github.com/homarr-labs/homarr/blob/main/apps/workshop/pb_migrations/1784240000_workshop_widgets.js).

## What can be listed

The Workshop accepts **Custom Widget v2 JSON** and **dashboard CSS**. It stores shareable content; each user's service URLs and credentials stay local. GitHub sign-in is needed to publish/manage listings. You do not need a separate Git repository for each listing. Workshop does not install Python helpers, reverse proxies, Docker services or source patches.

This release prepares nine native widgets and one CSS theme. Eight widgets require a separately installed collector/helper; Gitea uses its API directly. Hermes chat, domain manager and guest Assistant remain source-only packages because they are iframe applications or a core patch. They cannot currently be submitted as those supported types.

See `workshop-manifest.json` for eligibility and each folder's `WORKSHOP.md` and `workshop-submission.json` for ready-to-copy fields. No listing is published yet. Collector-based listings must retain their explicit helper prerequisite and installation link; importing widget JSON alone does not install the integration.

Privacy review removed private source-hosting URLs from the prepared descriptions. Before submitting, add a publicly approved source/setup URL for the corresponding release. The exporter uses a fictional example origin until that decision is made. See [manual privacy review](docs/PRIVACY-REVIEW.md); publish from the fresh sanitized snapshot rather than the earlier Git history or exports.

## Current submission requirements

- Type: `customWidget` (`homarr-custom-widget-v2`) or `customCss` (`homarr-custom-css-v1`). Widget JSON must pass Homarr's import schema and safe JSX validation.
- Title: 3–100 characters. Description and changelog: up to 2,000 characters each.
- Widget content: at most 1,000,000 characters. CSS: nonempty and at most 16,384 characters. Widget definitions also have their own field limits (including 128-character name and 512-character description).
- Screenshots: optional, up to five; PNG/JPEG/WebP, at most 5 MiB each. Use synthetic/demo data. This release includes no production screenshots.
- No secret values, real device inventory, personal analytics or deployment-specific local URLs. Source credentials are configured privately after import. Review declared network scopes and request permissions.

Limits above are from current official source; the hosted form is authoritative if it changes. Backend-dependent widgets are technically supported definitions, but inclusion and continued availability are subject to Workshop moderation. No approval or installation guarantee is implied.

## Publish

1. Test the selected integration on a clean test Homarr instance using its INSTALL.md. Verify all preview queries before saving. Collect optional screenshots using demo data only.
2. Sign into https://homarr.dev/workshop/ with GitHub and use Publish. Alternatively publish a saved custom widget from its menu under Management → Custom Widgets.
3. Copy title/description/changelog from `workshop-submission.json`. Select the correct type; paste/import the referenced `widget.json` or `theme.css`, not the metadata file. Retain the helper prerequisite and source/setup link.
4. Inspect every field, publish, then record the resulting URL/revision in the package's WORKSHOP.md and root manifest. Manage revisions through Yours; do not create duplicate listings for updates.

Publication is a separate authenticated action from pushing Git. A successful Git push does not create a Workshop listing. Run `HOMARR_SOURCE=/path/to/homarr bun tools/validate-workshop.ts` before submitting.

## Separate repositories

You may keep one source repository and ten Workshop listings. If independent repositories are preferred, `tools/export_repos.py` creates one standalone local repository per integration. Read [SPLITTING.md](SPLITTING.md). Each contains its own source/docs, license/security files and Workshop metadata where supported. It does not create remote repositories or publish listings.
