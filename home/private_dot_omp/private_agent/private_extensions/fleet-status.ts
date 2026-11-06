// Status-line warning while a fleet guard marker exists: config-drift and
// omp-baseline-drift mean the last guard run failed; config-pending means work
// held or deferred. The guards delete them on success. Details:
// `decent-angl-sync status` and the marker files.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const dir = path.join(process.env.XDG_STATE_HOME || path.join(os.homedir(), ".local", "state"), "decent-angl");
const markers = [
  ["config-drift", "config drift"],
  ["omp-baseline-drift", "omp drift"],
  ["config-pending", "config pending"],
];

const present = (file) => {
  try {
    return fs.statSync(path.join(dir, file)).size > 0;
  } catch {
    return false;
  }
};

export default function (pi) {
  let ui;
  let shown;
  const refresh = (force) => {
    if (!ui) return;
    const found = markers.filter(([file]) => present(file)).map(([, label]) => label);
    const text = found.length ? `fleet: ${found.join(", ")}` : undefined;
    if (!force && text === shown) return;
    shown = text;
    ui.setStatus("fleet", text);
  };
  const show = (_event, ctx) => {
    ui = ctx.ui;
    refresh(true);
  };
  pi.on("session_start", show);
  pi.on("session_switch", show);
  pi.on("agent_end", show);
  // Guards run unattended, so an idle session rechecks once a minute.
  const timer = setInterval(() => refresh(false), 60_000);
  timer.unref?.();
  pi.on("session_shutdown", () => clearInterval(timer));
}
