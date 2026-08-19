-- Portable startup overrides only. Omarchy owns the shell and core services.

-- SDDM autologin should never leave the workstation sitting unlocked.
o.exec_on_start("sleep 2 && omarchy-system-lock")
