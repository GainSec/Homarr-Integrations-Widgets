# Installation

Back up your Homarr data and existing image first. Use a separate checkout and test instance before replacing production. Requirements are the upstream project's Bun toolchain, its documented build dependencies, and Docker if building its container.

```sh
git clone https://github.com/homarr-labs/homarr.git homarr-guest
cd homarr-guest
git checkout ebbe134c5e9fa3400266fc8c0199ff54e903634b
git apply --check /absolute/path/to/guest-assistant.patch
git apply /absolute/path/to/guest-assistant.patch
bun install --frozen-lockfile
bun test apps/nextjs/src/app/api/assistant/guest/policy.spec.ts
```

Follow this pinned checkout's build/container instructions and run its typecheck before building your image. This repository does not include a built image. Set `HOMARR_GUEST_ASSISTANT=true` in your private deployment environment, configure an enabled custom OpenAI-compatible provider in Management → Assistant, make the intended board public and place an Assistant widget on it. Insert provider URLs/keys through Homarr's management UI, not this repository. Proxy streaming responses without buffering and preserve legitimate client IP information through a trusted proxy.

Test in a logged-out browser: intended public board chat succeeds; private boards, boards without Assistant and disabled guest mode reject it. Check that no admin cookies or tool controls are granted. Test signed-in Assistant separately.

Limits per application process: 20 text messages, 2,000 characters each, 32 KiB request, 1,024 output tokens, 90 seconds, 10 requests/minute per visitor/network identity, 60/minute aggregate and 4 streams. Multiple replicas do not share counters. Guests behind one proxy identity share the network budget. Provider usage is billed to the configured account.

Disable the environment flag, remove the widget or make the board private to stop guest access. Restore the prior image to uninstall. On upstream upgrades, rebase the patch, repeat policy tests/typecheck/build and logged-out authorization checks; patch applicability alone does not prove runtime compatibility.
