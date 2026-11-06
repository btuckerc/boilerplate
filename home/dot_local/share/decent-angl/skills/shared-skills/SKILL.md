---
name: shared-skills
description: Onboard, update, validate, or distribute shared skills across OMP and Codex, including invocation policy and provenance. Explicit requests only; not for using a skill.
---

# Shared skills

OMP-native directories in
`~/src/boilerplate/home/dot_local/share/decent-angl/skills/` are canonical.
`decent-angl-skills` discovers them and generates harness-specific views.

## Add a skill

`add`, `update` and `audit-source` write and check `~/src/boilerplate` unless
`DECENT_ANGL_REPO_ROOT` names another checkout. Prefix each of them with
`DECENT_ANGL_REPO_ROOT=<worktree>` (a worktree per `decent-angl-config`); never
export it, since `decent-angl-sync` reads it too and refuses a split source.

1. Stage a complete skill directory outside the repo.
2. Run `DECENT_ANGL_REPO_ROOT=<worktree> decent-angl-skills add DIR [UPSTREAM]`.
3. Review the Git diff, then run
   `DECENT_ANGL_REPO_ROOT=<worktree> decent-angl-skills audit-source`.
4. Preview with `chezmoi -S <worktree> diff`, commit, land with
   `git merge --ff-only`, and run `decent-angl-sync reconcile`.

To refresh a vendored skill, stage the reviewed replacement and run
`DECENT_ANGL_REPO_ROOT=<worktree> decent-angl-skills update DIR UPSTREAM`, then
steps 3-4. The command validates before swapping and restores the previous
source if the full audit fails.

For a first-party skill, create one directory containing `SKILL.md` and any
referenced resources, then audit it. Never edit generated views or discovery
links.

Every file under `references/` must appear in `SKILL.md` as
`(references/name.md)`. `decent-angl-skills validate` and `sync` audit the
live dest under `~/.local/share/decent-angl/skills/`. `sync` does not copy
source to dest; that is chezmoi. Reconcile applies the landed dest skill
directory, then runs `decent-angl-skills sync`.
A dest `references/` file without a dest SKILL.md link is
`undisclosed reference` even when source is already linked. That dest drift
is what blocks `--strict`, not an unlinked source file.

## Invocation

Omit `disable-model-invocation` by default. Add
`disable-model-invocation: true` only when a skill must require explicit use.
The sync projects that choice into Codex policy automatically. Canonical
frontmatter supports `name`, `description`, `argument-hint`, and
`disable-model-invocation`.

Vendored skills keep `provenance.tsv` beside the source. The audit pins and
checks upstream skill and license content.
