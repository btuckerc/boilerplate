import type { ExtensionAPI, ExtensionCommandContext, SessionEntry } from "@earendil-works/pi-coding-agent";

function defaultLabel(): string {
	return `checkpoint-${new Date().toISOString().replace(/[:.]/g, "-")}`;
}

function findBookmarkTarget(entries: SessionEntry[]) {
	for (let i = entries.length - 1; i >= 0; i--) {
		const entry = entries[i];
		if (entry.type === "message" && entry.message.role === "assistant") {
			return entry;
		}
	}
	return undefined;
}

export default function sessionBookmarks(pi: ExtensionAPI) {
	const bookmark = async (args: string, ctx: ExtensionCommandContext) => {
		const entry = findBookmarkTarget(ctx.sessionManager.getEntries());
		if (!entry) {
			if (ctx.hasUI) ctx.ui.notify("No assistant message to bookmark yet", "warning");
			return;
		}

		const label = args.trim() || defaultLabel();
		pi.setLabel(entry.id, label);
		if (ctx.hasUI) ctx.ui.notify(`Bookmarked: ${label}`, "info");
	};

	pi.registerCommand("bookmark", {
		description: "Label the latest assistant message for /tree navigation",
		handler: bookmark,
	});

	pi.registerCommand("checkpoint", {
		description: "Alias for /bookmark",
		handler: bookmark,
	});

	pi.registerCommand("unbookmark", {
		description: "Remove the latest bookmark label",
		handler: async (_args, ctx) => {
			const entries = ctx.sessionManager.getEntries();
			for (let i = entries.length - 1; i >= 0; i--) {
				const entry = entries[i];
				const label = ctx.sessionManager.getLabel(entry.id);
				if (!label) continue;

				pi.setLabel(entry.id, undefined);
				if (ctx.hasUI) ctx.ui.notify(`Removed bookmark: ${label}`, "info");
				return;
			}

			if (ctx.hasUI) ctx.ui.notify("No bookmark found", "warning");
		},
	});
}
