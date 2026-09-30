// Status-line label for the session directory: only its last path segment.
// The built-in `path` segment shows the full path outside ~ (e.g. every
// /srv/workspaces/repos/... session on nous) and has no basename option.
import path from "node:path";

export default function (pi) {
  const show = (_event, ctx) => {
    ctx.ui.setStatus("cwd", path.basename(ctx.cwd) || ctx.cwd);
  };
  pi.on("session_start", show);
  pi.on("session_switch", show);
}
