extends Node3D
## Meadow entry: load a Python snapshot, render it, and show diagnostics.

const SNAPSHOT_PATH := "res://data/demo-snapshot.json"
const EXPECTED_SCHEMA_VERSION := 1
const EXPECTED_SIM_API_VERSION := 1
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
	var plants: Array = snapshot.get("plants", [])
	var segment_count := 0
	for plant_value in plants:
		var plant := plant_value as Dictionary
		var segments: Array = plant.get("segments", [])
		segment_count += segments.size()

	var reserve_text := "No plants"
	if not plants.is_empty():
		var first_plant := plants[0] as Dictionary
		reserve_text = "Plant 0 — water %.2f  nutrients %.2f  cellulose %.2f" % [
			float(first_plant.get("moisture_reserve", 0.0)),
			float(first_plant.get("nutrient_reserve", 0.0)),
			float(first_plant.get("cellulose", 0.0)),
		]

	var layer := CanvasLayer.new()
	layer.name = "DebugOverlay"
	add_child(layer)

	var panel := ColorRect.new()
	panel.position = Vector2(18.0, 18.0)
	panel.size = Vector2(430.0, 104.0)
	panel.color = Color(0.03, 0.06, 0.04, 0.82)
	layer.add_child(panel)

	var label := Label.new()
	label.position = Vector2(14.0, 10.0)
	label.add_theme_font_size_override("font_size", 18)
	label.add_theme_color_override("font_color", Color(0.88, 0.94, 0.82))
	label.text = "Meadow — Python snapshot\nTick %d  |  Plants %d  |  Segments %d\n%s" % [
		int(snapshot.get("tick", 0)),
		plants.size(),
		segment_count,
		reserve_text,
	]
	panel.add_child(label)
