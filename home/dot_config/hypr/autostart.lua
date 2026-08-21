-- Portable startup overrides only. Omarchy owns the shell and core services.

-- Prefer user wrappers such as omarchy-launch-shell over packaged binaries.
-- Omarchy's envs.lua prepends $OMARCHY_PATH/bin after UWSM, which would
-- otherwise hide ~/.local/bin. Keep that bin dir; just put ~/.local/bin first.
do
	local home = os.getenv("HOME") or ""
	local local_bin = home .. "/.local/bin"
	local omarchy_bin = (os.getenv("OMARCHY_PATH") or "/usr/share/omarchy") .. "/bin"
	local kept = {}
	for entry in (os.getenv("PATH") or "/usr/local/bin:/usr/bin"):gmatch("[^:]+") do
		if entry ~= local_bin and entry ~= omarchy_bin then
			table.insert(kept, entry)
		end
	end
	table.insert(kept, 1, omarchy_bin)
	table.insert(kept, 1, local_bin)
	hl.env("PATH", table.concat(kept, ":"))
end

-- SDDM autologin should never leave the workstation sitting unlocked.
o.exec_on_start("sleep 2 && omarchy-system-lock")
