extends RefCounted
## Loads and validates the versioned Python-to-Godot snapshot contract.


static func load_snapshot(
	path: String,
	expected_schema_version: int,
	expected_sim_api_version: int,
) -> Dictionary:
	if not FileAccess.file_exists(path):
		push_error("Meadow snapshot not found: %s" % path)
		return {}

	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error(
			"Cannot open Meadow snapshot %s: %s"
			% [path, error_string(FileAccess.get_open_error())]
		)
		return {}

	var parser := JSON.new()
	var parse_result := parser.parse(file.get_as_text())
	if parse_result != OK:
		push_error(
			"Invalid Meadow snapshot JSON at line %d: %s"
			% [parser.get_error_line(), parser.get_error_message()]
		)
		return {}
	if not parser.data is Dictionary:
		push_error("Meadow snapshot root must be an object")
		return {}

	var snapshot := parser.data as Dictionary
	var validation_error := _validate_snapshot(
		snapshot,
		expected_schema_version,
		expected_sim_api_version,
	)
	if not validation_error.is_empty():
		push_error("Invalid Meadow snapshot: %s" % validation_error)
		return {}
	return snapshot


static func _validate_snapshot(
	snapshot: Dictionary,
	expected_schema_version: int,
	expected_sim_api_version: int,
) -> String:
	var error := _version_error(snapshot, "schema_version", expected_schema_version)
	if not error.is_empty():
		return error
	error = _version_error(snapshot, "sim_api_version", expected_sim_api_version)
	if not error.is_empty():
		return error

	if not snapshot.get("tick") is float and not snapshot.get("tick") is int:
		return "tick must be an integer"
	if not _is_integral_number(snapshot.get("tick")):
		return "tick must be an integer"

	var world_value: Variant = snapshot.get("world")
	if not world_value is Dictionary:
		return "world must be an object"
	var world := world_value as Dictionary
	error = _integral_fields_error(world, ["width", "height", "min_z", "max_z"], "world")
	if not error.is_empty():
		return error
	if int(world["width"]) < 1 or int(world["height"]) < 1:
		return "world dimensions must be positive"

	var tiles_value: Variant = snapshot.get("tiles")
	if not tiles_value is Array:
		return "tiles must be an array"
	var tiles := tiles_value as Array
	if tiles.size() != int(world["width"]) * int(world["height"]):
		return "tiles length must match world dimensions"
	for index in range(tiles.size()):
		if not tiles[index] is Dictionary:
			return "tiles[%d] must be an object" % index
		var tile := tiles[index] as Dictionary
		error = _integral_fields_error(tile, ["q", "r"], "tiles[%d]" % index)
		if not error.is_empty():
			return error
		error = _numeric_fields_error(
			tile,
			["moisture", "nutrients", "light", "drainage", "slope_q", "slope_r"],
			"tiles[%d]" % index,
		)
		if not error.is_empty():
			return error
		var occupant: Variant = tile.get("occupant_id")
		if occupant != null and not _is_integral_number(occupant):
			return "tiles[%d].occupant_id must be an integer or null" % index

	var plants_value: Variant = snapshot.get("plants")
	if not plants_value is Array:
		return "plants must be an array"
	var plants := plants_value as Array
	for plant_index in range(plants.size()):
		if not plants[plant_index] is Dictionary:
			return "plants[%d] must be an object" % plant_index
		var plant := plants[plant_index] as Dictionary
		var context := "plants[%d]" % plant_index
		error = _integral_fields_error(plant, ["id"], context)
		if not error.is_empty():
			return error
		error = _numeric_fields_error(
			plant,
			["moisture_reserve", "nutrient_reserve", "cellulose"],
			context,
		)
		if not error.is_empty():
			return error
		if not plant.has("home"):
			return "%s.home is required" % context
		var home: Variant = plant["home"]
		if home != null:
			error = _cell_error(home, "%s.home" % context)
			if not error.is_empty():
				return error
		if not plant.get("traits") is Dictionary:
			return "%s.traits must be an object" % context

		var segments_value: Variant = plant.get("segments")
		if not segments_value is Array:
			return "%s.segments must be an array" % context
		var segments := segments_value as Array
		for segment_index in range(segments.size()):
			if not segments[segment_index] is Dictionary:
				return "%s.segments[%d] must be an object" % [context, segment_index]
			var segment := segments[segment_index] as Dictionary
			var segment_context := "%s.segments[%d]" % [context, segment_index]
			error = _integral_fields_error(segment, ["id", "order"], segment_context)
			if not error.is_empty():
				return error
			var parent_id: Variant = segment.get("parent_id")
			if parent_id != null and not _is_integral_number(parent_id):
				return "%s.parent_id must be an integer or null" % segment_context
			var segment_type: Variant = segment.get("segment_type")
			if segment_type != "ROOT" and segment_type != "STEM":
				return "%s.segment_type must be ROOT or STEM" % segment_context
			error = _numeric_fields_error(
				segment,
				["diameter", "accumulated_length"],
				segment_context,
			)
			if not error.is_empty():
				return error
			error = _cell_error(segment.get("start"), "%s.start" % segment_context)
			if not error.is_empty():
				return error
			error = _cell_error(segment.get("end"), "%s.end" % segment_context)
			if not error.is_empty():
				return error

	return ""


static func _version_error(snapshot: Dictionary, key: String, expected: int) -> String:
	var value: Variant = snapshot.get(key)
	if not _is_integral_number(value) or float(value) != float(expected):
		return "%s must be exactly %d" % [key, expected]
	return ""


static func _cell_error(value: Variant, context: String) -> String:
	if not value is Dictionary:
		return "%s must be an object" % context
	return _integral_fields_error(value as Dictionary, ["q", "r", "z"], context)


static func _numeric_fields_error(
	record: Dictionary,
	fields: Array[String],
	context: String,
) -> String:
	for field in fields:
		if not _is_number(record.get(field)):
			return "%s.%s must be numeric" % [context, field]
	return ""


static func _integral_fields_error(
	record: Dictionary,
	fields: Array[String],
	context: String,
) -> String:
	for field in fields:
		if not _is_integral_number(record.get(field)):
			return "%s.%s must be an integer" % [context, field]
	return ""


static func _is_integral_number(value: Variant) -> bool:
	return _is_number(value) and floorf(float(value)) == float(value)


static func _is_number(value: Variant) -> bool:
	var value_type := typeof(value)
	return value_type == TYPE_INT or value_type == TYPE_FLOAT
