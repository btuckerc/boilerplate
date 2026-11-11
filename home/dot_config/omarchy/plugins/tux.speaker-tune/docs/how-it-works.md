# How it works

## The sound path

An app makes sound.

PipeWire takes that sound. PipeWire is the sound server.

When this path is on, PipeWire sends the sound to a sink named `tux_speaker_tune`. A sink is a place apps send sound.

That sink runs a filter chain. A filter is a step that changes the sound.

The last step sends the sound out as `tux_speaker_tune_output`.

That output is pinned to the laptop analog speakers. The hardware sink name is `alsa_output.pci-0000_05_00.6.analog-stereo`.

The speakers then play the sound.

A user unit named `tux-speaker-tune.service` starts a PipeWire client. The client reads `tux-speaker-tune.conf`. The path can start and stop without restarting every app.

## Why volume jumps now

Easy Effects is a separate app.

If Easy Effects is running, its speaker preset uses a maximizer. The maximizer keeps raising quiet parts so the sound stays near a set loudness.

Loudness then changes a lot as the music changes. That is why volume jumps now.

This plugin will not start while Easy Effects is running.

This plugin does not use that maximizer.

This plugin uses a compressor, then a limiter. A compressor turns down loud parts. A limiter stops peaks from going past a set loudness.

The limiter sets `alr` to 0 and `boost` to 0. Those two switches stay off so the limiter does not raise the level when the song gets quieter.

## Each filter step

The left and right sides use the same steps.

1. Highpass at 80 Hz, Q 0.7. This filter removes sound below 80 Hz. These small speakers cannot play that low band well. Q sets how wide the change is.
2. Lowshelf at 180 Hz, Q 0.7, gain +2.5. This filter raises low notes a little.
3. Peaking at 3500 Hz, Q 1.2, gain -3.5. This filter cuts a sharp band near 3500 Hz.
4. Peaking at 6000 Hz, Q 1.4, gain -2.5. This filter cuts a sharp band near 6000 Hz.
5. Highshelf at 8000 Hz, Q 0.7, gain -2.0. This filter lowers the highest notes a little.
6. LSP `compressor_stereo`. This compressor turns down loud parts. The ratio is about 2. Attack is about 20 ms. Release is about 200 ms. Threshold is about -18 dB.
7. LSP `limiter_stereo`. This limiter stops leftover peaks. `alr` is 0. `boost` is 0. Threshold `th` is about 0.891. Input gain `g_in` is about 0.7.

## Headphones must skip this path

Speakers and headphones are two ports on the same analog sink.

These filter numbers are for the built-in speakers only.

Headphones should get the sound with no speaker steps. If this path stayed on, the same cuts and boosts would change headphone sound the wrong way.

`scripts/tune.sh on` refuses to start if the active port is headphones.

The output stream is pinned to the speaker sink. It does not follow a headphone switch.

## This is not a mic measurement

This first filter set is not a mic measurement.

There was no calibrated microphone. The numbers are a first voicing for this ThinkPad T14 Gen 1.

Omarchy has no shipped tuning file for this laptop. The only shipped Omarchy tuning folder is `dell-xps-2026`.

These numbers were not measured with a microphone.
