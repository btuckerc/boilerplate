#!/bin/bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
plugin_root="$(cd "$script_dir/.." && pwd)"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"

tuning_conf="$plugin_root/tuning/tuning.conf"
filter_source="$plugin_root/tuning/filter-chain.conf"
host_source="$plugin_root/tuning/host.conf"
unit_source="$plugin_root/systemd/tux-speaker-tune.service"

host_config_name=tux-speaker-tune.conf
host_config="$config_home/pipewire/$host_config_name"
fragment="$config_home/pipewire/$host_config_name.d/90-tuning.conf"
unit_name=tux-speaker-tune.service
unit="$config_home/systemd/user/$unit_name"

sink_name=tux_speaker_tune
lv2_compressor=/usr/lib/lv2/lsp-plugins.lv2/compressor_stereo.ttl
lv2_limiter=/usr/lib/lv2/lsp-plugins.lv2/limiter_stereo.ttl
dmi_version_file=/sys/class/dmi/id/product_version

action="${1:-}"

load_tuning() {
  unset description match_dmi sink_pattern
  # shellcheck disable=SC1090
  source "$tuning_conf"
}

sink_matching() {
  pactl list sinks short 2>/dev/null | awk -v p="$1" '$2 ~ p {print $2; exit}'
}

hardware_sink() {
  local found
  [[ -n ${sink_pattern:-} ]] || return 1
  found="$(sink_matching "$sink_pattern")"
  [[ -n $found ]] || return 1
  printf '%s\n' "$found"
}

tuning_present() {
  pactl list sinks short 2>/dev/null | awk '{print $2}' | grep -x "$sink_name" >/dev/null
}

active_port() {
  local sink="$1"
  [[ -n $sink ]] || return 1
  pactl list sinks 2>/dev/null | awk -v s="$sink" '
    $1 == "Name:" && $2 == s {grab = 1; next}
    grab && $1 == "Name:" {exit}
    grab && $1 == "Active" && $2 == "Port:" {print $3; exit}
  '
}

easyeffects_running() {
  pactl list sinks short 2>/dev/null | awk '{print $2}' | grep -x easyeffects_sink >/dev/null ||
    pgrep -u "$(id -u)" -x easyeffects >/dev/null 2>&1 ||
    systemctl --user is-active --quiet easyeffects-t14.service ||
    systemctl --user is-active --quiet easyeffects.service
}

dmi_matches() {
  local have want
  [[ -r $dmi_version_file ]] || return 1
  have="$(<"$dmi_version_file")"
  [[ -n $have ]] || return 1
  for want in "$@"; do
    [[ ${have,,} == "${want,,}" ]] && return 0
  done
  return 1
}

lv2_present() {
  [[ -r $lv2_compressor && -r $lv2_limiter ]]
}

app_streams() {
  pactl list sink-inputs 2>/dev/null | awk '
    /^Sink Input #/ {id = substr($3, 2)}
    /application\.name = / {
      app = $0
      sub(/.*application\.name = "/, "", app)
      sub(/"$/, "", app)
      if (app != "EasyEffects") print id
    }'
}

move_apps_to() {
  local target="$1" id
  for id in $(app_streams); do
    pactl move-sink-input "$id" "$target" 2>/dev/null || true
  done
}

installed_files() {
  [[ -r $host_config && -r $fragment && -r $unit ]]
}

cmd_check() {
  [[ -r $tuning_conf ]] || {
    echo "missing $tuning_conf" >&2
    exit 1
  }
  [[ -r $filter_source ]] || {
    echo "missing $filter_source" >&2
    exit 1
  }
  [[ -r $host_source ]] || {
    echo "missing $host_source" >&2
    exit 1
  }
  [[ -r $unit_source ]] || {
    echo "missing $unit_source" >&2
    exit 1
  }

  load_tuning
  [[ -n ${match_dmi:-} ]] || {
    echo "tuning.conf has no match_dmi" >&2
    exit 1
  }
  [[ -n ${sink_pattern:-} ]] || {
    echo "tuning.conf has no sink_pattern" >&2
    exit 1
  }

  dmi_matches "${match_dmi[@]}" || {
    echo "DMI product_version is not ThinkPad T14 Gen 1" >&2
    exit 1
  }

  hardware_sink >/dev/null || {
    echo "no sink matching $sink_pattern" >&2
    exit 1
  }

  lv2_present || {
    echo "lsp-plugins-lv2 compressor_stereo and limiter_stereo are required" >&2
    exit 1
  }
}

cmd_status() {
  local installed=false active=false sink="" default_sink="" port="" err=""

  if installed_files; then
    installed=true
  fi

  if systemctl --user is-active --quiet "$unit_name" 2>/dev/null || tuning_present; then
    active=true
  fi

  if [[ -r $tuning_conf ]]; then
    load_tuning || err="could not read tuning.conf"
  else
    err="missing tuning.conf"
  fi

  if [[ -z $err ]]; then
    sink="$(hardware_sink || true)"
    port="$(active_port "$sink" || true)"
  fi

  default_sink="$(pactl get-default-sink 2>/dev/null || true)"

  jq -n \
    --argjson installed "$installed" \
    --argjson active "$active" \
    --arg sink "$sink" \
    --arg default "$default_sink" \
    --arg port "$port" \
    --arg error "$err" \
    '{
      installed: $installed,
      active: $active,
      sink: $sink,
      default: $default,
      port: $port,
      error: (if $error == "" then null else $error end)
    }'
}

remove_install() {
  systemctl --user disable --now "$unit_name" >/dev/null 2>&1 || true
  rm -f "$fragment" "$host_config" "$unit"
  rmdir "$config_home/pipewire/$host_config_name.d" 2>/dev/null || true
  systemctl --user daemon-reload >/dev/null 2>&1 || true
}

cmd_on() {
  load_tuning

  local speaker_sink
  speaker_sink="$(hardware_sink || true)"
  [[ -n $speaker_sink ]] || {
    echo "no sink matching $sink_pattern" >&2
    exit 1
  }

  if easyeffects_running; then
    echo "Easy Effects is running. Stop it before turning this tuning on." >&2
    exit 1
  fi

  local port
  port="$(active_port "$speaker_sink" || true)"
  if [[ $port == analog-output-headphones ]]; then
    echo "Active port is analog-output-headphones. Tuning stays off." >&2
    exit 1
  fi

  lv2_present || {
    echo "lsp-plugins-lv2 compressor_stereo and limiter_stereo are required" >&2
    exit 1
  }

  local rendered
  rendered="$(mktemp)"
  trap "rm -f -- $(printf '%q' "$rendered")" EXIT
  sed "s|@SPEAKER_SINK@|$speaker_sink|g" "$filter_source" >"$rendered"

  install -Dm644 "$host_source" "$host_config"
  install -Dm644 "$rendered" "$fragment"
  install -Dm644 "$unit_source" "$unit"
  systemctl --user daemon-reload >/dev/null 2>&1
  systemctl --user enable "$unit_name" >/dev/null 2>&1
  systemctl --user restart "$unit_name" >/dev/null 2>&1

  local _
  for _ in {1..40}; do
    tuning_present && break
    sleep 0.25
  done
  if ! tuning_present; then
    remove_install
    echo "Tuning sink never appeared, so it was removed. Audio is untouched." >&2
    echo "Check: systemctl --user status $unit_name" >&2
    exit 1
  fi

  pactl set-default-sink "$sink_name" >/dev/null 2>&1
  move_apps_to "$sink_name"
  echo "Speakers now play through tux_speaker_tune."
}

cmd_off() {
  if [[ ! -r $fragment && ! -r $host_config && ! -r $unit ]]; then
    echo "No speaker tuning installed."
    exit 0
  fi

  local speakers=""
  if [[ -r $tuning_conf ]]; then
    load_tuning
    speakers="$(hardware_sink || true)"
  fi

  remove_install

  local _
  for _ in {1..20}; do
    tuning_present || break
    sleep 0.25
  done

  if [[ -n $speakers ]]; then
    pactl set-default-sink "$speakers" >/dev/null 2>&1 || true
    move_apps_to "$speakers"
  fi
  echo "Speaker tuning removed."
}

case "$action" in
  check)
    cmd_check
    ;;
  status)
    cmd_status
    ;;
  on)
    cmd_on
    ;;
  off)
    cmd_off
    ;;
  *)
    echo "Usage: $0 <check|status|on|off>" >&2
    exit 2
    ;;
esac
