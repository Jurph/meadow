extends RefCounted
## Loads and validates the versioned Python-to-Godot snapshot contract.

const RECONCILIATION_TOLERANCE := 1e-9


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
	error = _integral_fields_error(snapshot, ["tick"], "snapshot")
	if not error.is_empty():
		return error

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
		var context := "tiles[%d]" % index
		error = _integral_fields_error(tile, ["q", "r"], context)
		if not error.is_empty():
			return error
		error = _numeric_fields_error(
			tile,
			["moisture", "nutrients", "light", "drainage", "slope_q", "slope_r"],
			context,
		)
		if not error.is_empty():
			return error
		if not tile.has("occupant_id"):
			return "%s.occupant_id is required" % context
		var occupant: Variant = tile["occupant_id"]
		if occupant != null and not _is_integral_number(occupant):
			return "%s.occupant_id must be an integer or null" % context

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
		if not plant.has("home"):
			return "%s.home is required" % context
		var home: Variant = plant["home"]
		if home != null:
			error = _cell_error(home, "%s.home" % context)
			if not error.is_empty():
				return error
		var resources_value: Variant = plant.get("resources")
		error = _resource_error(resources_value, "%s.resources" % context)
		if not error.is_empty():
			return error
		var resources := resources_value as Dictionary
		var allocation_value: Variant = plant.get("assimilate_allocation")
		error = _allocation_error(
			allocation_value,
			"%s.assimilate_allocation" % context,
		)
		if not error.is_empty():
			return error
		var allocation := allocation_value as Dictionary
		var allocated_assimilate := 0.0
		for category in ["root", "leaf", "stem", "reproduce"]:
			allocated_assimilate += float(allocation[category])
		if (
			allocated_assimilate
			> float(resources["assimilate"]) + RECONCILIATION_TOLERANCE
		):
			return "%s.assimilate_allocation exceeds available assimilate" % context
		if not plant.has("balance_sheet"):
			return "%s.balance_sheet is required" % context
		var balance_sheet: Variant = plant["balance_sheet"]
		if balance_sheet != null:
			error = _balance_sheet_error(
				balance_sheet,
				resources,
				"%s.balance_sheet" % context,
			)
			if not error.is_empty():
				return error
		error = _traits_error(plant.get("traits"), "%s.traits" % context)
		if not error.is_empty():
			return error
		var segments_value: Variant = plant.get("segments")
		error = _segments_error(segments_value, "%s.segments" % context)
		if not error.is_empty():
			return error
		if home == null and not (segments_value as Array).is_empty():
			return "%s.segments requires a non-null home" % context
		error = _leaves_error(
			plant.get("leaves"),
			segments_value as Array,
			home,
			"%s.leaves" % context,
		)
		if not error.is_empty():
			return error

	return ""


static func _resource_error(value: Variant, context: String) -> String:
	if not value is Dictionary:
		return "%s must be an object" % context
	var resources := value as Dictionary
	var error := _numeric_fields_error(
		resources,
		["water", "minerals", "assimilate"],
		context,
	)
	if not error.is_empty():
		return error
	for resource in ["water", "minerals", "assimilate"]:
		if float(resources[resource]) < 0.0:
			return "%s.%s must be non-negative" % [context, resource]
	return ""


static func _allocation_error(value: Variant, context: String) -> String:
	if not value is Dictionary:
		return "%s must be an object" % context
	var allocation := value as Dictionary
	var error := _numeric_fields_error(
		allocation,
		["root", "leaf", "stem", "reproduce"],
		context,
	)
	if not error.is_empty():
		return error
	for category in ["root", "leaf", "stem", "reproduce"]:
		if float(allocation[category]) < 0.0:
			return "%s.%s must be non-negative" % [context, category]
	return ""


static func _flux_error(value: Variant, context: String) -> String:
	if not value is Dictionary:
		return "%s must be an object" % context
	var flux := value as Dictionary
	var error := _resource_error(flux.get("potential"), "%s.potential" % context)
	if not error.is_empty():
		return error
	error = _resource_error(flux.get("actual"), "%s.actual" % context)
	if not error.is_empty():
		return error
	error = _string_array_error(
		flux.get("limiting_factors"),
		"%s.limiting_factors" % context,
	)
	if not error.is_empty():
		return error
	var potential := flux["potential"] as Dictionary
	var actual := flux["actual"] as Dictionary
	for resource in ["water", "minerals", "assimilate"]:
		if float(actual[resource]) > float(potential[resource]) + 1e-12:
			return "%s.actual.%s cannot exceed potential" % [context, resource]
	return ""


static func _balance_sheet_error(
	value: Variant,
	resources: Dictionary,
	context: String,
) -> String:
	if not value is Dictionary:
		return "%s must be an object or null" % context
	var balance := value as Dictionary
	var error := _integral_fields_error(balance, ["tick"], context)
	if not error.is_empty():
		return error
	error = _resource_error(balance.get("opening"), "%s.opening" % context)
	if not error.is_empty():
		return error
	error = _flux_error(balance.get("root_uptake"), "%s.root_uptake" % context)
	if not error.is_empty():
		return error
	error = _flux_error(balance.get("photosynthesis"), "%s.photosynthesis" % context)
	if not error.is_empty():
		return error
	error = _numeric_fields_error(
		balance,
		["photosynthesis_water"],
		context,
	)
	if not error.is_empty():
		return error
	if float(balance["photosynthesis_water"]) < 0.0:
		return "%s.photosynthesis_water must be non-negative" % context
	error = _resource_error(
		balance.get("construction_potential"),
		"%s.construction_potential" % context,
	)
	if not error.is_empty():
		return error
	error = _organ_counts_error(
		balance.get("organ_proposals"),
		"%s.organ_proposals" % context,
	)
	if not error.is_empty():
		return error
	error = _resource_error(balance.get("construction"), "%s.construction" % context)
	if not error.is_empty():
		return error
	error = _organ_counts_error(
		balance.get("organs_constructed"),
		"%s.organs_constructed" % context,
	)
	if not error.is_empty():
		return error
	error = _string_array_error(
		balance.get("construction_limiting_factors"),
		"%s.construction_limiting_factors" % context,
	)
	if not error.is_empty():
		return error
	error = _resource_error(balance.get("closing"), "%s.closing" % context)
	if not error.is_empty():
		return error

	var construction_potential := balance["construction_potential"] as Dictionary
	var construction_actual := balance["construction"] as Dictionary
	for resource in ["water", "minerals", "assimilate"]:
		if (
			float(construction_actual[resource])
			> float(construction_potential[resource]) + RECONCILIATION_TOLERANCE
		):
			return "%s.construction.%s cannot exceed potential" % [context, resource]
	var proposal_counts := {}
	for organ_value in balance["organ_proposals"] as Array:
		var organ := organ_value as Dictionary
		proposal_counts[str(organ["organ_type"])] = int(organ["count"])
	for organ_value in balance["organs_constructed"] as Array:
		var organ := organ_value as Dictionary
		var organ_type := str(organ["organ_type"])
		if int(organ["count"]) > int(proposal_counts.get(organ_type, 0)):
			return "%s constructed %s count cannot exceed proposals" % [
				context,
				organ_type,
			]

	var opening := balance["opening"] as Dictionary
	var root_uptake := balance["root_uptake"] as Dictionary
	var uptake_actual := root_uptake["actual"] as Dictionary
	var photosynthesis := balance["photosynthesis"] as Dictionary
	var photo_actual := photosynthesis["actual"] as Dictionary
	var construction := balance["construction"] as Dictionary
	var closing := balance["closing"] as Dictionary
	var expected := {
		"water":
		float(opening["water"])
		+ float(uptake_actual["water"])
		- float(balance["photosynthesis_water"])
		- float(construction["water"]),
		"minerals":
		float(opening["minerals"])
		+ float(uptake_actual["minerals"])
		- float(construction["minerals"]),
		"assimilate":
		float(opening["assimilate"])
		+ float(photo_actual["assimilate"])
		- float(construction["assimilate"]),
	}
	for resource in ["water", "minerals", "assimilate"]:
		if (
			absf(float(closing[resource]) - float(expected[resource]))
			> RECONCILIATION_TOLERANCE
		):
			return "%s does not reconcile for %s" % [context, resource]
		if (
			absf(float(closing[resource]) - float(resources[resource]))
			> RECONCILIATION_TOLERANCE
		):
			return "%s.closing does not match plant resources for %s" % [
				context,
				resource,
			]
	return ""


static func _traits_error(value: Variant, context: String) -> String:
	if not value is Dictionary:
		return "%s must be an object" % context
	var traits := value as Dictionary
	var error := _numeric_fields_error(
		traits,
		[
			"number_of_lobes",
			"lobe_aspect_ratio",
			"lobe_length",
			"root_reach",
			"alloc_root",
			"alloc_leaf",
			"alloc_stem",
			"alloc_reproduce",
			"basal_length",
			"branch_spacing",
			"apical_length",
			"max_root_length",
			"branch_probability",
			"gravitropism_weight",
			"hydrotropism_weight",
			"gsa_root",
		],
		context,
	)
	if not error.is_empty():
		return error
	for organ_type in ["root", "stem", "leaf"]:
		error = _resource_error(
			traits.get("%s_construction_cost" % organ_type),
			"%s.%s_construction_cost" % [context, organ_type],
		)
		if not error.is_empty():
			return error
	return ""


static func _segments_error(value: Variant, context: String) -> String:
	if not value is Array:
		return "%s must be an array" % context
	var segments := value as Array
	var segment_ids := {}
	for index in range(segments.size()):
		if not segments[index] is Dictionary:
			return "%s[%d] must be an object" % [context, index]
		var segment := segments[index] as Dictionary
		var segment_context := "%s[%d]" % [context, index]
		var error := _integral_fields_error(segment, ["id", "order"], segment_context)
		if not error.is_empty():
			return error
		var segment_id := int(segment["id"])
		if segment_ids.has(segment_id):
			return "%s.id must be unique" % segment_context
		segment_ids[segment_id] = true
		if not segment.has("parent_id"):
			return "%s.parent_id is required" % segment_context
		var parent_id: Variant = segment["parent_id"]
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


static func _leaves_error(
	value: Variant,
	segments: Array,
	home: Variant,
	context: String,
) -> String:
	if not value is Array:
		return "%s must be an array" % context
	var segments_by_id := {}
	for segment_value in segments:
		var segment := segment_value as Dictionary
		segments_by_id[int(segment["id"])] = segment
	var leaves := value as Array
	var leaf_ids := {}
	for index in range(leaves.size()):
		if not leaves[index] is Dictionary:
			return "%s[%d] must be an object" % [context, index]
		var leaf := leaves[index] as Dictionary
		var leaf_context := "%s[%d]" % [context, index]
		var error := _integral_fields_error(leaf, ["id"], leaf_context)
		if not error.is_empty():
			return error
		var leaf_id := int(leaf["id"])
		if leaf_ids.has(leaf_id):
			return "%s.id must be unique" % leaf_context
		leaf_ids[leaf_id] = true
		if not leaf.has("attachment_segment_id"):
			return "%s.attachment_segment_id is required" % leaf_context
		var attachment: Variant = leaf["attachment_segment_id"]
		if attachment != null and not _is_integral_number(attachment):
			return "%s.attachment_segment_id must be an integer or null" % leaf_context
		error = _cell_error(leaf.get("cell"), "%s.cell" % leaf_context)
		if not error.is_empty():
			return error
		var cell := leaf["cell"] as Dictionary
		if attachment == null:
			if home == null or not _same_cell(cell, home as Dictionary):
				return "%s without an attachment must be at the plant home" % leaf_context
		else:
			var attachment_id := int(attachment)
			if not segments_by_id.has(attachment_id):
				return "%s.attachment_segment_id does not exist" % leaf_context
			var attachment_segment := segments_by_id[attachment_id] as Dictionary
			if attachment_segment["segment_type"] != "STEM":
				return "%s must attach to a STEM segment" % leaf_context
			if not _same_cell(cell, attachment_segment["end"] as Dictionary):
				return "%s.cell must equal its attachment segment end" % leaf_context
		error = _numeric_fields_error(leaf, ["area", "health"], leaf_context)
		if not error.is_empty():
			return error
		if float(leaf["area"]) < 0.0:
			return "%s.area must be non-negative" % leaf_context
		if float(leaf["health"]) < 0.0 or float(leaf["health"]) > 1.0:
			return "%s.health must be between 0 and 1" % leaf_context
	return ""


static func _organ_counts_error(value: Variant, context: String) -> String:
	if not value is Array:
		return "%s must be an array" % context
	var organs := value as Array
	for index in range(organs.size()):
		if not organs[index] is Dictionary:
			return "%s[%d] must be an object" % [context, index]
		var organ := organs[index] as Dictionary
		var organ_context := "%s[%d]" % [context, index]
		if not organ.get("organ_type") is String:
			return "%s.organ_type must be a string" % organ_context
		var error := _integral_fields_error(organ, ["count"], organ_context)
		if not error.is_empty():
			return error
		if int(organ["count"]) < 0:
			return "%s.count must be non-negative" % organ_context
	return ""


static func _same_cell(left: Dictionary, right: Dictionary) -> bool:
	return (
		int(left["q"]) == int(right["q"])
		and int(left["r"]) == int(right["r"])
		and int(left["z"]) == int(right["z"])
	)


static func _version_error(snapshot: Dictionary, key: String, expected: int) -> String:
	var value: Variant = snapshot.get(key)
	if not _is_integral_number(value) or float(value) != float(expected):
		return "%s must be exactly %d" % [key, expected]
	return ""


static func _cell_error(value: Variant, context: String) -> String:
	if not value is Dictionary:
		return "%s must be an object" % context
	return _integral_fields_error(value as Dictionary, ["q", "r", "z"], context)


static func _string_array_error(value: Variant, context: String) -> String:
	if not value is Array:
		return "%s must be an array" % context
	var items := value as Array
	for index in range(items.size()):
		if not items[index] is String:
			return "%s[%d] must be a string" % [context, index]
	return ""


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
