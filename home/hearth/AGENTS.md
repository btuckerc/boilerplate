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
- Shared config (OMP, skills, dotfiles) lives in `boilerplate/home`. A change
  is done only when live on nous and the MacBook: `chezmoi apply`,
  `omp-baseline validate`, commit, `git push nous`, then over `ssh mac` pull
  from `nous`, `decent-angl-sync publish` (only the Mac has GitHub keys) and
  `reconcile`; verify on both. Mini and T14 are optional. Mac GUI work: the
  `mac` MCP (Peekaboo).
- `sudo -n` works for anything on nous (passwordless); don't hand root steps to
  Tucker.
- Infra questions: the `platform-ops` skill's nous reference. OMP config:
  `omp-config`. New models: `/skill:model-eval`.
