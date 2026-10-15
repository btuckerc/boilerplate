// Replaces OMP's bundled /review (a custom command beats prompts/*.md) with an exact-candidate release audit
// by the `auditor` agent through omp-audit. Pure: no imports, no I/O at load or run; it only returns a prompt.
// omp-agent-policy pins this file by sha256; re-review on any change.
const PROMPT = `Release audit request (/review). Scope from the user: $SCOPE

Follow the release-audit rule in RULES.md. Do not review it yourself and do not use the bundled reviewer.
1. Fix the exact candidate: a commit or Git tree id (for uncommitted work, \`git write-tree\` with a temporary index), or the sha256 of the exact content set. Audit nothing else.
2. Write a packet outside Git: the contract and acceptance items, the candidate id, the diff, file hashes and the raw output of the checks you ran. Leave out your own reasoning; label any pointers "pointers only, not evidence". Include no secrets.
3. Run \`omp-quota < /dev/null\`; hold if the Codex pool is below 10% or unknown.
4. Run \`omp-audit NAME PACKET CANDIDATE\` (blocking, up to an hour; NAME new each run). It dispatches one \`auditor\` child in a hardened project with the strict verdict schema and checks the serving model, effort and tools.
5. Report \`result.json\`: accepted, problems, verdict and findings. Only accepted PASS clears the boundary. On BLOCK allow one repair and one targeted re-audit of the new candidate; otherwise hold. A PASS grants no commit or publish authority.`;

export default () => ({
	name: "review",
	description: "Exact-candidate release audit by the auditor agent (omp-audit)",
	execute: (_args: string[], _ctx: unknown, rawArgs?: string) => {
		const scope = rawArgs?.trim() || "(none given: ask what to audit)";
		return PROMPT.replace("$SCOPE", () => scope);
	},
});
