import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

type ContinuityMode = "continue" | "notify" | "off";

const DEFAULT_THRESHOLD_PERCENT = 78;
const AUTO_MESSAGE =
	"Continue from the compaction summary and finish the latest user request. If the latest request is already complete, give a concise status and stop. Otherwise keep going, inspect only the files needed for the next step, and avoid broad re-reading.";
const COMPACT_INSTRUCTIONS =
	"Preserve the current goal, explicit user preferences, decisions made, exact files read or modified, current git/worktree state if known, unfinished work, validation already run, and the next concrete steps. Drop bulky tool output unless it is essential.";
const AUTOCONTINUE_COOLDOWN_MS = 60_000;
const MANUAL_COMPACT_WINDOW_MS = 30_000;

let mode: ContinuityMode = readMode();
let thresholdPercent = readThreshold();
let lastUserPrompt = "";
let manualCompactRequestedAt = 0;
let manualCompactPending = false;
let autoContinuesForPrompt = 0;
let lastAutoContinueAt = 0;
let proactiveCompactionInFlight = false;
const seenCompactions = new Set<string>();

function readMode(): ContinuityMode {
	const raw = (process.env.PI_COMPACT_CONTINUITY ?? "continue").toLowerCase();
	return raw === "off" || raw === "notify" || raw === "continue" ? raw : "continue";
}

function readThreshold(): number {
	const parsed = Number(process.env.PI_COMPACT_GUARD_PERCENT ?? DEFAULT_THRESHOLD_PERCENT);
	if (!Number.isFinite(parsed)) return DEFAULT_THRESHOLD_PERCENT;
	return Math.max(40, Math.min(95, parsed));
}

function usagePercent(ctx: ExtensionContext): number | null {
	const percent = ctx.getContextUsage?.()?.percent;
	return typeof percent === "number" && Number.isFinite(percent) ? percent : null;
}

function isManualCompactRecent(): boolean {
	return manualCompactPending || Date.now() - manualCompactRequestedAt < MANUAL_COMPACT_WINDOW_MS;
}

function sendContinuation(pi: ExtensionAPI, ctx: ExtensionContext) {
	if (mode !== "continue") return;
	if (isManualCompactRecent()) return;
	if (autoContinuesForPrompt >= 1) {
		if (ctx.hasUI) ctx.ui.notify("Compaction finished; auto-continue skipped to avoid a loop.", "warning");
		return;
	}
	if (Date.now() - lastAutoContinueAt < AUTOCONTINUE_COOLDOWN_MS) return;

	autoContinuesForPrompt++;
	lastAutoContinueAt = Date.now();
	if (ctx.isIdle()) {
		pi.sendUserMessage(AUTO_MESSAGE);
	} else {
		pi.sendUserMessage(AUTO_MESSAGE, { deliverAs: "followUp" });
	}
}

function triggerProactiveCompaction(pi: ExtensionAPI, ctx: ExtensionContext, percent: number) {
	if (proactiveCompactionInFlight || isManualCompactRecent()) return;

	proactiveCompactionInFlight = true;
	if (ctx.hasUI) ctx.ui.notify(`Context ${Math.round(percent)}%; compacting before it hits the wall.`, "info");
	ctx.compact({
		customInstructions: COMPACT_INSTRUCTIONS,
		onComplete: () => {
			proactiveCompactionInFlight = false;
			sendContinuation(pi, ctx);
		},
		onError: (error) => {
			proactiveCompactionInFlight = false;
			if (ctx.hasUI) ctx.ui.notify(`Compaction failed: ${error.message}`, "error");
		},
	});
}

export default function compactContinuity(pi: ExtensionAPI) {
	pi.on("input", async (event) => {
		if (event.source === "extension") return { action: "continue" };

		const text = event.text.trim();
		if (text.startsWith("/compact")) {
			manualCompactRequestedAt = Date.now();
			manualCompactPending = true;
		} else {
			lastUserPrompt = text;
			autoContinuesForPrompt = 0;
		}

		return { action: "continue" };
	});

	pi.on("session_before_compact", async (event) => {
		const reason = (event as any).reason;
		if (!proactiveCompactionInFlight && (reason === "manual" || (event as any).customInstructions)) {
			manualCompactRequestedAt = Date.now();
			manualCompactPending = true;
		}
	});

	pi.on("turn_end", async (_event, ctx) => {
		if (mode === "off") return;
		const percent = usagePercent(ctx);
		if (percent === null || percent < thresholdPercent) return;
		triggerProactiveCompaction(pi, ctx, percent);
	});

	pi.on("session_compact", async (event, ctx) => {
		const id = (event as any).compactionEntry?.id ?? `${Date.now()}`;
		if (seenCompactions.has(id)) return;
		seenCompactions.add(id);

		const wasManual = isManualCompactRecent();
		manualCompactPending = false;
		if (mode === "off" || wasManual) return;

		const promptHint = lastUserPrompt ? ` Last prompt: ${lastUserPrompt.slice(0, 80)}` : "";
		if (ctx.hasUI) {
			ctx.ui.notify(`Compaction finished.${mode === "continue" ? " Continuing automatically." : ""}${promptHint}`, "info");
		}

		if (!proactiveCompactionInFlight) {
			sendContinuation(pi, ctx);
		}
	});

	pi.registerCommand("compact-guard", {
		description: "Tune compaction continuity: status|continue|notify|off|threshold <40-95>",
		handler: async (args, ctx) => {
			const parts = args.trim().split(/\s+/).filter(Boolean);
			const command = parts[0] ?? "status";

			if (command === "continue" || command === "notify" || command === "off") {
				mode = command;
				if (ctx.hasUI) ctx.ui.notify(`Compact continuity: ${mode}`, "success");
				return;
			}

			if (command === "threshold") {
				const next = Number(parts[1]);
				if (!Number.isFinite(next) || next < 40 || next > 95) {
					if (ctx.hasUI) ctx.ui.notify("Usage: /compact-guard threshold <40-95>", "warning");
					return;
				}
				thresholdPercent = next;
				if (ctx.hasUI) ctx.ui.notify(`Compact guard threshold: ${thresholdPercent}%`, "success");
				return;
			}

			if (ctx.hasUI) ctx.ui.notify(`Compact guard: ${mode}, threshold ${thresholdPercent}%`, "info");
		},
	});
}
