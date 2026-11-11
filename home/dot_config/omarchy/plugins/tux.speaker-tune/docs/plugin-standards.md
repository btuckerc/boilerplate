# Plugin standards

## What an Omarchy plugin is

An Omarchy plugin is extra code that Omarchy can load.

First-party plugins ship with Omarchy. Their ids start with `omarchy.`.

Third-party plugins live in `~/.config/omarchy/plugins/<plugin-id>/`.

This repo is a third-party plugin. The id is `tux.speaker-tune`.

A plugin must not use the `omarchy.*` id prefix. That prefix is reserved.

## Required manifest.json fields

The file `manifest.json` must sit at the plugin root.

Omarchy checks these fields:

- `schemaVersion`. Must be the number 1.
- `id`. This plugin uses `tux.speaker-tune`.
- `name`. A short display name.
- `version`. A version string.
- `kinds`. A list of what the plugin provides.
- `entryPoints`. Paths to the files Omarchy loads for those kinds.

The id must start with a letter or a digit. After that it may use letters, digits, dots, underscores, or dashes. It must not contain `..`.

It must not start with `omarchy.`.

## Kinds this repo uses

This plugin uses two kinds.

`service`. Omarchy keeps a background file loaded. The file is `ui/Service.qml`.

`bar-widget`. Omarchy can put a control on the bar. The file is `ui/BarWidget.qml`.

The service runs `scripts/tune.sh`. It does not change sound by itself.

## Commands

`omarchy plugin validate <plugin-folder>`

This command checks `manifest.json`. It checks required fields, kinds, entry point files, and that the id is not reserved. It does not start sound.

`omarchy plugin add <git-url>`

This command copies the plugin from git into `~/.config/omarchy/plugins/`. It runs validate first. It leaves the plugin off unless you ask to enable it.

`omarchy plugin enable tux.speaker-tune`

This command turns the plugin on in Omarchy. It loads the service and can place the bar control.

`omarchy plugin list`

This command prints known plugins. It shows id, on or off, first-party or third-party, kinds, and name.

## What first-party audio does

The first-party plugin `omarchy.audio` only changes volume and picks outputs.

It is not speaker tone control. It is not this plugin.

Official Omarchy audio tuning has no file for ThinkPad T14 Gen 1. The only shipped tuning folder is `dell-xps-2026`.

This plugin adds speaker controls for this laptop. It still must keep the `tux.speaker-tune` id.
