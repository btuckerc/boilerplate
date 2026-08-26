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

-- Restore outer gap and border when two or more tiled windows are visible.
-- Do not set rounding in a window rule. That value sticks on the client
-- after the workspace selector stops matching. Chromium on a one-tile
-- workspace kept rounding 6; kitty on never-multi workspaces stayed 0.
-- decoration.rounding stays 0 so the first map is already square.
local single = "w[tv1]s[false]"
local multi = "w[tv2-99]s[false]"
hl.workspace_rule({
	workspace = single,
	gaps_out = 0,
	border_size = 0,
})
hl.workspace_rule({
	workspace = multi,
	gaps_out = 4,
	gaps_in = 2,
	border_size = 2,
})

-- Make windows carrying Omarchy's default-opacity tag fully opaque.
o.window({ tag = "default-opacity" }, {
	opacity = "1.0 override 1.0 override",
})
