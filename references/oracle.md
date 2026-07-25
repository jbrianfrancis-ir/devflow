# External consultation contract (/flow-oracle)

Second opinions from an external frontier model, concept-derived from [steipete/oracle](https://github.com/steipete/oracle): pack the question + curated files into one **context bundle**, send it to one or more models, distill the answer into a capped advisory verdict, keep the consult resumable in `.planning/consults/`.

**Advice is advisory, never law.** `.planning/ARCHITECTURE.md` pins and `CONTEXT.md` Locked decisions always win: a recommendation that violates one is flagged `[CONFLICTS: <pin>]` in the verdict and surfaces as a `checkpoint:decision` — never adopted silently, no matter how confident the model sounds.

## Engines — detect in order, degrade gracefully
1. **oracle CLI** — `command -v oracle` succeeds. Send: `oracle -p "<question + constraints>" -f <files...> -m <model>`. Panel: `--models m1,m2,m3 --allow-partial`. Long runs detach — capture the session id, collect later with `oracle status` / `oracle session <id>`. Follow-ups reuse the thread: `--followup <sessionId>` with only the delta.
2. **oracle MCP** — oracle MCP tools present in-session; same semantics via tool calls.
3. **Manual (render-and-copy)** — always works, nothing to install: write the bundle, the user pastes it into the model UI of their choice and saves the reply to `RESPONSE.md` beside it. Never block on missing tooling — this path IS the integration floor.

## Bundle — `.planning/consults/NNN-slug/BUNDLE.md`
One self-contained markdown file:
- **Request header**: the question, one-line project description, and the constraints the answer must respect — quote ARCHITECTURE.md pins (stack, versions, forbidden items) and relevant Locked decisions so the external model answers *within* them.
- **Files**: each fenced with a `### path` header. Curate — only files that change the answer (the seed state file, the code under suspicion, the failing plan), never "the repo". Cap ~100KB total; over cap → trim lowest-value files and list exclusions in the manifest.
- **Never include**: `.env*`, `*.pem`/`*.pfx`/`*.key`/`id_rsa*`, lockfiles, build output, or anything the scan below hits.

## Outbound secret scan (fail-closed)
A consult bundle leaving the machine is an outgoing diff in every way that matters. Before ANY send (all engines — including handing a bundle to the user for manual paste), run the `conventions.md` secret-scan pattern over the whole bundle. Hit → report file + pattern class only (never the value), don't send, `FLOW: GATE`. Only a human clears a hit.

## Send gate
Sending project code to an external provider is outward-facing (autonomy.md): show engine + model(s) + the file manifest (path, bytes) and get explicit confirmation before the first send of each consult. Follow-ups reuse the approval only while the file set is unchanged. Under `/goal`//`/loop` or `--auto`: never auto-send — stop at `GATE`.

## Panel (`--panel`)
Same bundle to 2–3 models (CLI `--models`, or the user pastes into multiple UIs on the manual engine). Distill agreements first, then disagreements. Models disagreeing on a real decision → present the positions as `checkpoint:decision` options with trade-offs; never silently pick the majority.

## Verdict & lineage
- Full responses → `RESPONSE-<model>.md` beside the bundle (never into orchestrator context).
- Consult file Verdict: **≤10 lines** — recommendation, key reasoning, per-model disagreements, `[CONFLICTS: pin]` flags, and what it would concretely change here (hypothesis, plan task, decision).
- `--followup NNN`: new consult with `parent: NNN`; bundle carries prior verdict + delta only, reusing the engine session when one exists.
- Outcome is recorded when the advice is applied (commit/plan/debug ref) or discarded (why) — a consult with no outcome is unfinished.
