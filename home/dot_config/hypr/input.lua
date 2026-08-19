-- Portable keyboard and pointer preferences.
hl.config({
	input = {
		kb_layout = "us",
		kb_options = "caps:ctrl_modifier",
		repeat_rate = 55,
		repeat_delay = 300,
		numlock_by_default = true,
		touchpad = {
			natural_scroll = true,
			clickfinger_behavior = true,
			scroll_factor = 0.70,
		},
	},
})

-- Per-device tuning is harmless when a device is absent and applies by name
-- when this portable workstation hardware is present.
hl.device({
	name = "synps/2-synaptics-touchpad",
	sensitivity = -0.12,
})

hl.device({
	name = "tpps/2-elan-trackpoint",
	accel_profile = "flat",
	sensitivity = 0.40,
})
