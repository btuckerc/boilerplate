-- Compact, distraction-free overrides layered after Omarchy defaults.
-- Single-window first paint must already be compact. Selector rules that
-- zero gaps after map run too late on a cold workspace visit; Super+Space
-- only looked like a fix because it forced a later layout pass.
hl.config({
	general = {
		gaps_in = 2,
		gaps_out = 0,
		border_size = 0,
	},
	decoration = {
		rounding = 0,
		shadow = { enabled = false },
		blur = { enabled = false },
	},
	animations = {
		enabled = false,
	},
	misc = {
		focus_on_activate = false,
	},
	debug = {
		-- First visit damages the new window only. The strip between the bar
		-- exclusive zone and that window stays stale until a later full
		-- composite (Super+Space, screencopy). Full damage includes the strip
		-- on the first frame. Scale and bar size stay put.
		damage_tracking = 0,
	},
})

-- Restore outer gap and chrome only when two or more tiled windows are visible.
-- Opening a second window is itself a layout event, so this path is reliable.
local multi = "w[tv2-99]s[false]"
hl.workspace_rule({
	workspace = multi,
	gaps_out = 4,
	gaps_in = 2,
	border_size = 2,
})
hl.window_rule({
	name = "multi-window-chrome",
	match = { float = false, workspace = multi },
	border_size = 2,
	rounding = 6,
})

-- Make windows carrying Omarchy's default-opacity tag fully opaque.
o.window({ tag = "default-opacity" }, {
	opacity = "1.0 override 1.0 override",
})
