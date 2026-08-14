import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { isAbsolute, join, normalize, relative, resolve, sep } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const HOME = homedir();
const LIVE_PI_AGENT = join(HOME, ".pi", "agent");
const BOILERPLATE_PI_AGENT = join(HOME, "src", "boilerplate", "home", "dot_pi", "agent");
const CHEZMOI_PI_AGENT = join(HOME, ".local", "share", "chezmoi", "home", "dot_pi", "agent");

const LOCAL_ONLY_PREFIXES = ["auth.json", "sessions/", "logs/", "git/", "npm/", "image-paste/"];
const SHARED_ROOT_FILES = new Set(["AGENTS.md", "README.md", "settings.json"]);
const SHARED_PREFIXES = ["extensions/", "prompts/"];

function hasPathPrefix(path: string, prefix: string): boolean {
	return path === prefix || path.startsWith(`${prefix}${sep}`);
}

function normalizeToolPath(rawPath: unknown, cwd: string): string | null {
	if (typeof rawPath !== "string") return null;

	let path = rawPath.trim();
	if (!path) return null;
	if (path.startsWith("@")) path = path.slice(1);

	if (path === "~") return HOME;
	if (path.startsWith("~/")) return normalize(join(HOME, path.slice(2)));
	return normalize(isAbsolute(path) ? path : resolve(cwd, path));
}

function livePiRelativePath(path: string): string | null {
	if (!hasPathPrefix(path, LIVE_PI_AGENT)) return null;
	return relative(LIVE_PI_AGENT, path).split(sep).join("/");
}

function isLocalOnlyPath(relPath: string): boolean {
	return LOCAL_ONLY_PREFIXES.some((prefix) => relPath === prefix.replace(/\/$/, "") || relPath.startsWith(prefix));
}

function isManagedSharedPath(relPath: string): boolean {
	return SHARED_ROOT_FILES.has(relPath) || SHARED_PREFIXES.some((prefix) => relPath.startsWith(prefix));
}

function sourcePathFor(relPath: string): string {
	const sourceRelPath = relPath.split("/").join(sep);
	const candidates = [join(BOILERPLATE_PI_AGENT, sourceRelPath), join(CHEZMOI_PI_AGENT, sourceRelPath)];
	return candidates.find((candidate) => existsSync(candidate)) ?? candidates[0];
}

export default function piPathGuard(pi: ExtensionAPI) {
	pi.on("tool_call", async (event, ctx) => {
		if (event.toolName !== "write" && event.toolName !== "edit") return;

		const absPath = normalizeToolPath((event.input as { path?: string }).path, ctx.cwd);
		if (!absPath) return;

		const relPath = livePiRelativePath(absPath);
		if (!relPath) return;

		if (isLocalOnlyPath(relPath)) {
			if (ctx.hasUI) {
				ctx.ui.notify(`Blocked local-only Pi state path: ${relPath}`, "warning");
			}
			return {
				block: true,
				reason: `Path ${absPath} is local-only Pi state. Keep auth, sessions, logs, caches, and pasted images local.`,
			};
		}

		if (isManagedSharedPath(relPath)) {
			const sourcePath = sourcePathFor(relPath);
			if (ctx.hasUI) {
				ctx.ui.notify(`Edit the shared source instead: ${sourcePath}`, "warning");
			}
			return {
				block: true,
				reason: `Edit shared Pi files in ${sourcePath}, then apply with chezmoi instead of writing live state under ${LIVE_PI_AGENT}.`,
			};
		}
	});
}
