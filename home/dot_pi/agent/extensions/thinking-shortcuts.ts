import type { ExtensionAPI, ExtensionCommandContext } from "@earendil-works/pi-coding-agent";

type ThinkingLevel = "off" | "minimal" | "low" | "medium" | "high" | "xhigh";

const levels: ThinkingLevel[] = ["off", "minimal", "low", "medium", "high", "xhigh"];
const aliases: Record<string, ThinkingLevel> = {
	"0": "off",
	"none": "off",
	"off": "off",
	"min": "minimal",
	"minimal": "minimal",
	"lo": "low",
	"low": "low",
	"med": "medium",
	"mid": "medium",
	"medium": "medium",
	"hi": "high",
	"high": "high",
	"max": "xhigh",
	"x": "xhigh",
	"xhigh": "xhigh",
};

function normalize(input: string): ThinkingLevel | undefined {
	return aliases[input.trim().toLowerCase()];
}

function notifyCurrent(pi: ExtensionAPI, ctx: ExtensionCommandContext) {
	ctx.ui.notify(`Thinking: ${pi.getThinkingLevel()}. Options: ${levels.join(", ")}`, "info");
}

function setThinking(pi: ExtensionAPI, ctx: ExtensionCommandContext, level: ThinkingLevel) {
	pi.setThinkingLevel(level);
	ctx.ui.notify(`Thinking set to ${level}`, "info");
}

export default function thinkingShortcuts(pi: ExtensionAPI) {
	const completions = (prefix: string) =>
		levels
			.filter((level) => level.startsWith(prefix.trim().toLowerCase()))
			.map((level) => ({ value: level, label: level }));

	const handler = async (args: string, ctx: ExtensionCommandContext) => {
		if (!args.trim()) {
			notifyCurrent(pi, ctx);
			return;
		}

		const level = normalize(args);
		if (!level) {
			ctx.ui.notify(`Unknown thinking level "${args.trim()}". Use: ${levels.join(", ")}`, "error");
			return;
		}

		setThinking(pi, ctx, level);
	};

	for (const name of ["thinking", "think"]) {
		pi.registerCommand(name, {
			description: "Show or set thinking level",
			getArgumentCompletions: completions,
			handler,
		});
	}

	const fixedCommands: Record<string, ThinkingLevel> = {
		toff: "off",
		tmin: "minimal",
		tlow: "low",
		tmed: "medium",
		thigh: "high",
		txhigh: "xhigh",
	};

	for (const [name, level] of Object.entries(fixedCommands)) {
		pi.registerCommand(name, {
			description: `Set thinking ${level}`,
			handler: async (_args, ctx) => setThinking(pi, ctx, level),
		});
	}
}
