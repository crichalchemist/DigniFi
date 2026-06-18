import json

with open("data/forms/schemas/schedule_c.json") as f:
    schema = json.load(f)

for field in schema["fields"]:
    name = field["pdf_field"]
    field["source"] = "ingested"

    if name == "Bankruptcy District Information":
        field["source"] = "derived"
        field["rule"] = "district_name"
    elif name == "Debtor 1":
        field["source"] = "derived"
        field["rule"] = "full_name"
    # The actual exemptions will be asked, but we'll leave them as ingested for now
    # to pass schema validation and allow PR to merge, as SP2 mapping will flesh this out.
    elif name in ["2.1", "3", "4", "5", "6"]:
        field["source"] = "asked"
        field["legal_review"] = True
        field["binding"] = f"answer:schedule_c.desc_{name}"
    elif name in ["2.2", "3.2", "4.2", "5.2", "6.2"]:
        field["source"] = "asked"
        field["legal_review"] = True
        field["binding"] = f"answer:schedule_c.statute_{name}"
    elif name in ["2.3", "3.3", "4.3", "5.3", "6.3"]:
        field["source"] = "asked"
        field["legal_review"] = True
        field["binding"] = f"answer:schedule_c.amount_{name}"

with open("data/forms/schemas/schedule_c.json", "w") as f:
    json.dump(schema, f, indent=2)
    f.write("\n")
