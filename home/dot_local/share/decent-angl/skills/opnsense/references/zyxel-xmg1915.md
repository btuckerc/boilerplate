# Zyxel XMG1915-10EP switch

Used at: elsie (10.77.78.112, ports in `elsie.md`). 8x 2.5G PoE+, 2x 10G SFP+, ZyNOS V4.80.

## Access

- Password: `op-secret field zyxel-<site> password`, user `admin`. Hand it to tools through
  an askpass helper or a variable; never print it or put it in argv.
- Enabled services: SSH 22, HTTPS 443, ICMP. Telnet, FTP, HTTP and SNMP are off.
- From nous the site LAN is reached through the Mac mini until the site router is on
  Tailscale (`ssh -J mini`, or `ssh -L <port>:10.77.78.112:443 mini`).

## Read (SSH CLI)

The CLI only shows and diagnoses: there is no `configure`. Commands need a pause before the
next one or the output is cut:

```sh
askpass=$(mktemp); printf '#!/bin/sh\nexec op-secret field zyxel-elsie password\n' >"$askpass"; chmod 700 "$askpass"
{ for c in 'show running-config' 'show interfaces 1'; do echo "$c"; sleep 2.5; done; echo exit; } |
  SSH_ASKPASS=$askpass SSH_ASKPASS_REQUIRE=force DISPLAY=:0 setsid -w ssh -tt \
  -o PreferredAuthentications=password -o PubkeyAuthentication=no -J mini admin@10.77.78.112 |
  tr -d '\r' | sed 's/7\{2,\}//g'
rm -f "$askpass"
```

Useful: `show running-config` (non-defaults only), `show interfaces <n>` (link, CRC, pause,
collisions), `show interfaces config 1-10` (flow control, speed), `show mac address-table all`
(which device is on which port), `show green-ethernet eee`, `show loopguard`,
`show service-control`, `show system-information`, `cable-diagnostics` (drops the link).

## Write (HTTPS forms)

1. `POST /Forms/login_1` with `rpAuthForm_Ipt_UserName`, `rpAuthForm_Ipt_Password`. The session
   is bound to the client IP (no cookie).
2. `GET /rp<Page>.html`, copy every field of its form, change yours, `POST /Forms/rp<Page>_1`.
   Unchecked checkboxes are simply omitted. Pages that call `applyBtn()` also need
   `rp<Page>_HidBtn_NumID=1`.
3. Save: `POST /Forms/rpSaveCfg_1` with `rpSaveCfg_HidBtn_SaveConfig=1` (config 1 is the boot
   config). Unsaved changes are lost at reboot.

- Changing service-control ends the web session: log in again.
- Do not write `rpPort`: it re-posts every port's speed and active flag, and a wrong value
  disables a port.
- Verify every write over SSH (`show running-config`) and with a ping across the switch.

## Recommended settings

Flow control off, EEE off, auto power down off (all defaults here), loop guard on every port,
RSTP off unless a second switch is added, telnet/FTP/HTTP/SNMP off. Firmware: Zyxel V4.80
patches (`rpFwUpgrade.html`); an upgrade reboots the switch and drops the whole site.
