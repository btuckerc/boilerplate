# Hearth

Tucker's starting point on nous for ideas, new projects and stack questions.

- New project: `new-project <name>` creates `src/<name>` with a bare
  `git/<name>.git` remote named `nous`. Create repos nowhere else.
- An idea or question with no project yet: a short note in
  `inbox/YYYY-MM-DD-slug.md`.
- Give a project an `AGENTS.md` only for practices an agent cannot infer from
  the code (commands, non-standard conventions), in a few lines. No overviews.
- Repos under `src/` are canonical; the MacBook `~/src` copies are frozen
  backups.
- Shared config (Claude Code, OMP, skills, dotfiles) lives in `boilerplate/home`. Edit it in
  a worktree (`git -C ~/src/boilerplate worktree add ~/src/boilerplate-wt/<task>`),
  never in `src/boilerplate` itself (only live-state capture and
  `omp-baseline upgrade` write there): uncommitted edits there hold back every
  apply on nous. Preview with `chezmoi -S <worktree> diff`, commit, land with
  `merge --ff-only` in `src/boilerplate`, then
  run `decent-angl-sync reconcile` on nous: it publishes to GitHub, applies,
  installs pins and validates. Other hosts converge within 15 minutes on their
  own; done means `decent-angl-sync status` is clean on nous and over
  `ssh mac`. Mini and T14 are optional. Mac GUI work: the `mac` MCP
  (Peekaboo).
- `sudo -n` works for anything on nous (passwordless); don't hand root steps to
  Tucker.
- Agents: Claude Code (`claude`, Opus high) directs; `agent-run` dispatches
  Codex Sol workers, consults, release audits and local Qwen runs.
  Zero-cloud work starts in `omp-local`.
- Infra questions: the `platform-ops` skill's nous reference. OMP config:
  `omp-config`. Cloudflare: the `cloudflare` skill (`cf` CLI). New models:
  the `model-eval` skill.
