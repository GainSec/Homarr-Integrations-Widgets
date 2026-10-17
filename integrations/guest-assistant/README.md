# Guest Assistant

Opt-in text chat for logged-out visitors on a public Homarr board. This is a patch against the exact Homarr commit in [upstream.json](upstream.json), not a drop-in widget or a prebuilt image. Signed-in users keep upstream Assistant behavior. See [installation](INSTALL.md) and the upstream license.

Requires a configured custom OpenAI-compatible provider. Keys stay server-side. Guest chat cannot use Homarr tools or control services. It is separate from the authenticated, personal [Hermes bridge](../hermes-chat/README.md). Browser-tab history is not saved into Homarr conversation tables.
