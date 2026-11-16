# TP-Link Archer access points (BE9700 / BE600)

Used at: clt `be9700` (Archer BE9700 v1.0, 10.77.77.111) and elsie `be9700` (reports
Archer BE600 v1.0, 10.77.78.111). Both in AP mode.

## Access

- Passwords: elsie `op-secret field be9700-elsie password`; clt
  `~/.local/share/decent-angl/secrets/be9700.env` (`TPLINK_PASSWORD=`, used by `netwatch`,
  not in 1Password yet).
- Python library `tplinkrouterc6u` (PyPI). Install it in a throwaway venv and run the
  script with `python -I`:

```python
from tplinkrouterc6u import TplinkRouterProvider
r = TplinkRouterProvider.get_client("http://10.77.78.111", password)   # class TplinkRouter
r.authorize()
r.get_firmware(); r.get_status()            # model/firmware; clients with band and RSSI
r.request("admin/wireless?form=wireless_5g", "operation=read")
r.logout()
```

- Readable forms: `admin/wireless?form=wireless_2g|wireless_5g|wireless_6g|smart_connect|
  ofdma_mimo|twt|region`, `admin/system?form=sysmode`, `admin/firmware?form=upgrade`,
  `admin/cloud_account?form=check_upgrade` (`update_number` > 0 means an update is offered).
  Wireless forms include the PSK: redact `psk*`, `*key*`, `password` before printing.
- elsie is reached from nous through a tunnel via the Mac mini (`ssh -L 18445:10.77.78.111:80 mini`).

## Writes

Untested. The web UI re-posts whole wireless forms, including the PSK, so a partial write
can blank settings and take the site's Wi-Fi down. Before the first write: save the full
read (0600, outside Git), test on a harmless form, read back, and have the user near the AP.
Radio changes restart the radios and kick clients (`wifi.md`).

## Recommended settings

AP mode; one SSID on 2.4+5 GHz (Smart Connect on, or off with identical names), WPA2/WPA3
mixed (`psk_sae`); 2.4 GHz 20 MHz; 5 GHz 80 MHz on a non-DFS block (149 when another AP has
36); fixed channels on a multi-AP site; airtime fairness on; MLO off; WMM on; AP isolation
off; beacon 100, DTIM 1. Per-site values: `wifi.md`.

## Firmware

`update_number` reports an offered update on both sites (2026-11-16, not installed). An
update reboots the AP (about 3 minutes without Wi-Fi). For clt, `netwatch/ap_upgrade.py`
waits for a quiet LAN and installs TP-Link's online update, then checks clients rejoined.

## Gotchas

- In Router mode with its uplink in a LAN port it runs a second DHCP server (192.168.0.x).
  Check with a DHCPDISCOVER probe, not leases.
- The elsie unit's DHCP hostname is `ArcherBE600` (its second MAC `...f4:5c`).
