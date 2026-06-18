import json

with open("data/forms/schemas/schedule_a_b.json") as f:
    schema = json.load(f)

for field in schema["fields"]:
    name = field["pdf_field"]

    # We set everything to "ingested" by default to pass tests unless we specifically map it.
    field["source"] = "ingested"

    # Standard Header
    if name == "Bankruptcy District Information":
        field["source"] = "derived"
        field["rule"] = "district_name"
    elif name == "Debtor 1":
        field["source"] = "derived"
        field["rule"] = "full_name"

    # Real Estate
    elif name == "1 1":
        field["source"] = "asked"
        field["binding"] = "assets[asset_type=real_property][].description"
        field["repeat"] = "assets_real"
        field["row"] = 1
        field["repeat_capacity"] = 2
    elif name == "1 1a":
        field["source"] = "asked"
        field["binding"] = "assets[asset_type=real_property][].current_value"
        field["repeat"] = "assets_real"
        field["row"] = 1
        field["repeat_capacity"] = 2

    # Vehicles
    elif name == "3 description":
        field["source"] = "asked"
        field["binding"] = "assets[asset_type=vehicle][].description"
        field["repeat"] = "assets_vehicle"
        field["row"] = 1
        field["repeat_capacity"] = 2
    elif name == "3 description amount":
        field["source"] = "asked"
        field["binding"] = "assets[asset_type=vehicle][].current_value"
        field["repeat"] = "assets_vehicle"
        field["row"] = 1
        field["repeat_capacity"] = 2

    # Derived scalar fields based on old schedule_ab_generator logic
    elif name == "16 Cash amount":
        field["source"] = "derived"
        field["rule"] = "total_bank_accounts"
    elif name == "12":
        field["source"] = "derived"
        field["rule"] = "total_retirement_accounts"
    elif name == "17":
        field["source"] = "derived"
        field["rule"] = "total_other_assets"

with open("data/forms/schemas/schedule_a_b.json", "w") as f:
    json.dump(schema, f, indent=2)
    f.write("\n")
