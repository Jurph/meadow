extends Node3D
## Meadow entry: load a Python snapshot, render it, and show diagnostics.

const SNAPSHOT_PATH := "res://data/demo-snapshot.json"
const EXPECTED_SCHEMA_VERSION := 2
const EXPECTED_SIM_API_VERSION := 2
const SnapshotRenderer = preload("res://gd/snapshot_renderer.gd")
const SnapshotLoader = preload("res://gd/snapshot_loader.gd")


func _ready() -> void:
	_setup_sky()
	var snapshot := SnapshotLoader.load_snapshot(
		SNAPSHOT_PATH,
		EXPECTED_SCHEMA_VERSION,
		EXPECTED_SIM_API_VERSION,
	)
	if snapshot.is_empty():
		return

	var renderer := SnapshotRenderer.new()
	renderer.name = "SnapshotRenderer"
	add_child(renderer)
	renderer.render_snapshot(snapshot)
	_add_debug_overlay(snapshot)


func _setup_sky() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.32, 0.52, 0.88)
	sky_mat.sky_horizon_color = Color(0.62, 0.74, 0.9)
	sky_mat.ground_bottom_color = Color(0.12, 0.18, 0.1)
	sky_mat.ground_horizon_color = Color(0.38, 0.46, 0.32)

	var sky := Sky.new()
	sky.sky_material = sky_mat

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.35

	var world_environment := WorldEnvironment.new()
	world_environment.environment = env
	add_child(world_environment)


func _add_debug_overlay(snapshot: Dictionary) -> void:
	var plants: Array = snapshot["plants"]
	var segment_count := 0
	var leaf_count := 0
	for plant_value in plants:
		var plant := plant_value as Dictionary
		var segments: Array = plant["segments"]
		var leaves: Array = plant["leaves"]
		segment_count += segments.size()
		leaf_count += leaves.size()

	var diagnostics_text := "No plants"
	if not plants.is_empty():
		var plant := plants[0] as Dictionary
		var resources := plant["resources"] as Dictionary
		var allocation := plant["assimilate_allocation"] as Dictionary
		diagnostics_text = "Plant %d reserves — %s" % [
			int(plant["id"]),
			_resource_text(resources),
		]
		diagnostics_text += "\nAllocation — root %.2f  leaf %.2f  stem %.2f  reproduce %.2f" % [
			float(allocation["root"]),
			float(allocation["leaf"]),
			float(allocation["stem"]),
			float(allocation["reproduce"]),
		]

		var balance_value: Variant = plant["balance_sheet"]
		if balance_value is Dictionary:
			var balance := balance_value as Dictionary
			var uptake := balance["root_uptake"] as Dictionary
			var photo := balance["photosynthesis"] as Dictionary
			var construction_potential := balance["construction_potential"] as Dictionary
			var construction_actual := balance["construction"] as Dictionary
			diagnostics_text += "\nUptake — potential %s  |  actual %s" % [
				_resource_text(uptake["potential"] as Dictionary),
				_resource_text(uptake["actual"] as Dictionary),
			]
			diagnostics_text += "\nPhotosynthesis — potential %.2f  |  actual %.2f  |  water %.2f" % [
				float((photo["potential"] as Dictionary)["assimilate"]),
				float((photo["actual"] as Dictionary)["assimilate"]),
				float(balance["photosynthesis_water"]),
			]
			diagnostics_text += (
				"\nConstruction — proposed %d (%s)  |  built %d (%s)"
				% [
					_organ_count(balance["organ_proposals"] as Array),
					_resource_text(construction_potential),
					_organ_count(balance["organs_constructed"] as Array),
					_resource_text(construction_actual),
				]
			)
			var limiters := PackedStringArray()
			for factor in uptake["limiting_factors"] as Array:
				limiters.append("uptake:%s" % str(factor))
			for factor in photo["limiting_factors"] as Array:
				limiters.append("photo:%s" % str(factor))
			for factor in balance["construction_limiting_factors"] as Array:
				limiters.append("construction:%s" % str(factor))
			diagnostics_text += "\nLimiters — %s" % (
				"none" if limiters.is_empty() else ", ".join(limiters)
			)

	var layer := CanvasLayer.new()
	layer.name = "DebugOverlay"
	add_child(layer)

	var panel := ColorRect.new()
	panel.position = Vector2(18.0, 18.0)
	panel.size = Vector2(1020.0, 220.0)
	panel.color = Color(0.03, 0.06, 0.04, 0.82)
	layer.add_child(panel)

	var label := Label.new()
	label.position = Vector2(14.0, 10.0)
	label.add_theme_font_size_override("font_size", 16)
	label.add_theme_color_override("font_color", Color(0.88, 0.94, 0.82))
	label.text = "Meadow — Python snapshot\nTick %d  |  Plants %d  |  Segments %d  |  Leaves %d\n%s" % [
		int(snapshot["tick"]),
		plants.size(),
		segment_count,
		leaf_count,
		diagnostics_text,
	]
	panel.add_child(label)


func _resource_text(resources: Dictionary) -> String:
	return "W %.2f M %.2f A %.2f" % [
		float(resources["water"]),
		float(resources["minerals"]),
		float(resources["assimilate"]),
	]


func _organ_count(organs: Array) -> int:
	var total := 0
	for organ_value in organs:
		var organ := organ_value as Dictionary
		total += int(organ["count"])
	return total
