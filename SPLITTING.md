# Export independent repositories

A separate repository per Workshop listing is optional. The publication copy retains the original integration folders and adds an exporter for independent releases.

Commit the desired release first, then run from this repository:

Use the fresh sanitized snapshot for anonymous/public releases. Earlier exported copies and the original history are superseded by the manual privacy review. `SOURCE_URL` in the exporter is a fictional example: set an approved public source origin before preparing real provenance/setup links. Never insert a private deployment or private Git origin.

```sh
python3 tools/export_repos.py --output /absolute/path/outside-this-checkout
# Or select one:
python3 tools/export_repos.py --output /absolute/path/outside-this-checkout --package gitea-repositories
```

The output contains `homarr-PACKAGE` directories, each initialized on `main` with an initial commit, source provenance and no remote. Existing destinations are rejected. Only regular **committed** package files and public license/security/ignore files are used; untracked/private working files and original Git history are not copied. Commit only reviewed public files: this is not a secret scanner.

Each export includes README/INSTALL, its runtime, tests and configuration examples; sibling documentation links become public source links. For guest Assistant retain `LICENSE.upstream`. Backend packages still require the upstream services/runtime described in their README; export does not package those services.

Create an empty remote repository yourself, enter the corresponding exported folder and run:

```sh
git remote add origin https://git.example.net/your-org/homarr-PACKAGE.git
git push -u origin main
```

Replace the example remote. The exporter never creates remote repositories, installs services or pushes. After moving to an individual remote, update its Workshop description's source/setup link to the new publicly reachable URL and keep its existing listing ID for updates. Future exports are fresh snapshots, not history-preserving split branches; maintain the monorepo as source of truth or take over development in each exported repo explicitly.
