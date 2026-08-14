import { execFile } from "node:child_process";
import { homedir } from "node:os";
import { basename, join } from "node:path";
import { promisify } from "node:util";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const execFileAsync = promisify(execFile);
const COMMAND_ARGS = "[optional prompt text]";
const HELPER = process.env.PI_IMAGE_PASTE_HELPER ?? join(homedir(), ".local", "bin", "pi-img");

type PasteResult = {
	path: string;
	atPath: string;
	mime: string;
	bytes: number;
};

async function runHelper(ctx: ExtensionContext): Promise<PasteResult> {
	const { stdout } = await execFileAsync(HELPER, ["--json", "--cwd", ctx.cwd], {
		timeout: 10000,
		maxBuffer: 1024 * 1024,
	});
	return JSON.parse(stdout) as PasteResult;
}

function appendToEditor(ctx: ExtensionContext, text: string) {
	const ui = ctx.ui as any;
	if (typeof ui.pasteToEditor === "function") {
		ui.pasteToEditor(text);
		return;
	}
	const current = typeof ui.getEditorText === "function" ? ui.getEditorText() : "";
	ui.setEditorText(`${current}${text}`);
}

async function pasteImage(args: string, ctx: ExtensionContext) {
	if (!ctx.hasUI) return;

	try {
		const result = await runHelper(ctx);
		const prompt = args.trim();
		const insert = prompt ? `${result.atPath} ${prompt} ` : `${result.atPath} `;
		appendToEditor(ctx, insert);
		ctx.ui.notify(`Image ready: ${basename(result.path)} (${Math.round(result.bytes / 1024)} KB)`, "success");
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		ctx.ui.notify(`Image paste failed. Try native Ctrl+V or run pi-img --copy. ${message}`, "error");
	}
}

export default function imagePaste(pi: ExtensionAPI) {
	pi.registerCommand("img", {
		description: `Paste clipboard image into the editor as an @file attachment: ${COMMAND_ARGS}`,
		handler: pasteImage,
	});

	pi.registerCommand("image", {
		description: "Alias for /img",
		handler: pasteImage,
	});

	pi.registerCommand("paste-image", {
		description: "Alias for /img",
		handler: pasteImage,
	});

	pi.registerShortcut("ctrl+alt+v", {
		description: "Paste clipboard image into the editor as an @file attachment",
		handler: async (ctx) => pasteImage("", ctx),
	});
}
