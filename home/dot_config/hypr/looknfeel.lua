-- Compact, distraction-free overrides layered after Omarchy defaults.
hl.config({
	general = {
		gaps_in = 2,
		gaps_out = 4,
	},
	decoration = {
		rounding = 6,
		shadow = { enabled = false },
		blur = { enabled = false },
	},
	animations = {
		enabled = false,
	},
	misc = {
		focus_on_activate = false,
	},
})

-- Smart gaps for one tiled window, one grouped tile, and fullscreen workspaces.
for _, selector in ipairs({ "w[t1]s[false]", "w[tg1]s[false]", "f[1]s[false]" }) do
	hl.workspace_rule({
		workspace = selector,
		gaps_out = 0,
		gaps_in = 0,
		border_size = 0,
	})
end

-- Make windows carrying Omarchy's default-opacity tag fully opaque.
o.window({ tag = "default-opacity" }, {
	opacity = "1.0 override 1.0 override",
})
