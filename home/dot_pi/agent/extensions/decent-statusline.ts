import { spawn } from "node:child_process";
import { basename } from "node:path";
import type { ExtensionAPI, ExtensionContext, Theme } from "@earendil-works/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";

type DisplayMode = "full" | "minimal";

type VcsStatus = {
	head: string;
	modified: number;
	added: number;
	removed: number;
};

type VcsCacheEntry = {
	value: VcsStatus | null;
	ts: number;
};

const WIDGET_KEY = "decent-statusline";
const VCS_CACHE_TTL_MS = 1500;
const VCS_COMMAND_TIMEOUT_MS = 300;
const STATUSLINE_ARGS = "on|off|toggle|full|minimal|refresh";

let enabled = process.env.PI_STATUSLINE !== "off";
let mode: DisplayMode = process.env.PI_STATUSLINE === "minimal" ? "minimal" : "full";
let currentCtx: ExtensionContext | undefined;
let requestRender: (() => void) | undefined;

const vcsCache = new Map<string, VcsCacheEntry>();
const vcsPending = new Set<string>();

function run(command: string, args: string[], timeoutMs = VCS_COMMAND_TIMEOUT_MS): Promise<string | null> {
	return new Promise((resolve) => {
		let stdout = "";
		let resolved = false;
		const proc = spawn(command, args, { stdio: ["ignore", "pipe", "ignore"] });
		const timer = setTimeout(() => {
			proc.kill();
			finish(null);
		}, timeoutMs);

		function finish(value: string | null) {
			if (resolved) return;
			resolved = true;
			clearTimeout(timer);
			resolve(value);
		}

		proc.stdout.on("data", (chunk) => {
			stdout += chunk.toString();
		});
		proc.on("error", () => finish(null));
		proc.on("close", (code) => finish(code === 0 ? stdout.trim() : null));
	});
}

function countPorcelain(porcelain: string): Pick<VcsStatus, "modified" | "added" | "removed"> {
	let modified = 0;
	let added = 0;
	let removed = 0;

	for (const line of porcelain.split("\n")) {
		if (!line) continue;
		const x = line[0];
		const y = line[1];
		if (x === "?" && y === "?") {
			added++;
		} else if (x === "D" || y === "D") {
			removed++;
		} else if (x === "A" || y === "A") {
			added++;
		} else if (x !== " " || y !== " ") {
			modified++;
		}
	}

	return { modified, added, removed };
}

async function fetchVcs(cwd: string): Promise<VcsStatus | null> {
	const branch = await run("git", ["-C", cwd, "branch", "--show-current"]);
	if (branch === null) return null;

	let head = branch;
	if (!head) {
		const sha = await run("git", ["-C", cwd, "rev-parse", "--short", "HEAD"]);
		head = sha ? `${sha} detached` : "detached";
	}

	const porcelain = await run("git", ["-C", cwd, "status", "--porcelain"]);
	const counts = porcelain ? countPorcelain(porcelain) : { modified: 0, added: 0, removed: 0 };
	return { head, ...counts };
}

function invalidateVcs(cwd?: string) {
	if (cwd) {
		vcsCache.delete(cwd);
		return;
	}
	vcsCache.clear();
}

function getVcs(cwd: string): VcsStatus | null {
	const now = Date.now();
	const cached = vcsCache.get(cwd);
	if (cached && now - cached.ts < VCS_CACHE_TTL_MS) return cached.value;

	if (!vcsPending.has(cwd)) {
		vcsPending.add(cwd);
		void fetchVcs(cwd)
			.then((value) => {
				vcsCache.set(cwd, { value, ts: Date.now() });
			})
			.finally(() => {
				vcsPending.delete(cwd);
				requestRender?.();
			});
	}

	return cached?.value ?? null;
}

function shortModel(model: { provider?: string; id?: string; name?: string } | undefined): string {
	if (!model) return "model";

	const provider = (model.provider ?? "").toLowerCase();
	const id = model.id ?? model.name ?? "model";
	const lower = id.toLowerCase();
	const tail = id.split("/").filter(Boolean).at(-1) ?? id;

	if (provider.includes("fireworks") || lower.includes("fireworks")) {
		if (lower.includes("kimi-k2p5")) return "fire/kimi-k2.5";
		return `fire/${tail.replace(/^accounts-/, "")}`;
	}
	if (provider.includes("openai-codex") || lower.includes("gpt-")) {
		if (lower.includes("gpt-5.3-codex-spark")) return "codex/spark";
		if (lower.includes("gpt-5.4-mini")) return "codex/5.4-mini";
		if (lower.includes("gpt-5.4")) return "codex/gpt-5.4";
		return `codex/${tail}`;
	}

	return `${provider ? `${provider}/` : ""}${tail}`;
}

function routeLabel(model: { provider?: string; id?: string } | undefined, thinking: string): string | null {
	const provider = (model?.provider ?? "").toLowerCase();
	const id = (model?.id ?? "").toLowerCase();

	if ((provider.includes("fireworks") || id.includes("kimi-k2p5")) && thinking === "off") return "safe";
	if (id.includes("gpt-5.3-codex-spark")) return "fast";
	if (id.includes("gpt-5.4") && thinking === "medium") return "core";
	if (id.includes("gpt-5.4") && thinking === "high") return "deep";
	if (id.includes("gpt-5.4") && thinking === "xhigh") return "max";
	return null;
}

function thinkingLabel(level: string): string {
	const aliases: Record<string, string> = {
		minimal: "min",
		medium: "med",
		xhigh: "xhi",
	};
	return aliases[level] ?? level;
}

function currentContext(ctx: ExtensionContext): { percent: number | null; hasWindow: boolean } {
	const usage = ctx.getContextUsage?.();
	if (usage) {
		if (typeof usage.percent === "number") {
			return { percent: Math.max(0, Math.min(999, usage.percent)), hasWindow: true };
		}
		if (usage.percent === null) return { percent: null, hasWindow: true };
	}

	const contextWindow = Number((ctx as any).model?.contextWindow ?? 0);
	return contextWindow ? { percent: null, hasWindow: true } : { percent: null, hasWindow: false };
}

function renderContext(theme: Theme, ctx: ExtensionContext): string | null {
	const context = currentContext(ctx);
	if (!context.hasWindow) return null;
	if (context.percent === null) return theme.fg("dim", "ctx ?");
	const rounded = context.percent > 0 && context.percent < 1 ? "<1" : `${Math.round(context.percent)}`;
	const color = context.percent >= 90 ? "error" : context.percent >= 70 ? "warning" : "dim";
	return theme.fg(color, `ctx ${rounded}%`);
}

function renderVcs(theme: Theme, cwd: string): string | null {
	const vcs = getVcs(cwd);
	if (!vcs?.head) return null;

	const dirty = vcs.modified > 0 || vcs.added > 0 || vcs.removed > 0;
	const parts = [mode === "minimal" ? vcs.head : `git ${vcs.head}`];
	if (mode === "minimal" && dirty) parts[0] += "*";
	if (mode === "full") {
		if (vcs.added) parts.push(`+${vcs.added}`);
		if (vcs.modified) parts.push(`~${vcs.modified}`);
		if (vcs.removed) parts.push(`-${vcs.removed}`);
	}

	return theme.fg(dirty ? "warning" : "success", parts.join(" "));
}

function renderLine(pi: ExtensionAPI, theme: Theme, ctx: ExtensionContext, width: number): string {
	const model = (ctx as any).model;
	const thinking = pi.getThinkingLevel();
	const route = routeLabel(model, thinking);
	const modelText = shortModel(model);
	const cwd = ctx.cwd ?? process.cwd();

	const segments = [
		theme.fg("text", route ? `${route} ${modelText}` : modelText),
		mode === "full" || thinking !== "off" ? theme.fg("muted", `think ${thinkingLabel(thinking)}`) : null,
		mode === "full" ? renderContext(theme, ctx) : null,
		theme.fg("accent", basename(cwd) || cwd),
		renderVcs(theme, cwd),
	].filter((segment): segment is string => Boolean(segment));

	const line = ` ${segments.join(theme.fg("dim", " | "))} `;
	return visibleWidth(line) > width ? truncateToWidth(line, width, theme.fg("dim", "...")) : line;
}

function applyWidget(pi: ExtensionAPI, ctx: ExtensionContext) {
	if (!ctx.hasUI) return;
	currentCtx = ctx;

	if (!enabled) {
		(ctx.ui as any).setWidget(WIDGET_KEY, undefined);
		return;
	}

	(ctx.ui as any).setWidget(
		WIDGET_KEY,
		(tui: { requestRender?: () => void }, theme: Theme) => {
			requestRender = () => tui.requestRender?.();
			return {
				invalidate() {},
				render(width: number) {
					if (!currentCtx) return [];
					return [renderLine(pi, theme, currentCtx, width)];
				},
			};
		},
		{ placement: "belowEditor" },
	);
}

function applyFooter(ctx: ExtensionContext) {
	if (!ctx.hasUI) return;

	if (!enabled) {
		ctx.ui.setFooter(undefined);
		return;
	}

	ctx.ui.setFooter((_tui, _theme, footerData) => {
		const unsubscribe = footerData.onBranchChange(() => requestRender?.());

		return {
			dispose: unsubscribe,
			invalidate() {},
			render() {
				return [];
			},
		};
	});
}

function commandStatus(ctx: ExtensionContext) {
	const state = enabled ? mode : "off";
	ctx.ui.notify(`Statusline: ${state}. Usage: /statusline [${STATUSLINE_ARGS}]`, "info");
}

function mightChangeVcs(command: string): boolean {
	return /\b(git)\s+(add|am|apply|branch|checkout|clean|commit|merge|mv|pull|push|rebase|reset|restore|rm|stash|switch|tag)\b/.test(
		command,
	);
}

export default function decentStatusline(pi: ExtensionAPI) {
	pi.on("session_start", async (_event, ctx) => {
		applyFooter(ctx);
		applyWidget(pi, ctx);
	});

	pi.on("model_select", async (_event, ctx) => {
		applyFooter(ctx);
		applyWidget(pi, ctx);
		requestRender?.();
	});

	pi.on("tool_result", async (event, ctx) => {
		if (event.toolName === "write" || event.toolName === "edit") {
			invalidateVcs(ctx.cwd);
		}
		const command = String((event.input as any)?.command ?? "");
		if (event.toolName === "bash" && mightChangeVcs(command)) {
			invalidateVcs(ctx.cwd);
		}
		requestRender?.();
	});

	pi.on("user_bash", async (event, ctx) => {
		if (mightChangeVcs(event.command)) {
			invalidateVcs(ctx.cwd);
			setTimeout(() => requestRender?.(), 150);
		}
	});

	pi.on("session_shutdown", async () => {
		currentCtx = undefined;
		requestRender = undefined;
	});

	pi.registerCommand("statusline", {
		description: `Configure the compact statusline: ${STATUSLINE_ARGS}`,
		handler: async (args, ctx) => {
			const arg = args.trim().toLowerCase();
			currentCtx = ctx;

			if (!arg) {
				commandStatus(ctx);
				return;
			}

			if (arg === "on") enabled = true;
			else if (arg === "off") enabled = false;
			else if (arg === "toggle") enabled = !enabled;
			else if (arg === "full") {
				enabled = true;
				mode = "full";
			} else if (arg === "minimal") {
				enabled = true;
				mode = "minimal";
			} else if (arg === "refresh") {
				invalidateVcs(ctx.cwd);
			} else {
				ctx.ui.notify(`Usage: /statusline [${STATUSLINE_ARGS}]`, "error");
				return;
			}

			applyWidget(pi, ctx);
			applyFooter(ctx);
			requestRender?.();
			commandStatus(ctx);
		},
	});
}
