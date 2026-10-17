# Installation

1. Copy this folder. Run Python 3.10+:

   ```sh
   python3 configure_widget.py --collector-url https://gitea.example.net --app-url https://gitea.example.net --network-scope public
   ```

   Replace both example URLs with your server origin. Use `--network-scope private` for a private LAN service. The API must be reachable from the Homarr server, not only your browser.
2. In Homarr, import `widget.configured.json` as a custom widget and add it to your board. Requests call `/api/v1/repos/search`, sorted by updated time, descending, up to 50 results. The widget filters these results locally and shows six per page.
3. If private repositories are needed, change the source `auth` to `bearer` and configure a narrowly scoped read-only Gitea token through Homarr's credential settings. Never paste a token into the widget JSON or commit the configured export. The source account determines which repositories can appear; dashboard viewers can see the results.

Verify by opening the board and checking repository links and filter pagination. An unavailable message indicates a source URL, network scope or API permission problem. Remove the placement and custom widget to uninstall; no Gitea data is changed. Reimport the previous widget export to roll back.
