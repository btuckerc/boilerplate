#!/usr/bin/env python3
"""_shell_cached_init (home/dot_config/shell/common.sh) never sources code another user could write.

Each case runs under zsh and every bash found; a case prints PASS, FAIL or SKIP.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMON_SH = ROOT / 'home/dot_config/shell/common.sh'

CASES = r'''
set +e
umask 022
T=$CASE_DIR; mkdir -p "$T/bin" "$T/v"
export XDG_CACHE_HOME="$T/cache" HOME="$T"
. "$COMMON_SH"
ok() { printf '%s %s\n' "$2" "$1"; }
mode() { stat -c %a "$1" 2>/dev/null || stat -f %Lp "$1"; }
acl() { # acl PATH allow|deny: grant or deny write to someone else
    if [ "$(uname -s)" = Darwin ]; then chmod +a "everyone $2 add_file,add_subdirectory,delete_child" "$1"
    elif command -v setfacl >/dev/null 2>&1; then
        if [ "$2" = allow ]; then setfacl -m u:nobody:rwx "$1"; else setfacl -m u:nobody:--- "$1"; fi
    else return 1; fi
}
noacl() { chmod -N "$1" 2>/dev/null || setfacl -b "$1"; }
gen() { printf '#!/bin/sh\n%s\n' "$2" >"$T/v/$1"; chmod +x "$T/v/$1"; }
gen good 'echo "echo init-$1"'
gen fail 'echo partial; exit 3'
gen empty 'exit 0'
cp "$T/v/good" "$T/bin/tool"; cp "$T/v/fail" "$T/bin/failtool"; cp "$T/v/empty" "$T/bin/emptytool"
PATH="$T/bin:$PATH"
src() { _shell_init_ok=; . "$_shell_init_file" >/dev/null && [ "$_shell_init_ok" = 1 ]; }
fresh() { rm -rf "$XDG_CACHE_HOME"; _shell_init_root_ok=; }
leftovers() { ls -A "$1" 2>/dev/null | grep -c '^\.tmp'; }
poison() { printf '# shell-init v3 t %s a\n%s\n' "$(cd -P "$T/bin" && pwd -P)/tool" "$1" >"$2"; }
case_name=

_shell_cached_init t tool a && src && [ "$(mode "$_shell_init_file")" = 600 ] && [ "$(mode "$XDG_CACHE_HOME/shell-init")" = 700 ] && ok cold-miss-cached PASS || ok cold-miss-cached FAIL
_shell_cached_init t tool a && src && ok warm-hit PASS || ok warm-hit FAIL
_shell_cached_init t failtool && ok generator-fails FAIL || ok generator-fails "$([ "$(leftovers "$XDG_CACHE_HOME/shell-init")" = 0 ] && echo PASS || echo FAIL)"
_shell_cached_init t emptytool && ok empty-output FAIL || ok empty-output PASS
_shell_cached_init t nosuchtool && ok missing-tool FAIL || ok missing-tool PASS
_shell_cached_init t tool a; f=$_shell_init_file; rm -f "$f"; mkdir "$f"
_shell_cached_init t tool a && ok dir-at-entry FAIL || ok dir-at-entry PASS; rmdir "$f"
echo 'echo OUTSIDE' >"$T/outside"; ln -s "$T/outside" "$f"
_shell_cached_init t tool a && src && [ ! -L "$f" ] && [ "$(cat "$T/outside")" = "echo OUTSIDE" ] && ok symlink-entry-replaced PASS || ok symlink-entry-replaced FAIL

fresh; n=$( umask 000; _shell_cached_init t tool a; find "$XDG_CACHE_HOME/shell-init" \( -perm -g+w -o -perm -o+w -o -perm -o+r \) | grep -c . )
[ "$n" = 0 ] && ok umask-000-private PASS || ok umask-000-private FAIL
_shell_init_root_ok=; chmod 755 "$XDG_CACHE_HOME/shell-init"
_shell_cached_init t tool a && ok root-0755-rejected FAIL || ok root-0755-rejected PASS
chmod 700 "$XDG_CACHE_HOME/shell-init"
_shell_init_root_ok=; mv "$XDG_CACHE_HOME/shell-init" "$T/realroot"; ln -s "$T/realroot" "$XDG_CACHE_HOME/shell-init"
_shell_cached_init t tool a && ok root-symlink-rejected FAIL || ok root-symlink-rejected PASS
rm "$XDG_CACHE_HOME/shell-init"; mv "$T/realroot" "$XDG_CACHE_HOME/shell-init"; _shell_init_root_ok=

gen v1 'echo "echo one"'; gen v2 'echo "echo two"'; touch -t 202001010000 "$T/v/v2"
ln -sfn "$T/v/v1" "$T/bin/linked"; touch -h -t 202001010000 "$T/bin/linked"
if _shell_cached_init t linked; then
    o1=$(. "$_shell_init_file"); ln -sfn "$T/v/v2" "$T/bin/linked"; touch -t 202001010000 "$T/bin"
    _shell_cached_init t linked && o2=$(. "$_shell_init_file")
    [ "$o1" = one ] && [ "$o2" = two ] && ok relink-older-exe-new-key PASS || ok relink-older-exe-new-key FAIL
else
    [ -n "${BASH_VERSION:-}" ] && ok relink-older-exe-new-key PASS || ok relink-older-exe-new-key FAIL
fi

fresh; _shell_cached_init t tool a; f=$_shell_init_file
poison 'echo POISON
_shell_init_ok=1' "$f"; chmod 666 "$f"; touch "$f"
_shell_cached_init t tool a && out=$(. "$_shell_init_file") && [ "$out" = init-a ] && [ "$(mode "$f")" = 600 ] && ok writable-entry-regenerated PASS || ok writable-entry-regenerated FAIL
poison 'echo POISON
_shell_init_ok=1' "$f"; chmod 600 "$f"; ln "$f" "$T/hardlink"; touch "$f"
_shell_cached_init t tool a && out=$(. "$_shell_init_file") && [ "$out" = init-a ] && grep -q POISON "$T/hardlink" && ok hardlinked-entry-regenerated PASS || ok hardlinked-entry-regenerated FAIL
poison 'exit 37' "$f"; chmod 600 "$f"; touch "$f"
_shell_cached_init t tool a && out=$(. "$_shell_init_file"; echo "rc=$?") && [ "$out" = "init-a
rc=0" ] && ok no-sentinel-regenerated PASS || ok no-sentinel-regenerated FAIL

fresh; _shell_cached_init t tool a; f=$_shell_init_file
[ "$(ls -ld "$XDG_CACHE_HOME/shell-init" | cut -c11)" != + ] && ok fresh-root-no-acl PASS || ok fresh-root-no-acl FAIL
_shell_init_root_ok=
if acl "$XDG_CACHE_HOME/shell-init" allow; then
    _shell_cached_init t tool a && ok acl-root-rejected FAIL || ok acl-root-rejected PASS
    noacl "$XDG_CACHE_HOME/shell-init"; _shell_init_root_ok=
    poison 'echo POISON
_shell_init_ok=1' "$f"; chmod 600 "$f"
    if acl "$f" allow; then
        # zsh relies on the ACL-free private root; bash also regenerates the entry.
        _shell_cached_init t tool a && out=$(. "$_shell_init_file") && { [ "$out" = init-a ] || [ -n "${ZSH_VERSION:-}" ]; } && ok acl-entry PASS || ok acl-entry FAIL
    fi
else
    ok acl-root-rejected SKIP
fi
cp "$T/v/good" "$T/bin/t2"; _shell_cached_init t t2 a; e=$_shell_init_file
printf 'bogus\n_shell_init_ok=1\n' >"$e"; cp "$T/v/fail" "$T/bin/t2"
_shell_cached_init t t2 a && ok regen-fail-drops-entry FAIL || { [ -n "$e" ] && [ ! -e "$e" ] && ok regen-fail-drops-entry PASS || ok regen-fail-drops-entry FAIL; }

# Ancestors: nobody else may be able to rename a directory on the path.
fresh; mkdir -m 700 "$T/shared"; chmod 777 "$T/shared"; export XDG_CACHE_HOME="$T/shared/c"
_shell_cached_init t tool a && ok world-writable-ancestor-rejected FAIL || ok world-writable-ancestor-rejected PASS
_shell_init_root_ok=; chmod 770 "$T/shared"
_shell_cached_init t tool a && ok group-writable-ancestor-rejected FAIL || ok group-writable-ancestor-rejected PASS
_shell_init_root_ok=; chmod 1777 "$T/shared"
_shell_cached_init t tool a && src && ok sticky-ancestor-accepted PASS || ok sticky-ancestor-accepted FAIL
_shell_init_root_ok=; chmod 755 "$T/shared"
if acl "$T/shared" allow; then
    _shell_cached_init t tool a && ok acl-allow-ancestor-rejected FAIL || ok acl-allow-ancestor-rejected PASS
    noacl "$T/shared"; _shell_init_root_ok=
    if [ "$(uname -s)" = Darwin ] && acl "$T/shared" deny; then
        _shell_cached_init t tool a && src && ok acl-deny-ancestor-accepted PASS || ok acl-deny-ancestor-accepted FAIL
        noacl "$T/shared"
    fi
else
    ok acl-allow-ancestor-rejected SKIP
fi
_shell_init_root_ok=; mkdir -m 700 "$T/realcache"; ln -s "$T/realcache" "$T/linkcache"; export XDG_CACHE_HOME="$T/linkcache"
_shell_cached_init t tool a && src && case $_shell_init_file in "$(cd -P "$T/realcache" && pwd -P)"/shell-init/*) true ;; *) false ;; esac &&
    ok symlinked-ancestor-uses-real-path PASS || ok symlinked-ancestor-uses-real-path FAIL
# Validated once per shell: the second call must not repeat the ancestor ls.
_shell_cached_init t tool a && [ "$_shell_init_root_ok" = "$T/linkcache/shell-init" ] && ok root-validated-once PASS || ok root-validated-once FAIL
export XDG_CACHE_HOME="$T/cache"

fresh; for i in 1 2 3 4 5 6 7 8 9 10; do ( _shell_cached_init t tool a && src && echo y ) & done >"$T/conc"; wait
[ "$(grep -c y "$T/conc")" = 10 ] && [ "$(leftovers "$XDG_CACHE_HOME/shell-init")" = 0 ] && ok concurrent-cold-starts PASS || ok concurrent-cold-starts FAIL
for v in _sci_bin _sci_root _sci_all _sci_real _sci_line _sci_count; do eval "[ -z \"\${$v+x}\" ]" || ok "no-leak-$v" FAIL; done
ok no-helper-variable-leak PASS
'''


def shells():
    found = []
    for path in ('/bin/zsh', '/usr/bin/zsh', '/bin/bash', '/usr/bin/bash', '/opt/homebrew/bin/bash', '/usr/local/bin/bash'):
        if os.access(path, os.X_OK) and os.path.realpath(path) not in [os.path.realpath(p) for p in found]:
            found.append(path)
    return found


class ShellCachedInitTest(unittest.TestCase):
    def test_cases_under_every_shell(self):
        found = shells()
        self.assertTrue(any('bash' in s for s in found), found)
        for shell in found:
            with self.subTest(shell=shell), tempfile.TemporaryDirectory() as tmp:
                case_dir = Path(tmp).resolve() / 'case'
                args = [shell, '-f'] if 'zsh' in shell else [shell, '--norc', '--noprofile']
                env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'CASE_DIR': str(case_dir),
                       'COMMON_SH': str(COMMON_SH), 'USER': os.environ.get('USER', ''), 'TERM': 'dumb'}
                result = subprocess.run(args + ['-c', CASES], env=env, capture_output=True, text=True, timeout=120)
                if os.environ.get('SHELL_CACHED_INIT_VERBOSE'):
                    print(f'== {shell}\n{result.stdout}', end='', file=sys.stderr)
                lines = result.stdout.splitlines()
                failed = [line for line in lines if not line.startswith(('PASS ', 'SKIP '))]
                self.assertEqual(failed, [], f'{shell}\n{result.stdout}{result.stderr}')
                self.assertGreaterEqual(sum(line.startswith('PASS ') for line in lines), 26, result.stdout)
                shutil.rmtree(case_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
