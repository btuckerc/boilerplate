#!/usr/bin/env python3
import hashlib
import itertools
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
BUN = subprocess.check_output(["mise", "which", "bun"], text=True).strip()

REPO = pathlib.Path(__file__).resolve().parents[2]
CHECKER = REPO / "home/dot_local/bin/executable_omp-agent-policy"
REVIEWED = REPO / "home/private_dot_omp/private_agent/private_extensions"
AUDITOR = REPO / "home/private_dot_omp/private_agent/private_agents/auditor.md"
REVIEW = REPO / "home/private_dot_omp/private_agent/private_commands/private_review/index.ts"
FULL = ["low", "medium", "high", "xhigh", "max"]
# What `omp models --json` writes to stderr (still exiting 0) when native loading rejects models.yml.
REJECTED = (
    "Warning: models.yml validation failed \u2014 custom providers disabled\n"
    "Schema error: providers.llama.cpp.models.0.thinking.supportsDisplay: must be boolean (was a string)\n"
)
# `omp config list --json` values at the 18.12.6 schema defaults, for the settings the checker compares.
NATIVE_DEFAULTS = {
    "todo.enabled": True, "glob.enabled": True, "grep.enabled": True, "astGrep.enabled": False, "astEdit.enabled": True,
    "find.enabled": "auto", "debug.enabled": True, "launch.enabled": True, "checkpoint.enabled": False, "github.enabled": False,
    "web_search.enabled": True, "security.enabled": False, "ask.enabled": True, "async.enabled": True, "tools.xdev": True,
    "lsp.enabled": True, "task.enableLsp": False, "bash.enabled": True, "ida.enabled": True, "goal.enabled": True,
    "externalThinking": False, "autolearn.enabled": False, "task.maxRecursionDepth": 2, "memory.backend": "off",
    "compaction.experimentalContextManagement": False, "eval.py": True, "eval.js": True,
    "advisor.continueSeverity": "concern", "lsp.requestTimeout": 10, "sharpshooter.minPromptLength": 16, "statusLine.segmentOptions": {},
    "enabledProviders": [], "task.prewalk": False, "task.agentPrewalk": {}, "prewalk.auto": "off", "prewalk.autoTarget": "@smol",
    "retry.enabled": True, "retry.modelFallback": True, "retry.usageAwareFallback": False, "task.structured": False,
    "task.enableEffort": False, "modelRoles": {}, "task.agentModelOverrides": {}, "task.disabledAgents": [], "task.maxEffort": "max",
    "disabledProviders": [], "extensions": [],
}


def _case_sensitive_tmp() -> bool:
    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "CaseProbe").touch()
        return not (pathlib.Path(d) / "caseprobe").exists()


# APFS (the macOS default) folds case, so fixtures that need a case variant beside an existing entry cannot exist there.
CASE_SENSITIVE = _case_sensitive_tmp()


def aliases_existing(base: pathlib.Path, rel: str) -> bool:
    """Whether a component of rel names an existing entry under another case spelling."""
    d = base
    for part in pathlib.PurePosixPath(rel).parts:
        if not d.is_dir():
            return False
        names = os.listdir(d)
        if part not in names and any(n.casefold() == part.casefold() for n in names):
            return True
        d = d / part
    return False


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        manifest = self.root / "home/dot_config/decent-angl/omp-baseline-manifest.tsv"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("# omp-version 18.12.6\n")
        self.agent = self.root / "home/private_dot_omp/private_agent"
        (self.agent / "private_agents").mkdir(parents=True)
        self.config = self.agent / "private_config.yml"
        self.config.write_text(
            "modelRoles:\n"
            "  default: anthropic/claude-opus-5-5:high\n"
            "  plan: openai-codex/gpt-6.1-sol:high\n"
            "  smol: llama.cpp/test:low\n"
            "  tiny: '@smol'\n"
            "  task: openai-codex/gpt-6-luna:medium\n"
            "task:\n  agentModelOverrides: {}\n  structured: true\n  enableEffort: true\n"
            "astGrep:\n  enabled: true\n"
            "tools:\n  xdev: true\n"
            "retry:\n  modelFallback: false\n"
        )
        # What native `omp config list --json` reports for this config; tests that change the config update it.
        self.native = {
            "task.enableEffort": True,
            "modelRoles": {
                "default": "anthropic/claude-opus-5-5:high", "plan": "openai-codex/gpt-6.1-sol:high",
                "smol": "llama.cpp/test:low", "tiny": "@smol", "task": "openai-codex/gpt-6-luna:medium",
            },
            "astGrep.enabled": True, "retry.modelFallback": False, "task.structured": True,
        }
        self.add("architect", "@plan:xhigh", "xhigh", ["read", "grep", "glob", "web_search", "yield"])
        shutil.copy(AUDITOR, self.agent / "private_agents/auditor.md")
        self.add("browser", "@default:medium", "medium", ["eval", "yield"])
        self.add("nous", "llama.cpp/test", "medium", ["read", "grep", "glob", "edit", "write", "yield"])
        self.add("scout", "llama.cpp/test", "low", ["read", "grep", "glob", "web_search", "yield"])
        self.add("sol", "@plan", "high")
        self.add("sonic", "llama.cpp/test", "low", ["read", "grep", "glob", "edit", "write", "yield"])
        self.add("fable", "anthropic/claude-fable-test", "medium")
        (self.agent / "private_commands/private_review").mkdir(parents=True)
        shutil.copy(REVIEW, self.agent / "private_commands/private_review/index.ts")

    def add(self, name, model, thinking, tools=None, description="agent"):
        text = f"---\nname: {name}\ndescription: {description}\nmodel: \"{model}\"\nthinkingLevel: {thinking}\n"
        if tools is not None:
            text += "tools: [" + ", ".join(tools) + "]\n"
        (self.agent / "private_agents" / (name + ".md")).write_text(text + "---\nbody\n")

    MODELS = [
        ("openai-codex", "gpt-6.1-sol", FULL),
        ("openai-codex", "gpt-6-luna", FULL),
        ("anthropic", "claude-opus-5-5", FULL),
        ("anthropic", "claude-fable-test", FULL),
        ("llama.cpp", "test", ["low", "medium", "high"]),
    ]
    serial = itertools.count()

    def run_checker(self, *args):
        env = {**os.environ, "HOME": str(self.root / "home-temp")}
        return subprocess.run([BUN, str(CHECKER), "--root", str(self.root), *args], capture_output=True, text=True, env=env)

    def evidence(self, models=None, models_file=None, profile="default", stderr="", version="18.12.6", native=None):
        """--catalog evidence as omp-baseline writes it: the native listing and settings, its stderr and what it covered."""
        models_file = models_file or self.agent / "private_models.yml"
        out = self.root / f"evidence-{next(self.serial)}.json"
        settings = {**NATIVE_DEFAULTS, **(self.native if native is None else native)}
        out.write_text(json.dumps({
            "models": [{"provider": p, "id": i, "reasoning": True, "thinking": t} for p, i, t in (models or self.MODELS)],
            "settings": {k: {"value": v} for k, v in settings.items()},
            "ompVersion": version,
            "profile": profile,
            "modelsYml": models_file.read_text() if models_file.exists() else None,
            "stderr": stderr,
        }))
        return str(out)

    def test_01_valid_control(self):
        result = self.run_checker("--catalog", self.evidence())
        self.assertEqual(result.returncode, 0, result.stderr)
        # Any models.yml override can narrow a ladder, so a contract level is never a pass without evidence.
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("UNVERIFIED architect thinking xhigh unclamped: openai-codex/gpt-6.1-sol needs native catalog evidence", result.stderr)

    def test_02_plan_suffix_clamps(self):
        self.add("architect", "@plan", "xhigh", ["read", "grep", "glob", "web_search", "yield"])
        result = self.run_checker()
        self.assertIn("EFFORT architect expected xhigh resolved high via selector-suffix", result.stderr)

    def test_03_inherited_browser_effort(self):
        self.add("browser", "@default", "medium", ["eval"])
        result = self.run_checker()
        self.assertIn("EFFORT browser expected medium resolved high", result.stderr)

    def test_04_browser_explicit_medium_passes(self):
        result = self.run_checker("--catalog", self.evidence())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_05_project_shadow(self):
        project = self.root / "project"
        project.mkdir()
        (project / "architect.md").write_text("---\nname: architect\ndescription: project\nmodel: openai-codex/gpt-6.1-sol\nthinkingLevel: xhigh\n---\n")
        result = self.run_checker("--project-agents", str(project))
        self.assertIn("SHADOW architect", result.stderr)

    def test_06_missing_description_malformed_and_missing(self):
        (self.agent / "private_agents/architect.md").write_text("---\nname: architect\nmodel: openai-codex/gpt-6.1-sol\n---\n")
        result = self.run_checker()
        self.assertIn("MALFORMED", result.stderr)
        self.assertIn("MISSING architect", result.stderr)

    def test_07_malformed_scout_falls_back_to_bundled(self):
        (self.agent / "private_agents/scout.md").write_text("bad")
        result = self.run_checker()
        self.assertIn("MISSING scout", result.stderr)

    def test_08_inert_prompt_keys(self):
        prompt_dir = self.agent / "private_prompts"
        prompt_dir.mkdir()
        (prompt_dir / "review.md").write_text("---\nmodel: x\nrestore: true\nargument-hint: x\n---\n")
        result = self.run_checker()
        self.assertIn("INERT", result.stderr)

    def test_09_overlay_precedence(self):
        overlay = self.root / "overlay.yml"
        overlay.write_text("task:\n  agentModelOverrides:\n    architect: '@plan'\n")
        result = self.run_checker("--config", str(overlay))
        self.assertIn("EFFORT architect", result.stderr)

    def test_10_local_profile_malformed_only(self):
        profile = self.root / "home/private_dot_omp/private_profiles/local/private_agent"
        (profile / "private_agents").mkdir(parents=True)
        (profile / "private_config.yml").write_text(
            "modelRoles:\n  default: anthropic/claude-opus-x:high\n  task: anthropic/claude-opus-x:medium\n"
        )
        (profile / "private_agents/cloud.md").write_text('---\nname: cloud\ndescription: cloud\nmodel: "anthropic/claude-opus-x"\nthinkingLevel: medium\n---\n')
        catalog = self.evidence(
            models=self.MODELS + [("anthropic", "claude-opus-x", FULL)], models_file=profile / "private_models.yml", profile="local",
            native={"modelRoles": {"default": "anthropic/claude-opus-x:high", "task": "anthropic/claude-opus-x:medium"}},
        )
        result = self.run_checker("--profile", "local", "--catalog", catalog)
        self.assertEqual(result.returncode, 0, result.stderr)
        # The merge is unconfirmed without native settings evidence.
        self.assertIn("UNVERIFIED settings merge not confirmed", self.run_checker("--profile", "local").stderr)
        (profile / "private_agents/bad.md").write_text("bad")
        result = self.run_checker("--profile", "local")
        self.assertIn("MALFORMED", result.stderr)

    def test_11_runtime_grants_and_restricted(self):
        self.add("architect", "openai-codex/gpt-6.1-sol", "xhigh", ["read", "grep"])
        result = self.run_checker("--json")
        report = json.loads(result.stdout)
        architect = next(agent for agent in report["agents"] if agent["name"] == "architect")
        self.assertIn("write(xd-devices-only)", architect["callable"])
        self.assertNotIn("write", architect["callable"])
        self.assertNotIn("ast_grep", architect["callable"])  # registered auto-include, inactive under an explicit list
        restricted = self.run_checker("--dispatch", "restricted", "--json")
        architect = next(agent for agent in json.loads(restricted.stdout)["agents"] if agent["name"] == "architect")
        self.assertEqual(architect["callable"], ["read", "grep", "yield"])
        # task.structured off: the child gets no yield, even a declared one (task/executor.ts:4041-4045).
        self.add("architect", "openai-codex/gpt-6.1-sol", "xhigh", ["read", "grep", "yield"])
        self.config.write_text(self.config.read_text().replace("  structured: true\n", ""))
        for args in ((), ("--dispatch", "restricted")):
            architect = self.agent_report(self.run_checker("--json", *args), "architect")
            self.assertNotIn("yield", architect["callable"])
            self.assertIn("read", architect["callable"])

    def test_12_unknown_version(self):
        (self.root / "home/dot_config/decent-angl/omp-baseline-manifest.tsv").write_text("# omp-version 19.0\n")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("VERSION", result.stderr)

    def test_13_effort_catalog(self):
        catalog = self.evidence(models=[
            ("openai-codex", "gpt-6.1-sol", ["low", "medium", "high"]),
            ("openai-codex", "gpt-6-luna", ["low", "medium", "high"]),
            ("anthropic", "claude-opus-5-5", ["low", "medium", "high"]),
            ("llama.cpp", "test", ["low", "medium"]),
            ("anthropic", "claude-fable-test", ["low", "medium"]),
        ])
        result = self.run_checker("--catalog", catalog, "--effort", "med")
        self.assertIn("via caller-effort", result.stderr)
        overlay = self.root / "ceiling.yml"
        overlay.write_text("task:\n  maxEffort: minimal\n")
        result = self.run_checker("--catalog", catalog, "--effort", "med", "--config", str(overlay))
        self.assertEqual(result.returncode, 1)
        self.assertIn("task.maxEffort=minimal", result.stderr)
        # 18.12.6 ignores stale caller effort when its runtime gate is disabled.
        overlay.write_text("task:\n  enableEffort: false\n")
        result = self.run_checker("--catalog", catalog, "--effort", "med", "--config", str(overlay))
        self.assertNotIn("via caller-effort", result.stderr)
        self.assertIn("via selector-suffix", result.stderr)

    def test_14_invalid_yaml_fails_closed(self):
        (self.agent / "private_agents/architect.md").write_text('---\nname: architect\ndescription: fallback\nmodel: openai-codex/gpt-6.1-sol\nthinking-level: xhigh\ntools: [read, grep\n---\n')
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("UNSUPPORTED frontmatter", result.stderr)

    def test_15_nested_role_expansion(self):
        overlay = self.root / "overlay.yml"
        overlay.write_text("modelRoles:\n  tiny: '@smol'\n  smol: llama.cpp/test:low\ntask:\n  agentModelOverrides:\n    architect: '@tiny'\n")
        result = self.run_checker("--config", str(overlay))
        self.assertIn("MODEL architect", result.stderr)
        self.assertIn("llama.cpp/test", result.stdout)

    def test_16_disabled_provider_filtering(self):
        catalog = self.evidence(models=[("openai-codex", "gpt-6.1-sol", ["low", "medium", "high"])])
        overlay = self.root / "disabled.yml"
        overlay.write_text("disabledProviders: [openai-codex]\n")
        result = self.run_checker("--catalog", catalog, "--config", str(overlay))
        self.assertIn("MODEL architect", result.stderr)

    def test_17_prompt_argument_hint_is_inert(self):
        prompt_dir = self.agent / "private_prompts"
        prompt_dir.mkdir()
        (prompt_dir / "review.md").write_text("---\nargument-hint: file\n---\n")
        result = self.run_checker()
        self.assertIn("INERT", result.stderr)
        self.assertIn("argument-hint", result.stderr)

    def test_17b_source_prompts_and_commands_resolve_chezmoi_names(self):
        """Every source entry that deploys a loaded prompt or Markdown command is checked; one not deployed as stored fails closed."""
        prompts = self.agent / "private_prompts"
        (prompts / "nested").mkdir(parents=True)
        (prompts / "nested/clean.md").write_text("---\ndescription: ok\n---\nbody\n")
        (prompts / ".hidden.md").write_text("---\nmodel: x\n---\n")
        commands = self.agent / "private_commands"
        (commands / "clean.md").write_text("---\ndescription: ok\nargument-hint: file\n---\nbody\n")
        result = self.run_checker("--catalog", self.evidence())
        self.assertEqual(result.returncode, 0, result.stderr)
        cases = {
            prompts / "probe.md.tmpl": "UNSUPPORTED source {}",
            prompts / "symlink_probe.md": "UNSUPPORTED source {}",
            commands / "probe.md.tmpl": "UNSUPPORTED source {}",
            prompts / "nested/probe.md": "INERT {} key model",
            prompts / "readonly_probe.md": "INERT {} key model",
        }
        for file, message in cases.items():
            with self.subTest(file=file.name):
                file.write_text("---\ndescription: probe\nmodel: openai-codex/gpt-6.1-sol\nrestore: true\n---\nReview this change.\n")
                result = self.run_checker("--catalog", self.evidence())
                file.unlink()
                self.assertEqual(result.returncode, 1)
                self.assertIn(message.format(file), result.stderr)
        # The prompts dir itself under another source name, and as a template.
        renamed = self.agent / "readonly_prompts"
        prompts.rename(renamed)
        (renamed / "probe.md").write_text("---\nmodel: x\n---\n")
        result = self.run_checker("--catalog", self.evidence())
        self.assertIn(f"INERT {renamed / 'probe.md'} key model", result.stderr)
        shutil.rmtree(renamed)
        (self.agent / "symlink_prompts").write_text("/elsewhere\n")
        result = self.run_checker("--catalog", self.evidence())
        self.assertIn(f"UNSUPPORTED source {self.agent / 'symlink_prompts'}", result.stderr)

    def test_18_no_catalog_suffix_overrides_frontmatter(self):
        self.add("sol", "openai-codex/gpt-6.1-sol:low", "high")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1)
        self.assertIn("EFFORT sol expected high resolved low via selector-suffix", result.stderr)

    def live_fixture(self):
        """A live default profile at $HOME/.omp/agent mirroring the root fixture; returns (cwd, run)."""
        home = self.root / "home-temp"
        live = home / ".omp/agent"
        (live / "agents").mkdir(parents=True)
        (live / "config.yml").write_text(self.config.read_text())
        for agent in (self.agent / "private_agents").iterdir():
            (live / "agents" / agent.name).write_text(agent.read_text())
        (live / "commands/review").mkdir(parents=True)
        shutil.copy(REVIEW, live / "commands/review/index.ts")
        cwd = self.root / "work"
        (cwd / ".omp").mkdir(parents=True)
        # Hermetic: only the variables a test passes reach the checker's environment screen.
        env = {k: v for k, v in os.environ.items() if not k.startswith(("PI_", "OMP_", "XDG_")) and k != "CLAUDE_CONFIG_DIR"}
        env["HOME"] = str(home)

        def run(live_dir=live, args=(), at=None, **extra):
            catalog = self.evidence(models_file=live_dir / "models.yml")
            return subprocess.run(
                [BUN, str(CHECKER), "--live", str(live_dir), "--omp-version", "omp/18.12.6", "--cwd", str(at or cwd), "--catalog", catalog, *args],
                capture_output=True, text=True, env={**env, **extra},
            )
        return cwd, run

    def test_19_live_project_config_overlay(self):
        cwd, run = self.live_fixture()
        result = run()
        self.assertEqual(result.returncode, 0, result.stderr)
        (cwd / ".omp/config.yml").write_text("task:\n  agentModelOverrides:\n    architect: '@plan'\n")
        result = run()
        self.assertEqual(result.returncode, 1)
        self.assertIn("EFFORT architect expected xhigh resolved high via selector-suffix", result.stderr)
        # Any other live shape would skip the default-profile contracts silently.
        self.assertEqual(run(self.root / "elsewhere/agent").returncode, 2)
        # discovery/builtin.ts getConfigDirs: no project layer when cwd is home, compared by realpath.
        home = self.root / "home-temp"
        (home / ".omp/config.yml").write_text("task:\n  agentModelOverrides:\n    architect: '@plan'\n")
        (self.root / "home-link").symlink_to(home)
        for at in (home, self.root / "home-link"):
            result = run(at=at)
            self.assertEqual(result.returncode, 0, result.stderr)
        project = home / "project"
        (project / ".git").mkdir(parents=True)
        (home / ".omp/agents").mkdir(parents=True)
        (home / ".omp/agents/architect.md").write_text(
            "---\nname: architect\ndescription: project walk loads this user-layout directory\nmodel: anthropic/claude-opus-5-5\nthinkingLevel: low\n---\n")
        project_result = run(at=project)
        self.assertEqual(project_result.returncode, 1)
        self.assertIn("MISSING architect expected user definition; effective project", project_result.stderr)

    def test_20_live_host_overlay_and_plugin_registry(self):
        cwd, run = self.live_fixture()
        host = self.root / "host.yml"
        host.write_text("modelRoles:\n  plan: openai-codex/gpt-6.1-sol:medium\ntask:\n  agentModelOverrides:\n    sol: '@plan'\n")
        result = run(PI_CONFIG_FILES=str(host))
        self.assertIn("EFFORT sol expected high resolved medium via selector-suffix", result.stderr)
        result = run(PI_CONFIG_FILES=str(self.root / "missing.yml"))
        self.assertIn("CONFIG overlay missing", result.stderr)
        registry = cwd / ".omp/plugins/installed_plugins.json"
        registry.parent.mkdir(parents=True)
        registry.write_text('{"version": 2, "plugins": {}}')
        result = run()
        self.assertEqual(result.returncode, 1)
        foreign = self.root / "srv/foreign"
        repo = foreign / "repo"
        (repo / ".git").mkdir(parents=True)
        (foreign / ".omp/agent").mkdir(parents=True)
        (foreign / ".omp/plugins").mkdir(parents=True)
        (self.root / "srv/.omp/plugins").mkdir(parents=True)
        registry = self.root / "srv/.omp/plugins/installed_plugins.json"
        registry.write_text('{"version": 2, "plugins": {}}')
        result = run(at=repo)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"UNSUPPORTED agent root {registry}", result.stderr)
        self.assertIn(f"UNSUPPORTED agent root {registry}", result.stderr)

    @unittest.skipUnless(CASE_SENSITIVE, "needs a case-sensitive filesystem: APFS opens HOME-TEMP as home-temp")
    def test_plugin_registry_case_distinct_home_is_not_a_ceiling(self):
        _, run = self.live_fixture()
        foreign = self.root / "HOME-TEMP"
        repo = foreign / "repo"
        (repo / ".git").mkdir(parents=True)
        plugin = self.root / "case-plugin"
        (plugin / "agents").mkdir(parents=True)
        (plugin / "agents/task.md").write_text("---\nname: task\ndescription: plugin task\ntools: [read]\n---\n")
        registry = foreign / ".omp/plugins/installed_plugins.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(json.dumps({"version": 2, "plugins": {"case@test": [
            {"scope": "project", "installPath": str(plugin), "version": "1.0.0", "enabled": True},
        ]}}))
        result = run(at=repo)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(f"UNSUPPORTED agent root {registry}", result.stderr)

    def test_plugin_registry_agent_file_is_not_a_foreign_user_root(self):
        _, run = self.live_fixture()
        foreign = self.root / "srv/foreign"
        repo = foreign / "repo"
        (repo / ".git").mkdir(parents=True)
        (foreign / ".omp").mkdir()
        (foreign / ".omp/agent").write_text("a file, not a user agent directory\n")
        plugin = self.root / "foreign-plugin"
        (plugin / "agents").mkdir(parents=True)
        (plugin / "agents/task.md").write_text("---\nname: task\ndescription: plugin task\ntools: [read]\n---\n")
        registry = foreign / ".omp/plugins/installed_plugins.json"
        registry.parent.mkdir()
        registry.write_text(json.dumps({"version": 2, "plugins": {"foreign@test": [
            {"scope": "project", "installPath": str(plugin), "version": "1.0.0", "enabled": True},
        ]}}))
        result = run(at=repo)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(f"UNSUPPORTED agent root {registry}", result.stderr)

    def test_plugin_registry_agent_symlink_to_active_agent_dir_is_screened(self):
        # Upstream helpers.ts:1061-1065 compares real paths with getAgentDir(): an .omp/agent that links to the
        # active agent dir is not foreign, so its registry is the one selected and must be screened.
        _, run = self.live_fixture()
        shared = self.root / "srv/shared"
        repo = shared / "repo"
        (repo / ".git").mkdir(parents=True)
        (shared / ".omp").mkdir()
        (shared / ".omp/agent").symlink_to(self.root / "home-temp/.omp/agent", target_is_directory=True)
        plugin = self.root / "shared-plugin"
        (plugin / "agents").mkdir(parents=True)
        (plugin / "agents/task.md").write_text("---\nname: task\ndescription: plugin task\ntools: [read]\n---\n")
        registry = shared / ".omp/plugins/installed_plugins.json"
        registry.parent.mkdir()
        registry.write_text(json.dumps({"version": 2, "plugins": {"shared@test": [
            {"scope": "project", "installPath": str(plugin), "version": "1.0.0", "enabled": True},
        ]}}))
        result = run(at=repo)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(f"UNSUPPORTED agent root {registry}", result.stderr)

    def test_plugin_registry_of_every_profile_is_screened(self):
        # utils/src/dirs.ts:342-434,669-674: a named profile keeps plugins under its own data root,
        # ~/.omp/profiles/<name> or $XDG_DATA_HOME/omp/profiles/<name>, which the checker must not skip.
        _, run = self.live_fixture()
        home = self.root / "home-temp"
        xdg = self.root / "xdg-data"
        registries = [home / ".omp/profiles/local/plugins/installed_plugins.json", xdg / "omp/profiles/work/plugins/installed_plugins.json"]
        for registry in registries:
            registry.parent.mkdir(parents=True)
            registry.write_text('{"version": 2, "plugins": {}}')
        result = run(XDG_DATA_HOME=str(xdg))
        self.assertEqual(result.returncode, 1, result.stderr)
        for registry in registries:
            self.assertIn(f"UNSUPPORTED agent root {registry}", result.stderr)

    @unittest.skipIf(os.name != "posix" or os.geteuid() == 0, "needs a non-root POSIX user for EACCES")
    def test_unlistable_profiles_dir_fails_closed(self):
        # A searchable but unreadable profiles dir would hide every profile's registry.
        _, run = self.live_fixture()
        profiles = self.root / "home-temp/.omp/profiles"
        (profiles / "local/plugins").mkdir(parents=True)
        (profiles / "local/plugins/installed_plugins.json").write_text('{"version": 2, "plugins": {}}')
        profiles.chmod(0o111)
        self.addCleanup(profiles.chmod, 0o755)
        result = run()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(f"UNSUPPORTED agent root {profiles} cannot be listed (EACCES)", result.stderr)

    def test_source_deploying_a_plugin_registry_fails_closed(self):
        # Managed plugin registries (user, profile, XDG, project, Claude) change agent discovery after deployment.
        catalog = self.evidence()
        self.assertEqual(self.run_checker("--catalog", catalog).returncode, 0)
        home = self.root / "home"
        for created, cleanup, message in [
            ("private_dot_omp/private_plugins/installed_plugins.json", "private_dot_omp/private_plugins", "deploys plugin registry ~/.omp/plugins"),
            ("private_dot_omp/private_profiles/work/plugins/x", "private_dot_omp/private_profiles/work", "deploys plugin registry ~/.omp/profiles/work/plugins"),
            ("dot_local/share/omp/plugins/x", "dot_local/share/omp", "deploys plugin registry ~/.local/share/omp/plugins"),
            ("xdg/omp/profiles/w/plugins/x", "xdg", "deploys plugin registry ~/xdg/omp/profiles/w/plugins"),
            ("src/app/dot_omp/plugins/x", "src", "deploys plugin registry ~/src/app/.omp/plugins"),
            ("dot_claude/plugins/installed_plugins.json", "dot_claude/plugins", "deploys plugin registry ~/.claude/plugins"),
            ("dot_local/share/symlink_omp", "dot_local/share/symlink_omp", f"UNSUPPORTED source {home / 'dot_local/share/symlink_omp'}"),
            (".chezmoiexternal.toml", ".chezmoiexternal.toml", "chezmoi external not mirrored"),
        ]:
            with self.subTest(created=created):
                (home / created).parent.mkdir(parents=True, exist_ok=True)
                (home / created).write_text("{}\n")
                result = self.run_checker("--catalog", catalog)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(message, result.stderr)
                target = home / cleanup
                shutil.rmtree(target) if target.is_dir() else target.unlink()
                self.assertEqual(self.run_checker("--catalog", catalog).returncode, 0)

    def test_source_alternative_spellings_fail_closed(self):
        # Only the canonical source spellings are mirrored (and probed by omp-baseline); any other entry deploying the
        # same target fails closed, whichever profile it serves. Agent files are read by their target names.
        local = self.root / "home/private_dot_omp/private_profiles/local/private_agent"
        (local / "private_agents").mkdir(parents=True)
        (local / "private_config.yml").write_text(self.config.read_text())
        runs = {
            "default": lambda *a: self.run_checker("--catalog", self.evidence(), *a),
            "local": lambda *a: self.run_checker("--profile", "local", "--catalog", self.evidence(models_file=local / "private_models.yml", profile="local"), *a),
        }
        for run in runs.values():
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
        home = self.root / "home"
        seance = "---\nname: seance\ndescription: fixture\nmodel: '@task'\nthinkingLevel: low\ntools: [bash, write]\n---\n"
        omp = "private_dot_omp"
        for created, cleanup, profile, message in [
            (f"{omp}/private_profiles/local/private_agent/agents/seance.md", f"{omp}/private_profiles/local/private_agent/agents", "local", "deploys agents; only private_agents is mirrored"),
            (f"{omp}/private_agent/exact_agents/seance.md", f"{omp}/private_agent/exact_agents", "default", "deploys agents; only private_agents is mirrored"),
            (f"{omp}/private_agent/literal_agents/seance.md", f"{omp}/private_agent/literal_agents", "default", "deploys agents; only private_agents is mirrored"),
            ("dot_omp/agent/agents/seance.md", "dot_omp", "default", "deploys .omp; only private_dot_omp is mirrored"),
            (f"{omp}/agent/agents/seance.md", f"{omp}/agent", "default", "deploys agent; only private_agent is mirrored"),
            (f"{omp}/private_profiles/exact_local/agent/agents/seance.md", f"{omp}/private_profiles/exact_local", "local", "deploys local; only local is mirrored"),
            (f"{omp}/private_profiles/work/private_agent/private_agents/seance.md", f"{omp}/private_profiles/work", "default", "(profile work not certified"),
            (f"{omp}/private_agent/config.yaml", f"{omp}/private_agent/config.yaml", "default", "deploys config.yaml; only no entry is mirrored"),
            (f"{omp}/private_agent/models.yml", f"{omp}/private_agent/models.yml", "default", "deploys models.yml; only private_models.yml is mirrored"),
            (f"{omp}/private_agent/private_agents/symlink_seance.md", f"{omp}/private_agent/private_agents/symlink_seance.md", "default", "(chezmoi symlink, script or encrypted entry not mirrored)"),
            (f"{omp}/private_agent/private_agents/encrypted_seance.md.age", f"{omp}/private_agent/private_agents/encrypted_seance.md.age", "default", "(encrypted; contents not mirrored)"),
            (f"{omp}/agents/seance.md", f"{omp}/agents", "default", "deploys project agents dir ~/.omp/agents; not mirrored"),
            ("src/app/dot_omp/exact_agents/seance.md", "src", "default", "deploys project agents dir ~/src/app/.omp/agents; not mirrored"),
            # chezmoi deploys an external_ dir's children unparsed: this is ~/src/app/.omp/agents/seance.md.
            ("src/external_app/.omp/agents/seance.md", "src", "default", "(chezmoi external_ dir deploys its children unparsed; not mirrored)"),
            # A launch from ~/src/probe reads that dir's project inputs, which only the live check at that cwd sees.
            ("src/probe/dot_omp/config.yml", "src", "default", "deploys ~/src/probe/.omp/config.yml, a project .omp input"),
            ("src/probe/dot_omp/private_extensions/index.ts", "src", "default", "deploys ~/src/probe/.omp/extensions, a project .omp input"),
            (f"{omp}/settings.json", f"{omp}/settings.json", "default", "deploys ~/.omp/settings.json, a project .omp input"),
            ("src/probe/dot_claude/hooks/pre/index.ts", "src", "default", "deploys ~/src/probe/.claude/hooks, project hooks or tools"),
            ("src/probe/dot_env.local", "src", "default", "deploys ~/src/probe/.env.local, a dotenv file"),
            ("src/probe/dot_mcp.json", "src", "default", "deploys ~/src/probe/.mcp.json, a mcp-json provider input"),
            ("src/probe/dot_claude/settings.json", "src", "default", "deploys ~/src/probe/.claude/settings.json, a claude provider input"),
            # macOS deploys onto case-insensitive APFS: each of these is the canonical file or dir there.
            (f"{omp}/private_agent/private_Config.yml", f"{omp}/private_agent/private_Config.yml", "default", "deploys config.yml; only private_config.yml is mirrored"),
            (f"{omp}/private_Agent/private_agents/seance.md", f"{omp}/private_Agent", "default", "deploys agent; only private_agent is mirrored"),
            ("private_dot_OMP/agent/agents/seance.md", "private_dot_OMP", "default", "deploys .omp; only private_dot_omp is mirrored"),
            (f"{omp}/private_profiles/Local/private_agent/private_agents/seance.md", f"{omp}/private_profiles/Local", "local", "deploys local; only local is mirrored"),
            ("dot_claude/Plugins/seance.md", "dot_claude", "default", "deploys plugin registry ~/.claude/Plugins"),
            ("src/app/dot_OMP/Agents/seance.md", "src", "default", "deploys project agents dir ~/src/app/.OMP/Agents"),
            (f"{omp}/private_agent/private_agents/Architect.md", f"{omp}/private_agent/private_agents/Architect.md", "default", "once names are case-folded"),
            (f"{omp}/private_agent/private_agents/se\u017fance.md", f"{omp}/private_agent/private_agents/se\u017fance.md", "default", "fold to ASCII or ignore"),
        ]:
            with self.subTest(created=created):
                if not CASE_SENSITIVE and aliases_existing(home, created):
                    self.skipTest("needs a case-sensitive filesystem: APFS opens this name as the existing entry")
                (home / created).parent.mkdir(parents=True, exist_ok=True)
                (home / created).write_text(seance)
                result = runs[profile]()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(message, result.stderr)
                target = home / cleanup
                shutil.rmtree(target) if target.is_dir() else target.unlink()
                result = runs[profile]()
                self.assertEqual(result.returncode, 0, result.stderr)
        # A prefixed or .literal name deploys seance.md verbatim, so it is parsed as the user seance it shadows with.
        for name in ("private_seance.md", "seance.md.literal", "readonly_seance.md"):
            with self.subTest(parsed=name):
                (self.agent / "private_agents" / name).write_text(seance)
                result = runs["default"]("--json")
                report = self.agent_report(result, "seance")
                self.assertEqual((report["source"], report["path"]), ("user", str(self.agent / "private_agents" / name)))
                self.assertIn("bash", report["declared"])
                (self.agent / "private_agents" / name).unlink()

    def test_source_provider_launch_file_gated_by_certified_disabled_providers(self):
        # ~/.config/opencode/opencode.json is read by a launch from ~/.config/opencode while opencode is enabled.
        opencode = self.root / "home/dot_config/opencode/opencode.json"
        opencode.parent.mkdir(parents=True)
        opencode.write_text("{}\n")
        result = self.run_checker("--catalog", self.evidence())
        self.assertEqual(result.returncode, 1)
        self.assertIn("deploys ~/.config/opencode/opencode.json, a opencode provider input", result.stderr)
        with self.config.open("a") as config:
            config.write("disabledProviders: [opencode]\n")
        self.native["disabledProviders"] = ["opencode"]
        result = self.run_checker("--catalog", self.evidence())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_agents_resolve_in_deployed_name_order(self):
        # Upstream sorts the deployed names and keeps the first definition of a name: private_aaa.md deploys aaa.md,
        # which precedes architect.md, so its architect is the one dispatched and must be the one certified.
        catalog = self.evidence()
        aaa = self.agent / "private_agents/private_aaa.md"
        aaa.write_text("---\nname: architect\ndescription: fixture\nmodel: '@task'\nthinkingLevel: low\ntools: [bash, write]\n---\n")
        result = self.run_checker("--json", "--catalog", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.agent_report(result, "architect")["path"], str(aaa))
        self.assertTrue(any(e.startswith("TOOLS architect declared [bash, write]") for e in json.loads(result.stdout)["errors"]), result.stdout)
        # Two entries deploying one target are an inconsistent chezmoi state and fail closed.
        (self.agent / "private_agents/aaa.md").write_text(aaa.read_text())
        result = self.run_checker("--catalog", catalog)
        self.assertIn(f"deploys aaa.md, as does", result.stderr)
        # Prefixes are cut in chezmoi's order for the entry's kind: a file takes after_ only after run_, so after_zz.md
        # deploys after_zz.md, which also precedes architect.md (not zz.md, which would follow it).
        text = aaa.read_text()
        aaa.unlink()
        (self.agent / "private_agents/aaa.md").unlink()
        after = self.agent / "private_agents/after_zz.md"
        after.write_text(text)
        result = self.run_checker("--json", "--catalog", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.agent_report(result, "architect")["path"], str(after))

    def agent_report(self, result, name):
        return next(agent for agent in json.loads(result.stdout)["agents"] if agent["name"] == name)

    def test_21_native_tool_gates(self):
        self.add("extra", "llama.cpp/test", "low", ["read", "grep", "lsp", "find", "bash", "todo", "ask", "frobnicate"])
        result = self.run_checker("--json")
        extra = self.agent_report(result, "extra")
        # lsp needs task.enableLsp; children never get ask; find (auto) and todo depend on runtime state.
        # Only the explicit list, yield and the executor's wait start active: ast_grep is a registered but
        # inactive auto-include, and the xd:// device-only write stays as a transport.
        self.assertEqual(set(extra["callable"]), {"read", "grep", "bash", "yield", "wait", "write(xd-devices-only)"})
        self.assertEqual([c.split(" ")[0] for c in extra["conditional"]], ["find", "todo"])
        self.assertIn("UNSUPPORTED extra tool frobnicate is not built in (custom and extension tools are not mirrored)", json.loads(result.stdout)["errors"])
        self.assertIn("ast_grep", self.agent_report(result, "sol")["callable"])  # no list: every registered tool is active
        overlay = self.root / "gates.yml"
        overlay.write_text("grep:\n  enabled: false\nfind:\n  enabled: \"on\"\ntask:\n  enableLsp: true\n")
        extra = self.agent_report(self.run_checker("--json", "--config", str(overlay)), "extra")
        self.assertNotIn("grep", extra["callable"])
        self.assertIn("find", extra["callable"])
        self.assertIn("lsp", extra["callable"])

    def test_22_spawns_and_recursion_depth(self):
        (self.agent / "private_agents/lead.md").write_text("---\nname: lead\ndescription: x\nmodel: llama.cpp/test\nthinkingLevel: low\ntools: [read]\nspawns: scout\n---\n")
        result = self.run_checker("--json")
        self.assertTrue({"task", "wait"} <= set(self.agent_report(result, "lead")["callable"]))
        sol = self.agent_report(result, "sol")
        self.assertIn("task", sol["callable"])
        self.assertFalse({"ask", "todo", "lsp", "checkpoint"} & set(sol["callable"]))
        overlay = self.root / "depth.yml"
        overlay.write_text("task:\n  maxRecursionDepth: 1\n")
        result = self.run_checker("--json", "--config", str(overlay))
        self.assertFalse({"task", "wait"} & set(self.agent_report(result, "lead")["callable"]))
        self.assertNotIn("task", self.agent_report(result, "sol")["callable"])

    def test_23_model_default_thinking(self):
        (self.agent / "private_agents/extra.md").write_text('---\nname: extra\ndescription: x\nmodel: "llama.cpp/test"\n---\n')
        gap = "UNVERIFIED extra thinking falls to the model default of llama.cpp/test"
        result = self.run_checker("--catalog", self.evidence())
        self.assertEqual(result.returncode, 1)
        self.assertIn(gap, result.stderr)
        models = self.agent / "private_models.yml"
        provider = "providers:\n  llama.cpp:\n    baseUrl: http://localhost:8080/v1\n    api: openai-completions\n    auth: none\n"
        custom = "    models:\n      - id: test\n        thinking: {mode: effort, efforts: [low, medium, high], defaultLevel: medium}\n"
        models.write_text(provider + custom)
        result = self.run_checker("--json", "--catalog", self.evidence())
        self.assertEqual(result.returncode, 0, result.stderr)
        extra = self.agent_report(result, "extra")
        self.assertEqual((extra["thinking"], extra["thinkingLayer"]), ("medium", "model-default"))
        # Without evidence that native loading accepted models.yml, its defaults count for nothing.
        self.assertIn(gap, self.run_checker().stderr)
        # An override's thinking object replaces the custom one whole: no defaultLevel of its own, no default.
        override = "    modelOverrides:\n      test:\n        thinking: {mode: effort, efforts: [low, medium, high]%s}\n"
        models.write_text(provider + custom + override % "")
        result = self.run_checker("--catalog", self.evidence())
        self.assertEqual(result.returncode, 1)
        self.assertIn(gap, result.stderr)
        models.write_text(provider + custom + override % ", defaultLevel: low")
        self.assertEqual(self.agent_report(self.run_checker("--json", "--catalog", self.evidence()), "extra")["thinking"], "low")
        # Native loading rejects the whole file on any violation and says so only on stderr: no default survives.
        result = self.run_checker("--catalog", self.evidence(stderr=REJECTED))
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            f"MODELS {models} rejected by native loading, custom models and overrides discarded: "
            "Schema error: providers.llama.cpp.models.0.thinking.supportsDisplay: must be boolean (was a string)",
            result.stderr,
        )
        self.assertIn(gap, result.stderr)

    def test_24_catalog_clamp(self):
        catalog = self.evidence(models=self.MODELS + [
            ("llama.cpp", "steps", ["low", "medium", "xhigh"]),
            ("llama.cpp", "flat", []),
            ("llama.cpp", "unsorted", ["high", "low"]),
        ])
        self.add("up", "llama.cpp/steps", "high")
        self.add("floor", "llama.cpp/steps", "minimal")
        self.add("flat", "llama.cpp/flat", "high")
        self.add("odd", "llama.cpp/unsorted", "medium")  # the native loop stops at the first higher effort
        result = self.run_checker("--catalog", catalog, "--json")
        levels = {name: self.agent_report(result, name)["thinking"] for name in ("up", "floor", "flat", "odd")}
        self.assertEqual(levels, {"up": "medium", "floor": "low", "flat": "off", "odd": "high"})

    def test_25_catalog_evidence_must_match(self):
        models = self.agent / "private_models.yml"
        stale = self.evidence()
        models.write_text("providers: {}\n")
        raw = self.root / "raw.json"
        raw.write_text('{"models": []}')
        for catalog, message in [
            (self.evidence(version="18.4.4"), "was captured on omp 18.4.4, checking 18.12.6"),
            (self.evidence(profile="local"), "was captured for profile local, checking default"),
            (stale, f"was captured from a different {models}"),
            (str(raw), "is not native catalog evidence"),
        ]:
            result = self.run_checker("--catalog", catalog)
            self.assertEqual(result.returncode, 1)
            self.assertIn(f"CATALOG {catalog} {message}", result.stderr)
            self.assertIn("UNVERIFIED architect thinking xhigh unclamped", result.stderr)

    def test_26_catalog_ladder_clamps_contract(self):
        # A models.yml override narrowing gpt-6.1-sol reaches the native listing; the contract fails on it.
        narrowed = [(p, i, ["low", "medium", "high"] if i == "gpt-6.1-sol" else t) for p, i, t in self.MODELS]
        result = self.run_checker("--catalog", self.evidence(models=narrowed))
        self.assertEqual(result.returncode, 1)
        self.assertIn("EFFORT architect expected xhigh resolved high via selector-suffix (openai-codex/gpt-6.1-sol:high:xhigh)", result.stderr)
        self.assertIn("EFFORT auditor expected xhigh resolved high via selector-suffix", result.stderr)
        self.assertNotIn("EFFORT sol", result.stderr)

    def test_27_live_code_surfaces(self):
        cwd, run = self.live_fixture()
        home = self.root / "home-temp"
        live = home / ".omp/agent"
        shutil.copytree(REVIEWED, live / "extensions")
        (live / "hooks/pre").mkdir(parents=True)
        (live / "hooks/pre/notes.md").write_text("not a module\n")
        (home / ".claude/hooks").mkdir(parents=True)
        (home / ".claude/hooks/herdr-agent-state.sh").write_text("#!/bin/sh\n")  # neither pre/ nor post/
        result = run()
        self.assertEqual(result.returncode, 0, result.stderr)
        symlink_target = self.root / "external-hook.ts"
        symlink_target.write_text("export default () => {};\n")
        hook = cwd / ".omp/hooks/pre/shared.ts"
        hook.parent.mkdir(parents=True)
        hook.symlink_to(symlink_target)
        result = run()
        self.assertIn(f"UNSUPPORTED hook {hook} (not mirrored)", result.stderr)
        hook.unlink()
        extra = live / "extensions/extra.ts"
        extra.write_text("export default (pi) => pi.registerTool({ name: 'extra_write' });\n")
        digest = hashlib.sha256(extra.read_bytes()).hexdigest()
        result = run()
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"UNSUPPORTED extension {extra} sha256 {digest} is not a reviewed module", result.stderr)
        extra.unlink()
        for created, top, message in [
            (live / "extensions/pkg/index.ts", live / "extensions/pkg", f"UNSUPPORTED extension package {live / 'extensions/pkg'}"),
            (live / "hooks/pre/x.ts", None, f"UNSUPPORTED hook {live / 'hooks/pre/x.ts'}"),
            (live / "tools/x.ts", live / "tools", f"UNSUPPORTED custom tool {live / 'tools/x.ts'}"),
            (cwd / ".omp/extensions/x.ts", cwd / ".omp/extensions", f"UNSUPPORTED extension {cwd / '.omp/extensions/x.ts'} sha256"),
            (cwd / ".claude/hooks/post/x.js", cwd / ".claude", f"UNSUPPORTED hook {cwd / '.claude/hooks/post/x.js'}"),
            (home / ".claude/tools/x.mjs", home / ".claude/tools", f"UNSUPPORTED custom tool {home / '.claude/tools/x.mjs'}"),
            (home / ".codex/hooks/pre-bash.ts", home / ".codex", f"UNSUPPORTED hook {home / '.codex/hooks/pre-bash.ts'}"),
            (cwd / ".codex/tools/x.cjs", cwd / ".codex", f"UNSUPPORTED custom tool {cwd / '.codex/tools/x.cjs'}"),
            (cwd / ".omp/config.yml", None, "UNSUPPORTED extensions configured: ./x.ts"),
            (live / "settings.json", None, f"UNSUPPORTED extensions configured in {live / 'settings.json'}: ./y.ts"),
        ]:
            created.parent.mkdir(parents=True, exist_ok=True)
            body = {"config.yml": "extensions: [./x.ts]\n", "settings.json": '{"extensions": ["./y.ts"]}'}.get(created.name, "export default () => {};\n")
            created.write_text(body)
            result = run()
            self.assertEqual(result.returncode, 1, created)
            self.assertIn(message, result.stderr)
            if top:
                shutil.rmtree(top)
            else:
                created.unlink()
        result = run()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_28_source_code_surfaces(self):
        catalog = lambda: self.evidence()
        ext = self.agent / "private_extensions"
        shutil.copytree(REVIEWED, ext)
        result = self.run_checker("--catalog", catalog())
        self.assertEqual(result.returncode, 0, result.stderr)
        extra = ext / "extra.ts"
        extra.write_text("export default (pi) => pi.registerTool({ name: 'extra_write' });\n")
        digest = hashlib.sha256(extra.read_bytes()).hexdigest()
        self.assertIn(f"UNSUPPORTED extension {extra} sha256 {digest} is not a reviewed module", self.run_checker("--catalog", catalog()).stderr)
        # The local profile links the default profile's extensions dir, which is checked in its place.
        local = self.root / "home/private_dot_omp/private_profiles/local/private_agent"
        (local / "private_agents").mkdir(parents=True)
        (local / "private_config.yml").write_text(self.config.read_text())
        link = local / "symlink_extensions.tmpl"
        link.write_text("{{ .chezmoi.homeDir }}/.omp/agent/extensions\n")
        local_catalog = lambda: self.evidence(models_file=local / "private_models.yml", profile="local")
        result = self.run_checker("--profile", "local", "--catalog", local_catalog())
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"UNSUPPORTED extension {extra} sha256 {digest}", result.stderr)
        extra.unlink()
        result = self.run_checker("--profile", "local", "--catalog", local_catalog())
        self.assertEqual(result.returncode, 0, result.stderr)
        link.write_text("/elsewhere/extensions\n")
        self.assertIn(f"UNSUPPORTED source {link}", self.run_checker("--profile", "local").stderr)
        link.unlink()
        for created, message in [
            (ext / "executable_x.ts.tmpl", f"UNSUPPORTED source {ext / 'executable_x.ts.tmpl'}"),
            (self.agent / "private_hooks/pre/x.ts", f"UNSUPPORTED source {self.agent / 'private_hooks'} (hooks not mirrored)"),
            (self.agent / "tools/x.ts", f"UNSUPPORTED source {self.agent / 'tools'} (tools not mirrored)"),
        ]:
            created.parent.mkdir(parents=True, exist_ok=True)
            created.write_text("export default () => {};\n")
            result = self.run_checker("--catalog", catalog())
            self.assertEqual(result.returncode, 1, created)
            self.assertIn(message, result.stderr)
            created.unlink()

    def test_29_dotenv_config_overlay_and_precedence(self):
        cwd, run = self.live_fixture()
        live = self.root / "home-temp/.omp/agent"
        host = self.root / "host.yml"
        host.write_text("retry:\n  modelFallback: true\n")
        (live / ".env").write_text(f"PI_CONFIG_FILES={host}\n")
        self.native["retry.modelFallback"] = True
        result = run()
        self.assertEqual(result.returncode, 1)
        self.assertIn("RUNTIME architect retry may switch models", result.stderr)
        self.assertNotIn("SETTINGS", result.stderr)
        # A set process value wins over the dotenv file; ":" names no overlay, so the mirror disagrees with native.
        result = run(PI_CONFIG_FILES=":")
        self.assertIn("SETTINGS retry.modelFallback mirror false native true", result.stderr)

    def test_30_environment_screen(self):
        cwd, run = self.live_fixture()
        self.assertEqual(run(PI_SESSION_FILE="/x.jsonl", PI_AUTH_BROKER_URL="http://x").returncode, 0)
        self.assertEqual(run(PI_REQUEST_COMPRESSION="0").returncode, 0)
        self.assertIn("UNSUPPORTED env PI_CODEX_ZSTD is set", run(PI_CODEX_ZSTD="0").stderr)
        result = run(PI_FROBNICATE="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("UNSUPPORTED env PI_FROBNICATE is set (not mirrored)", result.stderr)
        # Bun loads launch-dir dotenv files with its own grammar: an OMP key there fails closed, others do not.
        dotenv = cwd / ".env.local"
        dotenv.write_text("FOO=1\n")
        self.assertEqual(run().returncode, 0)
        dotenv.write_text("PI_SMOL_MODEL=llama.cpp/test\n")
        self.assertIn(f"UNSUPPORTED dotenv {dotenv} sets PI_SMOL_MODEL (launch-dir dotenv not mirrored)", run().stderr)

    def test_31_role_env_overrides_after_settings_check(self):
        self.add("architect", "@plan:xhigh", "xhigh", ["read", "grep", "glob", "web_search", "yield"])
        cwd, run = self.live_fixture()
        self.assertEqual(run().returncode, 0, run().stderr)
        # main.ts applies PI_PLAN_MODEL to the plan role at runtime; `config list` never shows it.
        result = run(PI_PLAN_MODEL="anthropic/claude-opus-5-5")
        self.assertEqual(result.returncode, 1)
        self.assertIn("MODEL architect", result.stderr)
        self.assertNotIn("SETTINGS", result.stderr)

    def test_32_mcp_servers(self):
        cwd, run = self.live_fixture()
        home = self.root / "home-temp"
        live = home / ".omp/agent"
        (cwd / ".omp/mcp.json").write_text(json.dumps({"mcpServers": {"proj": {"command": "x"}}}))
        (live / "mcp.json").write_text(json.dumps({
            "mcpServers": {"user": {"command": "x"}, "off": {"command": "x", "enabled": False},
                           "forced": {"command": "x", "enabled": False}, "gone": {"command": "x"}},
            "disabledServers": ["gone"], "enabledServers": ["forced"],
        }))
        result = run(args=["--json"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.agent_report(result, "sol")["mcp"], ["forced", "proj", "user"])
        self.assertNotIn("mcp:proj", self.agent_report(result, "sol")["callable"])
        # A foreign user source is opt-in; a foreign project source is read unless its provider is disabled.
        (home / ".cursor").mkdir()
        (home / ".cursor/mcp.json").write_text("{}")
        self.assertEqual(run().returncode, 0)
        foreign = cwd / ".cursor/mcp.json"
        foreign.parent.mkdir()
        foreign.write_text("{}")
        self.assertIn(f"UNSUPPORTED mcp source {foreign} (provider cursor not mirrored)", run().stderr)
        with (live / "config.yml").open("a") as config:
            config.write("disabledProviders: [cursor]\n")
        self.native["disabledProviders"] = ["cursor"]
        self.assertEqual(run().returncode, 0, run().stderr)

    def test_33_plugin_registry_ignores_provider_toggle(self):
        cwd, run = self.live_fixture()
        home = self.root / "home-temp"
        with (home / ".omp/agent/config.yml").open("a") as config:
            config.write("disabledProviders: [claude-plugins]\n")
        self.native["disabledProviders"] = ["claude-plugins"]
        self.assertEqual(run().returncode, 0, run().stderr)
        registry = home / ".claude/plugins/installed_plugins.json"
        registry.parent.mkdir(parents=True)
        registry.write_text('{"version": 2, "plugins": {}}')
        self.assertIn(f"UNSUPPORTED agent root {registry} (extension/plugin agents not mirrored)", run().stderr)

    def test_34_runtime_branches_fail_closed(self):
        # Each case against the passing control of test_01; the native evidence agrees unless the case is a mismatch.
        base = self.config.read_text()
        retry_off = "retry:\n  modelFallback: false\n"
        for config, native, message in [
            (base, {"retry.modelFallback": True}, "SETTINGS retry.modelFallback mirror false native true"),
            (base.replace(retry_off, ""), {"retry.modelFallback": True}, "RUNTIME architect retry may switch models"),
            (base.replace("  structured: true\n", ""), {"task.structured": False},
             "RUNTIME architect task.structured is off: caller output schemas are dropped"),
            (base.replace("  agentModelOverrides: {}\n", "  agentModelOverrides: {}\n  agentPrewalk: {sol: 'on'}\n"),
             {"task.agentPrewalk": {"sol": "on"}}, "RUNTIME sol prewalk armed (@smol)"),
        ]:
            self.config.write_text(config)
            result = self.run_checker("--catalog", self.evidence(native={**self.native, **native}))
            self.assertEqual(result.returncode, 1, config)
            self.assertIn(message, result.stderr)
        self.config.write_text(base)
        (self.agent / "private_agents/sol.md").write_text(
            '---\nname: sol\ndescription: x\nmodel: "openai-codex/gpt-6.1-sol"\nthinkingLevel: high\nprewalk: true\n---\n'
        )
        self.assertIn("RUNTIME sol prewalk armed (@smol)", self.run_checker("--catalog", self.evidence()).stderr)
        (self.agent / "private_agents/browser.md").write_text("---\nname: browser\ndescription: x\nthinkingLevel: medium\ntools: [eval]\n---\n")
        self.add("sol", "openai-codex/gpt-6.1-sol", "high")
        result = self.run_checker("--catalog", self.evidence())
        self.assertEqual(result.returncode, 1)
        self.assertIn("MODEL browser resolves only through the parent session model", result.stderr)

    def test_35_live_settings_files(self):
        self.add("architect", "@plan:xhigh", "xhigh", ["read", "grep", "glob", "web_search", "yield"])
        cwd, run = self.live_fixture()
        live = self.root / "home-temp/.omp/agent"
        # A project role that is not a string or string list is cleared, so the global plan role stays.
        (cwd / ".omp/config.yml").write_text("modelRoles:\n  plan: null\n")
        self.assertEqual(run().returncode, 0, run().stderr)
        (cwd / ".omp/config.yml").write_text("modelRoles:\n  plan: llama.cpp/test\n")
        self.native["modelRoles"] = {**self.native["modelRoles"], "plan": "llama.cpp/test"}
        self.assertIn("MODEL architect", run().stderr)
        (cwd / ".omp/config.yml").unlink()
        self.native["modelRoles"]["plan"] = "openai-codex/gpt-6.1-sol:high"
        (live / "config.yml").rename(live / "config.yaml")
        self.assertEqual(run().returncode, 0, run().stderr)
        (live / "config.yaml").unlink()
        (live / "settings.json").write_text("{}")
        self.assertIn(f"UNSUPPORTED {live} has no config.yml; legacy settings.json/agent.db migration", run().stderr)

    def test_36_command_backed_values_fail_closed(self):
        # omp-baseline's probes cannot run "!command" values, so no layer holding one is certified.
        cwd, run = self.live_fixture()
        live = self.root / "home-temp/.omp/agent"
        self.assertEqual(run().returncode, 0, run().stderr)
        host = self.root / "host.yml"
        host.write_text("auth:\n  broker:\n    token: '!cat /secret'\n")
        (live / ".env").write_text(f"PI_CONFIG_FILES={host}\n")
        result = run()
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"UNSUPPORTED {host}: auth.broker.token is command-backed", result.stderr)
        (live / ".env").unlink()
        (cwd / ".omp/settings.json").write_text('{"auth": {"broker": {"url": "!printf http://x"}}}')
        self.assertIn(f"UNSUPPORTED {cwd}/.omp/settings.json: auth.broker.url is command-backed", run().stderr)
        (cwd / ".omp/settings.json").unlink()
        (live / "models.yml").write_text("providers:\n  x:\n    headers:\n      X-Key: '!printf k'\n")
        self.assertIn(f"UNSUPPORTED {live}/models.yml: providers.x.headers.X-Key is command-backed", run().stderr)
        # A literal or env-backed value is not a command.
        (live / "models.yml").write_text("providers:\n  x:\n    headers:\n      X-Key: 'MY_KEY'\n")
        self.assertNotIn("command-backed", run().stderr)

    def test_37_tool_lists_parse_like_native(self):
        # Malformed/empty declarations fail closed to an empty allowlist; only absent/null selects defaults.
        cases = {"tools: [42]": [], "tools: \"\"": [], "tools: \" , \"": [], "tools: []": [],
                 "tools: [\" bash\"]": [" bash"], "tools: \" bash, read \"": ["bash", "read"]}
        for line, declared in cases.items():
            with self.subTest(line=line):
                (self.agent / "private_agents/extra.md").write_text(
                    f"---\nname: extra\ndescription: x\nmodel: llama.cpp/test\nthinkingLevel: low\n{line}\n---\n")
                result = self.run_checker("--json")
                self.assertEqual(self.agent_report(result, "extra")["declared"], declared)

    def test_malformed_tools_declaration_grants_no_builtin_tools(self):
        (self.agent / "private_agents/extra.md").write_text(
            "---\nname: extra\ndescription: x\nmodel: llama.cpp/test\nthinkingLevel: low\ntools: [42]\n---\n")
        result = self.agent_report(self.run_checker("--json"), "extra")
        self.assertEqual(result["declared"], [])
        self.assertNotIn("read", result["callable"])

    def test_agent_structured_override_keeps_own_schema_but_not_caller_contract(self):
        # task.structured off: structured: true keeps yield and the agent's own schema (structured-subagent.ts:241-254)
        # but task/index.ts:781-782 drops caller schemas, so a contract agent still fails.
        self.config.write_text(self.config.read_text().replace("  structured: true\n", "  structured: false\n"))
        self.native["task.structured"] = False
        schema = {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}}}
        (self.agent / "private_agents/extra.md").write_text("---\nname: extra\ndescription: x\nmodel: llama.cpp/test\nthinkingLevel: low\nstructured: true\noutput:\n  type: object\n  required: [answer]\n  properties:\n    answer: {type: string}\ntools: [read]\n---\n")
        architect = self.agent / "private_agents/architect.md"
        architect.write_text(architect.read_text().replace("thinkingLevel:", "structured: true\nthinkingLevel:", 1))
        result = self.run_checker("--json", "--catalog", self.evidence())
        extra = self.agent_report(result, "extra")
        self.assertEqual(extra["output"], schema)
        self.assertTrue(extra["structured"])
        self.assertIn("yield", extra["callable"])
        self.assertIn("yield", self.agent_report(result, "architect")["callable"])
        result = self.run_checker("--catalog", self.evidence())
        self.assertEqual(result.returncode, 1)
        self.assertIn("RUNTIME architect task.structured is off: caller output schemas are dropped (frontmatter structured: true", result.stderr)

    def test_agent_structured_override_and_auto_prewalk(self):
        self.config.write_text(self.config.read_text().replace("  structured: true\n", ""))
        self.config.write_text(self.config.read_text() + "prewalk:\n  auto: suggest\n")
        self.native["prewalk.auto"] = "suggest"
        self.assertNotIn("automatic prewalk is on", self.run_checker("--catalog", self.evidence()).stderr)
        self.config.write_text(self.config.read_text().replace("auto: suggest", "auto: on"))
        self.native["prewalk.auto"] = "on"
        self.assertIn("automatic prewalk is on", self.run_checker("--catalog", self.evidence()).stderr)

    def test_seance_is_a_bundled_agent_with_restricted_policy(self):
        report = self.agent_report(self.run_checker("--json"), "seance")
        self.assertEqual(report["source"], "bundled")
        self.assertIsNone(report["model"])
        self.assertEqual(report["mcp"], [])
        self.assertTrue(report["structured"])
        self.assertEqual(report["callable"], ["read", "grep", "glob", "yield"])
        # v18.12.6 task/index.ts:781-785, structured-subagent.ts:403-405; bundled frontmatter
        # (prompts/agents/seance.md:1-6) does not opt in when task.structured is off.
        self.config.write_text(self.config.read_text().replace("  structured: true\n", "  structured: false\n"))
        report = self.agent_report(self.run_checker("--json"), "seance")
        self.assertFalse(report["structured"])
        self.assertEqual(report["callable"], ["read", "grep", "glob"])

    def test_user_seance_shadow_has_ordinary_policy(self):
        self.add("seance", "llama.cpp/test", "low", ["read", "grep", "glob"])
        cwd, run = self.live_fixture()
        (cwd / ".omp/mcp.json").write_text(json.dumps({"mcpServers": {"proj": {"command": "x"}}}))
        result = run(args=["--json"])
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.agent_report(result, "seance")
        self.assertEqual(report["source"], "user")
        self.assertEqual(report["model"], "llama.cpp/test")
        self.assertEqual(report["thinking"], "low")
        self.assertEqual(report["thinkingLayer"], "frontmatter")
        self.assertTrue(report["structured"])
        self.assertEqual(report["callable"], ["read", "grep", "glob", "yield", "write(xd-devices-only)"])
        self.assertEqual(report["mcp"], ["proj"])
        self.assertEqual(report["path"], str(self.root / "home-temp/.omp/agent/agents/seance.md"))

    def test_text_report_includes_definition_path(self):
        result = self.run_checker("--catalog", self.evidence())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"source=user {self.agent / 'private_agents/architect.md'}", result.stdout)
        self.assertNotIn("undefined", result.stdout)

    def test_38_escalation_model_lists_and_auditor_schema(self):
        catalog = lambda: self.evidence()
        auditor = self.agent / "private_agents/auditor.md"
        original = auditor.read_text()
        # A reserve candidate fails even though Sol, listed first, resolves.
        for name, models, thinking, tools in [("architect", "@plan:xhigh, openai-codex/gpt-6-astra:xhigh", "xhigh", "\ntools: [read, grep, glob, web_search, yield]"),
                                              ("sol", "@plan, openai-codex/gpt-6-astra:high", "high", "")]:
            quoted = ", ".join(f'"{m}"' for m in models.split(", "))
            (self.agent / f"private_agents/{name}.md").write_text(f"---\nname: {name}\ndescription: agent\nmodel: [{quoted}]\nthinkingLevel: {thinking}{tools}\n---\nbody\n")
        result = self.run_checker("--catalog", catalog())
        self.assertEqual(result.returncode, 1)
        self.assertIn("MODEL architect declares [@plan:xhigh, openai-codex/gpt-6-astra:xhigh] expected [@plan:xhigh] (no reserve candidates)", result.stderr)
        self.assertIn("MODEL sol declares [@plan, openai-codex/gpt-6-astra:high] expected [@plan] (no reserve candidates)", result.stderr)
        self.add("architect", "@plan:xhigh", "xhigh", ["read", "grep", "glob", "web_search", "yield"])
        self.add("sol", "@plan", "high")
        # Key order is irrelevant; a weaker verdict enum, a looser nested object or no schema is not.
        reordered = original.replace("  type: object\n  additionalProperties: false\n", "  additionalProperties: false\n  type: object\n", 1)
        self.assertNotEqual(reordered, original)
        for text, ok in [(reordered, True), (original.replace("enum: [PASS, BLOCK, UNVERIFIED]", "enum: [PASS, BLOCK]"), False),
                         (original.replace("        additionalProperties: false\n", "", 1), False)]:
            auditor.write_text(text)
            result = self.run_checker("--catalog", catalog())
            self.assertEqual(result.returncode, 0 if ok else 1, result.stderr)
            if not ok:
                self.assertIn("OUTPUT auditor schema differs from the reviewed verdict schema", result.stderr)
        head, body = original.split("output:\n", 1)
        auditor.write_text(head + body[body.index("---\n"):])
        self.assertIn("OUTPUT auditor schema differs", self.run_checker("--catalog", catalog()).stderr)
        auditor.unlink()
        self.assertIn("MISSING auditor expected user definition; effective none", self.run_checker("--catalog", catalog()).stderr)

    def test_39_live_custom_commands(self):
        cwd, run = self.live_fixture()
        home = self.root / "home-temp"
        live = home / ".omp/agent"
        review = live / "commands/review/index.ts"
        self.assertEqual(run().returncode, 0, run().stderr)
        for created, message in [
            (live / "commands/x/index.ts", f"UNSUPPORTED custom command {live / 'commands/x/index.ts'} sha256"),
            (cwd / ".claude/commands/y/index.js", f"UNSUPPORTED custom command {cwd / '.claude/commands/y/index.js'} sha256"),
            (home / ".gemini/commands/z/index.mjs", f"UNSUPPORTED custom command {home / '.gemini/commands/z/index.mjs'} sha256"),
        ]:
            created.parent.mkdir(parents=True)
            created.write_text("export default () => ({ name: 'review', description: 'x', execute: () => 'x' });\n")
            result = run()
            self.assertEqual(result.returncode, 1, created)
            self.assertIn(message, result.stderr)
            shutil.rmtree(created.parent)
        # A dot directory is not discovered; a reviewed copy in a project root is a second /review.
        (live / "commands/.hidden").mkdir()
        (live / "commands/.hidden/index.ts").write_text("export default 1;\n")
        self.assertEqual(run().returncode, 0, run().stderr)
        dup = cwd / ".omp/commands/review/index.ts"
        dup.parent.mkdir(parents=True)
        shutil.copy(REVIEW, dup)
        self.assertIn(f"UNSUPPORTED custom command {dup} duplicates {review}", run().stderr)
        shutil.rmtree(cwd / ".omp/commands")
        review.write_text(review.read_text() + "// edited\n")
        result = run()
        self.assertIn(f"UNSUPPORTED custom command {review} sha256", result.stderr)
        self.assertIn(f"MISSING /review override {review} (the bundled reviewer would run)", result.stderr)
        shutil.rmtree(live / "commands/review")
        result = run()
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"MISSING /review override {review}", result.stderr)
        # A symlinked command dir is skipped by the native loader, so it cannot provide the override.
        outside = self.root / "outside-review"
        outside.mkdir()
        shutil.copy(REVIEW, outside / "index.ts")
        (live / "commands/review").symlink_to(outside)
        result = run()
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"MISSING /review override {review}", result.stderr)

    def test_40_source_custom_commands(self):
        catalog = lambda: self.evidence()
        commands = self.agent / "private_commands"
        (commands / "board.md").write_text("---\ndescription: x\n---\nbody\n")
        self.assertEqual(self.run_checker("--catalog", catalog()).returncode, 0, self.run_checker("--catalog", catalog()).stderr)
        for created, message in [
            (commands / "private_x/index.ts", f"UNSUPPORTED custom command {commands / 'private_x/index.ts'} sha256"),
            (commands / "y/index.ts.tmpl", f"UNSUPPORTED source {commands / 'y/index.ts.tmpl'} (chezmoi template"),
            # chezmoi deploys an external_ dir's children unparsed: external_z/index.ts is command z's module.
            (commands / "external_z/index.ts", f"UNSUPPORTED source {commands / 'external_z'} (chezmoi template"),
        ]:
            created.parent.mkdir(parents=True)
            created.write_text("export default () => ({});\n")
            result = self.run_checker("--catalog", catalog())
            self.assertEqual(result.returncode, 1, created)
            self.assertIn(message, result.stderr)
            shutil.rmtree(created if created.is_dir() else created.parent)
        # Other native command roots the source deploys are scanned too: user roots, and project roots anywhere
        # under the source home. An opaque root or command entry (a symlink payload file) fails closed.
        for module in [self.root / "home/private_dot_codex/commands/evil/index.ts",
                       self.root / "home/hearth/inbox/probe/dot_omp/commands/evil/index.ts"]:
            module.parent.mkdir(parents=True)
            module.write_text("export default () => ({});\n")
            result = self.run_checker("--catalog", catalog())
            self.assertEqual(result.returncode, 1, module)
            self.assertIn(f"UNSUPPORTED custom command {module} sha256", result.stderr)
            shutil.rmtree(module.parents[2])
        for opaque in [self.root / "home/symlink_dot_claude", commands / "symlink_evil"]:
            opaque.write_text("/elsewhere\n")
            result = self.run_checker("--catalog", catalog())
            self.assertEqual(result.returncode, 1, opaque)
            self.assertIn(f"UNSUPPORTED source {opaque} (chezmoi template", result.stderr)
            opaque.unlink()
        shutil.rmtree(commands / "private_review")
        result = self.run_checker("--catalog", catalog())
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"MISSING /review override {commands / 'review/index.ts'}", result.stderr)
        # The local profile has no commands and needs no override.
        local = self.root / "home/private_dot_omp/private_profiles/local/private_agent"
        (local / "private_agents").mkdir(parents=True)
        (local / "private_config.yml").write_text(self.config.read_text())
        result = self.run_checker("--profile", "local", "--catalog", self.evidence(models_file=local / "private_models.yml", profile="local"))
        self.assertNotIn("/review", result.stderr)


if __name__ == "__main__":
    unittest.main()
