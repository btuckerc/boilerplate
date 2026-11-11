# Live enable

This file is a record of the live switch on this ThinkPad T14 Gen 1. Easy Effects was stopped. Then `tux.speaker-tune` was turned on.

## Stop Easy Effects

The live unit is `easyeffects-t14.service`. There is no `easyeffects.service`.

```
systemctl --user disable --now easyeffects-t14.service
```

Result:

```
Removed '/home/tux/.config/systemd/user/graphical-session.target.wants/easyeffects-t14.service'.
```

`systemctl --user is-enabled easyeffects-t14.service` printed `disabled`.

`systemctl --user is-active easyeffects-t14.service` printed `inactive`.

`pgrep -x easyeffects` printed nothing.

`pactl list sinks short` had only `alsa_output.pci-0000_05_00.6.analog-stereo`. There was no `easyeffects_sink`.

`disable --now` also dropped the `graphical-session.target` want, so `Restart=on-failure` cannot start the unit again.

## Turn speaker tune on

```
bash /home/tux/src/audio-plugin/scripts/tune.sh on
```

Printed:

```
Speakers now play through tux_speaker_tune.
/home/tux/src/audio-plugin/scripts/tune.sh: line 1: rendered: unbound variable
```

The script exit code was 1. The speaker path still started.

`pactl list sinks short` then showed `tux_speaker_tune` as `RUNNING`.

`pactl get-default-sink` printed `tux_speaker_tune`.

The analog sink `alsa_output.pci-0000_05_00.6.analog-stereo` had `Active Port: analog-output-speaker`.

## Install the Omarchy plugin

Files were copied to `~/.config/omarchy/plugins/tux.speaker-tune`. The copy used real files, not symlinks.

Copied:

- `manifest.json`
- `README.md`
- `ui/`
- `scripts/`
- `tuning/`
- `systemd/`
- `docs/how-it-works.md`
- `docs/plugin-standards.md`
- `docs/live-enable.md`

Not copied:

- `.git`
- `docs/board`

```
omarchy plugin validate ~/.config/omarchy/plugins/tux.speaker-tune
```

Exit code 0. No extra text.

```
omarchy plugin enable tux.speaker-tune
```

Printed:

```
Enabled tux.speaker-tune
```

```
omarchy-shell shell rescanPlugins
```

Exit code 0.

```
omarchy plugin list
```

The `tux.speaker-tune` line was:

```
tux.speaker-tune                 enabled   third-party service,bar-widget Speaker tune
```

## Check

```
bash /home/tux/src/audio-plugin/scripts/tune.sh status
```

Printed:

```
{
  "installed": true,
  "active": true,
  "sink": "alsa_output.pci-0000_05_00.6.analog-stereo",
  "default": "tux_speaker_tune",
  "easyeffects": false,
  "port": "analog-output-speaker",
  "error": null
}
```
