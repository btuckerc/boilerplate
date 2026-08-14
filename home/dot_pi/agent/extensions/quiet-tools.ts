import { Buffer } from "node:buffer";
import { homedir } from "node:os";
import type { BashToolDetails, EditToolDetails, ExtensionAPI, ReadToolDetails } from "@earendil-works/pi-coding-agent";
import { createBashTool, createEditTool, createReadTool, createWriteTool } from "@earendil-works/pi-coding-agent";
import { Text } from "@earendil-works/pi-tui";

const COMMAND_ARGS = "compact|expanded|status|toggle";
const MAX_CALL_CHARS = 120;
const EXPANDED_LINES = 40;

let autoCollapse = process.env.PI_TOOL_UI !== "expanded";

const toolCache = new Map<string, ReturnType<typeof createBuiltInTools>>();

function createBuiltInTools(cwd: string) {
	return {
		read: createReadTool(cwd),
		bash: createBashTool(cwd),
		edit: createEditTool(cwd),
		write: createWriteTool(cwd),
	};
}

function getBuiltInTools(cwd: string) {
	let tools = toolCache.get(cwd);
	if (!tools) {
		tools = createBuiltInTools(cwd);
		toolCache.set(cwd, tools);
	}
	return tools;
}

function shortenPath(path: string): string {
	const home = homedir();
	if (path.startsWith(home)) return `~${path.slice(home.length)}`;
	return path;
}

function compact(text: string, maxChars = MAX_CALL_CHARS): string {
	const oneLine = text.replace(/\s+/g, " ").trim();
	if (oneLine.length <= maxChars) return oneLine;
	return `${oneLine.slice(0, maxChars - 3)}...`;
}

function textContent(result: { content?: Array<{ type: string; text?: string }> }): string {
	return (result.content ?? [])
		.filter((content) => content.type === "text" && typeof content.text === "string")
		.map((content) => content.text ?? "")
		.join("\n");
}

function linesOf(text: string): string[] {
	const trimmed = text.replace(/\s+$/g, "");
	if (!trimmed) return [];
	return trimmed.split(/\r?\n/);
}

function firstUsefulLine(text: string): string | null {
	for (const line of linesOf(text)) {
		const trimmed = line.trim();
		if (trimmed) return compact(trimmed, 96);
	}
	return null;
}

function diffStats(diff: string): { additions: number; removals: number } {
	let additions = 0;
	let removals = 0;

	for (const line of diff.split(/\r?\n/)) {
		if (line.startsWith("+") && !line.startsWith("+++")) additions++;
		if (line.startsWith("-") && !line.startsWith("---")) removals++;
	}

	return { additions, removals };
}

function formatDiffLines(diff: string, theme: any, maxLines = EXPANDED_LINES): string {
	const lines = diff.split(/\r?\n/);
	const rendered = lines.slice(0, maxLines).map((line) => {
		if (line.startsWith("+") && !line.startsWith("+++")) return theme.fg("success", line);
		if (line.startsWith("-") && !line.startsWith("---")) return theme.fg("error", line);
		return theme.fg("dim", line);
	});

	if (lines.length > maxLines) {
		rendered.push(theme.fg("muted", `... ${lines.length - maxLines} more diff lines`));
	}

	return rendered.join("\n");
}

function formatOutputLines(output: string, theme: any, maxLines = EXPANDED_LINES): string {
	const lines = linesOf(output);
	const tail = lines.slice(Math.max(0, lines.length - maxLines));
	const rendered = tail.map((line) => theme.fg("dim", line));
	if (lines.length > maxLines) {
		rendered.unshift(theme.fg("muted", `... ${lines.length - maxLines} earlier lines`));
	}
	return rendered.join("\n");
}

function collapseTools(ctx: any) {
	if (!autoCollapse || !ctx.hasUI) return;
	ctx.ui.setToolsExpanded(false);
}

function notifyStatus(ctx: any) {
	const state = autoCollapse ? "compact" : "expanded";
	ctx.ui.notify(`Tool UI: ${state}. Usage: /tool-ui [${COMMAND_ARGS}]`, "info");
}

async function handleToolUiCommand(args: string, ctx: any) {
	const arg = args.trim().toLowerCase();

	if (!arg || arg === "status") {
		notifyStatus(ctx);
		return;
	}

	if (arg === "compact" || arg === "quiet" || arg === "collapse" || arg === "on") {
		autoCollapse = true;
		if (ctx.hasUI) ctx.ui.setToolsExpanded(false);
		notifyStatus(ctx);
		return;
	}

	if (arg === "expanded" || arg === "full" || arg === "off") {
		autoCollapse = false;
		if (ctx.hasUI) ctx.ui.setToolsExpanded(true);
		notifyStatus(ctx);
		return;
	}

	if (arg === "toggle") {
		autoCollapse = !autoCollapse;
		if (ctx.hasUI) ctx.ui.setToolsExpanded(!autoCollapse);
		notifyStatus(ctx);
		return;
	}

	ctx.ui.notify(`Usage: /tool-ui [${COMMAND_ARGS}]`, "error");
}

export default function quietTools(pi: ExtensionAPI) {
	pi.on("session_start", async (_event, ctx) => collapseTools(ctx));
	pi.on("before_agent_start", async (_event, ctx) => collapseTools(ctx));
	pi.on("turn_start", async (_event, ctx) => collapseTools(ctx));

	pi.registerCommand("tool-ui", {
		description: `Configure compact tool rendering: ${COMMAND_ARGS}`,
		handler: handleToolUiCommand,
	});

	pi.registerCommand("tools-ui", {
		description: "Alias for /tool-ui",
		handler: handleToolUiCommand,
	});

	pi.registerTool({
		name: "read",
		label: "read",
		description: getBuiltInTools(process.cwd()).read.description,
		parameters: getBuiltInTools(process.cwd()).read.parameters,
		renderShell: "self",

		async execute(toolCallId, params, signal, onUpdate, ctx) {
			return getBuiltInTools(ctx.cwd).read.execute(toolCallId, params, signal, onUpdate);
		},

		renderCall(args, theme) {
			let text = `${theme.fg("toolTitle", theme.bold("read"))} ${theme.fg("accent", shortenPath(String(args.path ?? "")))}`;
			if (args.offset !== undefined || args.limit !== undefined) {
				const start = args.offset ?? 1;
				const end = args.limit !== undefined ? start + args.limit - 1 : "";
				text += theme.fg("muted", `:${start}${end ? `-${end}` : ""}`);
			}
			return new Text(text, 0, 0);
		},

		renderResult(result, { expanded, isPartial }, theme) {
			if (isPartial) return new Text(theme.fg("warning", "reading..."), 0, 0);

			const content = textContent(result);
			const details = result.details as ReadToolDetails | undefined;

			if (result.content?.some((item) => item.type === "image")) {
				return new Text(theme.fg("success", "image loaded"), 0, 0);
			}

			const lines = linesOf(content);
			let text = theme.fg("success", `${lines.length} lines`);
			if (details?.truncation?.truncated) {
				text += theme.fg("warning", ` (truncated from ${details.truncation.totalLines})`);
			}

			if (expanded && content) {
				text += `\n${formatOutputLines(content, theme)}`;
			}

			return new Text(text, 0, 0);
		},
	});

	pi.registerTool({
		name: "bash",
		label: "bash",
		description: getBuiltInTools(process.cwd()).bash.description,
		parameters: getBuiltInTools(process.cwd()).bash.parameters,
		renderShell: "self",

		async execute(toolCallId, params, signal, onUpdate, ctx) {
			return getBuiltInTools(ctx.cwd).bash.execute(toolCallId, params, signal, onUpdate);
		},

		renderCall(args, theme) {
			let text = `${theme.fg("toolTitle", theme.bold("$"))} ${theme.fg("accent", compact(String(args.command ?? "")))}`;
			if (args.timeout) text += theme.fg("muted", ` (timeout ${args.timeout}s)`);
			return new Text(text, 0, 0);
		},

		renderResult(result, { expanded, isPartial }, theme) {
			if (isPartial) return new Text(theme.fg("warning", "running..."), 0, 0);

			const output = textContent(result);
			const lines = linesOf(output);
			const details = result.details as BashToolDetails | undefined;
			const exitMatch = output.match(/exit code:\s*(\d+)/i);
			const exitCode = Number((details as any)?.exitCode ?? (details as any)?.code ?? exitMatch?.[1] ?? 0);
			const failed = Boolean((result as any).isError) || exitCode !== 0;

			let text = failed ? theme.fg("error", `exit ${exitCode}`) : theme.fg("success", "done");
			text += theme.fg("dim", ` (${lines.length} lines)`);
			if ((details as any)?.truncation?.truncated) text += theme.fg("warning", " truncated");

			const firstLine = firstUsefulLine(output);
			if (failed && firstLine) text += theme.fg("muted", ` ${firstLine}`);
			if (expanded && output) text += `\n${formatOutputLines(output, theme)}`;

			return new Text(text, 0, 0);
		},
	});

	pi.registerTool({
		name: "edit",
		label: "edit",
		description: getBuiltInTools(process.cwd()).edit.description,
		parameters: getBuiltInTools(process.cwd()).edit.parameters,
		renderShell: "self",

		async execute(toolCallId, params, signal, onUpdate, ctx) {
			return getBuiltInTools(ctx.cwd).edit.execute(toolCallId, params, signal, onUpdate);
		},

		renderCall(args, theme) {
			return new Text(
				`${theme.fg("toolTitle", theme.bold("edit"))} ${theme.fg("accent", shortenPath(String(args.path ?? "")))}`,
				0,
				0,
			);
		},

		renderResult(result, { expanded, isPartial }, theme) {
			if (isPartial) return new Text(theme.fg("warning", "editing..."), 0, 0);

			const output = textContent(result);
			if ((result as any).isError || /^error\b/i.test(output.trim())) {
				return new Text(theme.fg("error", firstUsefulLine(output) ?? "edit failed"), 0, 0);
			}

			const details = result.details as EditToolDetails | undefined;
			const diff = details?.diff ?? "";
			if (!diff) return new Text(theme.fg("success", "applied"), 0, 0);

			const stats = diffStats(diff);
			let text = `${theme.fg("success", `+${stats.additions}`)} ${theme.fg("error", `-${stats.removals}`)}`;
			if (expanded) text += `\n${formatDiffLines(diff, theme)}`;

			return new Text(text, 0, 0);
		},
	});

	pi.registerTool({
		name: "write",
		label: "write",
		description: getBuiltInTools(process.cwd()).write.description,
		parameters: getBuiltInTools(process.cwd()).write.parameters,
		renderShell: "self",

		async execute(toolCallId, params, signal, onUpdate, ctx) {
			return getBuiltInTools(ctx.cwd).write.execute(toolCallId, params, signal, onUpdate);
		},

		renderCall(args, theme) {
			const content = String(args.content ?? "");
			const lineCount = content ? content.split(/\r?\n/).length : 0;
			let text = `${theme.fg("toolTitle", theme.bold("write"))} ${theme.fg("accent", shortenPath(String(args.path ?? "")))}`;
			if (lineCount) text += theme.fg("muted", ` (${lineCount} lines)`);
			return new Text(text, 0, 0);
		},

		renderResult(result, { expanded, isPartial }, theme, context) {
			if (isPartial) return new Text(theme.fg("warning", "writing..."), 0, 0);

			const output = textContent(result);
			if ((result as any).isError || /^error\b/i.test(output.trim())) {
				return new Text(theme.fg("error", firstUsefulLine(output) ?? "write failed"), 0, 0);
			}

			const content = String((context.args as any)?.content ?? "");
			let text = theme.fg("success", `written ${Buffer.byteLength(content, "utf8")}B`);
			if (expanded && output) text += `\n${formatOutputLines(output, theme, 12)}`;
			return new Text(text, 0, 0);
		},
	});
}
