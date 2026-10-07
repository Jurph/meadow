class_name MeadowSnapshotRenderer
extends Node3D
## Renders immutable Python simulation snapshots without owning simulation rules.

const HEX_SIZE := 0.55
const VERTICAL_SCALE := 0.55
const TILE_HEIGHT := 0.08

var _root_material: StandardMaterial3D
var _stem_material: StandardMaterial3D
var _seed_material: StandardMaterial3D


func _init() -> void:
	_root_material = StandardMaterial3D.new()
	_root_material.albedo_color = Color(0.48, 0.29, 0.13)
	_root_material.roughness = 0.9
	_root_material.no_depth_test = true

	_stem_material = StandardMaterial3D.new()
	_stem_material.albedo_color = Color(0.55, 0.78, 0.24)
	_stem_material.roughness = 0.75

	_seed_material = StandardMaterial3D.new()
	_seed_material.albedo_color = Color(0.74, 0.66, 0.36)
	_seed_material.roughness = 0.8


func render_snapshot(snapshot: Dictionary) -> void:
	var tiles: Array = snapshot["tiles"]
	for tile_value in tiles:
		_spawn_tile(tile_value as Dictionary)

	var plants: Array = snapshot["plants"]
	for plant_value in plants:
		_spawn_plant(plant_value as Dictionary)


func _spawn_tile(tile: Dictionary) -> void:
	var q := int(tile["q"])
	var r := int(tile["r"])
	var moisture := float(tile["moisture"])
	var nutrients := float(tile["nutrients"])
	var wetness := clampf(moisture / 80.0, 0.0, 1.0)
	var fertility := clampf(nutrients / 100.0, 0.0, 1.0)

	var dry_soil := Color(0.36, 0.29, 0.17)
	var meadow_green := Color(0.22, 0.48, 0.20)
	var wet_green := Color(0.16, 0.36, 0.26)
	var tile_color := dry_soil.lerp(meadow_green, 0.35 + 0.55 * fertility)
	tile_color = tile_color.lerp(wet_green, 0.35 * wetness)

	var material := StandardMaterial3D.new()
	material.albedo_color = tile_color
	material.roughness = 0.92

	var mesh := CylinderMesh.new()
	mesh.top_radius = HEX_SIZE * 0.92
	mesh.bottom_radius = HEX_SIZE * 0.92
	mesh.height = TILE_HEIGHT
	mesh.radial_segments = 6
	mesh.rings = 1

	var mesh_instance := MeshInstance3D.new()
	mesh_instance.name = "Tile_%d_%d" % [q, r]
	mesh_instance.mesh = mesh
	mesh_instance.set_surface_override_material(0, material)
	mesh_instance.position = axial_to_world_xz(q, r)
	add_child(mesh_instance)


func _spawn_plant(plant: Dictionary) -> void:
	var plant_id := int(plant["id"])
	var home: Variant = plant["home"]
	if home is Dictionary:
		var seed := MeshInstance3D.new()
		seed.name = "Plant_%d" % plant_id
		var sphere := SphereMesh.new()
		sphere.radius = 0.13
		sphere.height = 0.26
		seed.mesh = sphere
		seed.set_surface_override_material(0, _seed_material)
		seed.position = cell_to_world(home as Dictionary) + Vector3(0.0, 0.12, 0.0)
		add_child(seed)

	var segments: Array = plant["segments"]
	for segment_value in segments:
		_spawn_segment(segment_value as Dictionary, plant_id)


func _spawn_segment(segment: Dictionary, plant_id: int) -> void:
	var start := cell_to_world(segment["start"] as Dictionary)
	var end := cell_to_world(segment["end"] as Dictionary)
	var direction := end - start
	var length := direction.length()
	if length <= 0.0:
		return

	var segment_type := str(segment["segment_type"])
	var diameter := float(segment["diameter"])
	var radius := maxf(0.035, 0.055 * diameter)

	var mesh := CylinderMesh.new()
	mesh.top_radius = radius * 0.82
	mesh.bottom_radius = radius
	mesh.height = length
	mesh.radial_segments = 8
	mesh.rings = 1

	var mesh_instance := MeshInstance3D.new()
	mesh_instance.name = "Plant_%d_%s_%d" % [
		plant_id,
		segment_type,
		int(segment["id"]),
	]
	mesh_instance.mesh = mesh
	mesh_instance.position = (start + end) * 0.5
	mesh_instance.quaternion = Quaternion(Vector3.UP, direction.normalized())
	var material := _root_material if segment_type == "ROOT" else _stem_material
	mesh_instance.set_surface_override_material(0, material)
	add_child(mesh_instance)


static func axial_to_world_xz(q: int, r: int) -> Vector3:
	var x := HEX_SIZE * (sqrt(3.0) * float(q) + sqrt(3.0) * 0.5 * float(r))
	var z := HEX_SIZE * (1.5 * float(r))
	return Vector3(x, 0.0, z)


static func cell_to_world(cell: Dictionary) -> Vector3:
	var point := axial_to_world_xz(int(cell["q"]), int(cell["r"]))
	point.y = float(cell["z"]) * VERTICAL_SCALE + TILE_HEIGHT * 0.5
	return point
