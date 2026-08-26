# T14 publish

Published commit: `671144b` (`master`)

The T14 policy keeps SuperGrok (`xai-oauth/grok-4.6`) as the default and uses
OpenRouter Luna (`openrouter/openai/gpt-5.6-luna`) for the `smol`, `tiny`, and
`task` roles. The live config now has the same default and retains Luna for
those roles. `dev.autoqaConsent` remains `denied`.

The publish includes the owned T14 board/drive changes, the Chromium removal,
the OpenRouter usage collector and tests, and the shell overlay files. The
MacBook-only `home/.chezmoidata/ui.yaml` was not staged.

`omp-baseline validate --strict` reached `CONFIG  model roles parse` and all
other checks. It still exits nonzero because the validator reports the
pre-existing live/source mismatch at `/home/tux/.omp/agent/config.yml` as
`LIVE drift`; that drift is recorded rather than hidden.

Proof:

```sh
omp config get modelRoles --json
python3 -c "p=open('docs/fleet-converge/t14-publish.md').read(); assert 'luna' in p.lower()"
python3 -c "import json,subprocess; d=json.loads(subprocess.check_output(['omp','config','get','modelRoles','--json'])); v=d.get('value',d); assert v['default']=='xai-oauth/grok-4.6' and v['task']=='openrouter/openai/gpt-5.6-luna'"
git show --oneline --stat 671144b
```
