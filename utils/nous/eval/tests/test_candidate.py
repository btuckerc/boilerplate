import pytest

from nevl.candidate import CandidateError, derive_preset, incumbent, load, manifest
from nevl.runner import parse_overrides

PRESET = """version = 1
[*]
device = Vulkan0
ctx-size = 16384

; comment
[old]
model = /srv/models/old.gguf
ctx-size = 8192

[prod]
model = /srv/models/prod.gguf
ctx-size = 163840
spec-draft-n-max = 5
load-on-startup = true
"""


def test_derive_preset_keeps_global_and_production_section_only():
    text, section = derive_preset(PRESET, None, {"spec-draft-n-max": 4, "ubatch-size": 2048})
    assert section == "prod"
    assert "[old]" not in text and "old.gguf" not in text
    assert "[*]" in text and "device = Vulkan0" in text and text.startswith("version = 1")
    prod = text.split("[prod]")[1]
    assert "spec-draft-n-max = 4" in prod and "spec-draft-n-max = 5" not in prod
    assert "ubatch-size = 2048" in prod and "ctx-size = 163840" in prod


def test_derive_preset_named_section_and_unknown_section():
    assert derive_preset(PRESET, "old", {})[1] == "old"
    with pytest.raises(CandidateError):
        derive_preset(PRESET, "missing", {})
    with pytest.raises(CandidateError):
        derive_preset(PRESET.replace("load-on-startup = true", ""), None, {})


def test_incumbent_is_the_spec_production_loaded(tmp_path):
    """The recorded spec while llama.service runs, even after /etc changed; the installed one
    when nothing runs, since that is what starts next (ledger M60)."""
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    (rootfs / ".nous-serve-image.json").write_text('{"env": [], "id": "sha", "image": "ref"}')
    spec, record = tmp_path / "production.toml", tmp_path / "record.toml"

    def write(path, model):
        path.write_text(f'rootfs = "{rootfs}"\nserved_model_name = "{model}"\nhome = "{tmp_path}"\n'
                        f'args = ["--model", "/models/qwen"]\n[mounts]\n"/models" = "{tmp_path}"\n')
    write(spec, "installed")
    show = (f"ExecStart={{ path=/usr/local/bin/nous-serve ; argv[]=/usr/local/bin/nous-serve run {spec} "
            f"--port 8080 --record {record} ; ignore_errors=no ; start_time=[n/a] }}")
    c = incumbent(show)
    assert c["kind"] == "serve" and c["label"] == "incumbent"
    assert c["model"] == "installed" and c["spec"]["rootfs"] == str(rootfs)
    write(record, "running")
    assert incumbent(show)["model"] == "running"
    assert incumbent(show.replace(f" --record {record}", ""))["model"] == "installed"




def test_incumbent_rejects_non_nous_serve_execstart():
    with pytest.raises(CandidateError, match="llama.service"):
        incumbent("ExecStart={ path=/opt/llama-server ; argv[]=/opt/llama-server ; start_time=x }")
def test_command_candidates_take_overrides_in_their_argv(tmp_path):
    """A vLLM winner must be tunable one factor at a time too, with its real knob syntax
    (council S-04, O-08, A-04)."""
    path = tmp_path / "v.toml"
    path.write_text('kind = "command"\nlabel = "v"\nmodel = "m"\nstart = ["vllm", "serve", "-e", "RADIANCE_KV=8",'
                    ' "--speculative-config.num_speculative_tokens", "7", "--enable-prefix-caching",'
                    ' "--enable-prompt-tokens-details", "--max-num-seqs", "8"]\n')
    tuned = load(path, parse_overrides(["RADIANCE_KV=4", "speculative-config.num_speculative_tokens=5"]))
    assert tuned["start"] == ["vllm", "serve", "-e", "RADIANCE_KV=4",
                              "--speculative-config.num_speculative_tokens", "5", "--enable-prefix-caching",
                              "--enable-prompt-tokens-details", "--max-num-seqs", "8"]
    assert tuned["label"] != load(path)["label"]
    switches = load(path, parse_overrides(["enable-prefix-caching=false", "enforce-eager=true", "max-num-batched-tokens=4096"]))
    assert switches["start"] == ["vllm", "serve", "-e", "RADIANCE_KV=8",
                                 "--speculative-config.num_speculative_tokens", "7",
                                 "--enable-prompt-tokens-details", "--max-num-seqs", "8",
                                 "--enforce-eager", "--max-num-batched-tokens", "4096"]
    with pytest.raises(CandidateError, match="RADIANCE_CACTUS_DELTA"):  # never appended as a flag
        load(path, parse_overrides(["RADIANCE_CACTUS_DELTA=0"]))


def test_serve_candidates_check_encoder_reservation(tmp_path):
    path, _ = serve_fixture(tmp_path)
    spec = tmp_path / "serve.toml"
    original = spec.read_text()
    spec.write_text(original.replace('args = [', 'args = ["--skip-mm-profiling", '))
    with pytest.raises(CandidateError, match="vision encoder"):
        load(path)
    spec.write_text(original.replace('args = [', 'args = ["--skip-mm-profiling", "--limit-mm-per-prompt.image", "0", '))
    assert load(path)["kind"] == "serve"
    spec.write_text(original.replace('args = [', 'args = ["--skip-mm-profiling", "--limit-mm-per-prompt.image", "2", '))
    assert "--skip-mm-profiling" not in load(path, {"skip-mm-profiling": "false"})["spec"]["args"]


def test_set_overrides_get_their_own_label(tmp_path):
    """Two settings of one candidate file must stay apart in a run and its comparisons."""
    (tmp_path / "models.ini").write_text(PRESET)
    path = tmp_path / "tip.toml"
    path.write_text(f'engine = "/bin/true"\npreset = "{tmp_path / "models.ini"}"\n')
    plain, tuned = load(path), load(path, {"ubatch-size": "2048", "spec-draft-n-max": "4"})
    assert plain["label"] == "tip"
    assert tuned["label"] == "tip.spec-draft-n-max-4.ubatch-size-2048"
    assert "ubatch-size = 2048" in tuned["preset_text"]


def test_labels_must_be_path_safe(tmp_path):
    path = tmp_path / "x.toml"
    path.write_text('kind = "command"\nlabel = "a/b"\nmodel = "m"\nstart = ["x"]\n')
    with pytest.raises(CandidateError):
        load(path)


def test_an_unchanged_engine_has_the_same_manifest_every_time(tmp_path):
    """llama-server --version prints a timestamped log line; the identity must ignore it,
    or the last ABBA block of every run fails as 'candidate changed' (ledger M41)."""
    engine = tmp_path / "bin" / "llama-server"
    engine.parent.mkdir()
    engine.write_text('#!/bin/sh\necho "0.00.000.$(date +%N) I srv  llama_server: initializing ..." >&2\n'
                      'echo "version: 1 (build 1, commit abc)" >&2\n')
    engine.chmod(0o755)
    (tmp_path / "prod.gguf").write_bytes(b"weights")
    (tmp_path / "models.ini").write_text(PRESET.replace("/srv/models/prod.gguf", str(tmp_path / "prod.gguf")))
    path = tmp_path / "c.toml"
    path.write_text(f'engine = "{engine}"\npreset = "{tmp_path / "models.ini"}"\n')
    candidate = load(path)
    first = manifest(candidate)
    assert manifest(candidate) == first and "commit abc" in first["engine_version"]


def serve_fixture(tmp_path):
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    (rootfs / ".nous-serve-image.json").write_text(
        '{"id":"image-id","image":"ghcr.io/slybase/vllm-sly-radiance:1.9.1-rocm10.1",'
        '"env":["FROM_IMAGE=base"],"entrypoint":["vllm","serve"]}')
    models = tmp_path / "models"
    (models / "target").mkdir(parents=True)
    (models / "draft").mkdir()
    spec = tmp_path / "serve.toml"
    spec.write_text(f'rootfs = "{rootfs}"\nserved_model_name = "target"\nhome = "{tmp_path}"\n'
                    'args = ["--model", "/models/target", "--speculative-config.model", "/models/draft"]\n'
                    f'[mounts]\n"/models" = "{models}"\n[env]\nEXISTING = "before"\n')
    path = tmp_path / "candidate.toml"
    path.write_text(f'kind = "serve"\nspec = "{spec}"\n')
    return path, rootfs
def test_serve_home_override_and_run_port(tmp_path):
    from nevl.server import Server
    path, _ = serve_fixture(tmp_path)
    home = tmp_path / "release-home"
    path.write_text(path.read_text() + f'\n[overrides]\nhome = "{home}"\n')
    candidate = load(path)
    server = Server(candidate, tmp_path / "run", 18738)
    assert candidate["spec"]["home"] == str(home)
    assert server.base_url == "http://127.0.0.1:18738"
    assert server.argv()[-1] == "18738"
    assert "--port" in server.argv()


def test_serve_overrides_args_env_and_rootfs_and_rejects_unknown_env(tmp_path):
    path, _ = serve_fixture(tmp_path)
    alt = tmp_path / "alt-root"
    alt.mkdir()
    (alt / ".nous-serve-image.json").write_text('{"env":["OTHER=ok"],"id":"alt","image":"alt"}')
    path.write_text(path.read_text() +
                    f'\n[overrides]\nmodel = "/models/target"\nEXISTING = "after"\nFROM_IMAGE = "changed"\n'
                    f'rootfs = "{alt}"\nserved_model_name = "canary"\n')
    c = load(path)
    assert c["model"] == "canary" and c["spec"]["rootfs"] == str(alt)
    assert c["spec"]["env"] == {"EXISTING": "after", "FROM_IMAGE": "changed"}
    assert c["spec"]["args"][:2] == ["--model", "/models/target"]
    path.write_text(path.read_text() + 'NOT_PRESENT = "x"\n')
    with pytest.raises(CandidateError, match="absent from spec and image"):
        load(path)


def test_serve_manifest_maps_argument_paths_through_mounts(tmp_path, monkeypatch):
    path, _ = serve_fixture(tmp_path)
    c = load(path)
    monkeypatch.setattr("nevl.candidate._fingerprint", lambda p, whole=False: {"path": str(p)})
    monkeypatch.setattr("nevl.candidate._serve_module",
                        lambda: type("Serve", (), {"identity": staticmethod(lambda spec: {"image": "id"})}))
    out = manifest(c)
    assert out["model_files"] == [{"path": str(tmp_path / "models/draft")},
                                  {"path": str(tmp_path / "models/target")}]
