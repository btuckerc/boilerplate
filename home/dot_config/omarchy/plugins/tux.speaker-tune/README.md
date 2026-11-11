# T14 speaker tune

This repo is an Omarchy plugin. A plugin is extra code that Omarchy can load.

The plugin id is `tux.speaker-tune`.

It turns a speaker sound path on and off for a Lenovo ThinkPad T14 Gen 1. The path runs in PipeWire, which is the sound server on this laptop.

## The problem

Omarchy has no shipped speaker tuning for this ThinkPad T14 Gen 1.

The first-party plugin named `omarchy.audio` only changes volume and picks outputs. It does not change speaker tone.

The built-in speakers share one sink with the headphone jack. A sink is a place apps send sound. That sink is `alsa_output.pci-0000_05_00.6.analog-stereo`. The chip is Realtek ALC257.

Easy Effects is a separate app. It is not this plugin. Its speaker preset uses a maximizer that changes loudness a lot. That is why volume jumps now.

This plugin uses its own filter set. A filter is a step that changes the sound. This first filter set is not a mic measurement.

## Install

Copy this folder to `~/.config/omarchy/plugins/tux.speaker-tune`.

Or add it from git:

```
omarchy plugin add <git-url>
```

Then check the plugin folder:

```
omarchy plugin validate .
```

If you copied the files, run that command on the copy.

Then load the plugin in Omarchy:

```
omarchy plugin enable tux.speaker-tune
```

That loads the bar control. It does not start the speaker path while Easy Effects is running.

## Use it from the Omarchy audio panel

Once installed with `scripts/tune.sh on`, the tuning is a normal output
device. Open the stock Audio panel in the bar and pick an output:

- **Tuned Speakers**: speakers through this filter set.
- **ALC257 Analog**: the raw speakers and headphone jack, no tuning.

The host service stays enabled, so the row survives reboots. When nothing
plays through it, the tuned sink suspends.

Nothing in Omarchy's own files is changed, so `omarchy update` leaves this
alone. The output node is named `omarchy_speaker_tuning_tux_output` on
purpose: the stock panel hides playback streams whose name starts with
`omarchy_speaker_tuning`, so the filter's own output stays out of the
SOURCES list. If an update drops that rule, the only effect is that row
showing up again.

The bar widget in `ui/` is optional. It is not in the bar layout by default.

## Turn the speaker path on later

Stop Easy Effects first. This plugin will not start while Easy Effects is running.

Then run:

```
scripts/tune.sh on
```

You can also use the bar control after Easy Effects is stopped.

## Turn the speaker path off

```
scripts/tune.sh off
```

That stops the extra sound path. Apps go back to the laptop analog speakers.

## Easy Effects

Do not start this speaker path while Easy Effects is running.

Do not run both at once. Both would change the same sound.

Do not copy the Easy Effects preset into this plugin.
