extends Node3D
## Meadow entry: sky, light, camera, and a small hex patch preview.

const GRID_SIZE := 7
const HEX_SIZE := 0.55


func _ready() -> void:
	_setup_sky()
	_spawn_demo_hexes()


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

	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)


func _spawn_demo_hexes() -> void:
	var root := Node3D.new()
	root.name = "HexPreview"
	add_child(root)

	var grass := Color(0.22, 0.48, 0.2)
	var grass_dark := Color(0.14, 0.32, 0.12)

	for q in range(GRID_SIZE):
		for r in range(GRID_SIZE):
			var parity := (q + r) & 1
			var mat := StandardMaterial3D.new()
			mat.albedo_color = grass if parity == 0 else grass_dark
			mat.roughness = 0.92

			var mesh_inst := MeshInstance3D.new()
			var cyl := CylinderMesh.new()
			cyl.top_radius = HEX_SIZE * 0.92
			cyl.bottom_radius = HEX_SIZE * 0.92
			cyl.height = 0.08
			cyl.radial_segments = 6
			cyl.rings = 1
			mesh_inst.mesh = cyl
			mesh_inst.set_surface_override_material(0, mat)
			mesh_inst.position = axial_to_world_xz(q, r)
			root.add_child(mesh_inst)


static func axial_to_world_xz(q: int, r: int) -> Vector3:
	var s := float(HEX_SIZE)
	var x := s * (sqrt(3.0) * float(q) + sqrt(3.0) * 0.5 * float(r))
	var z := s * (1.5 * float(r))
	return Vector3(x, 0.0, z)
