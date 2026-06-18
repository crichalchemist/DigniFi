import json

def fix_capacity():
    with open("data/forms/schemas/schedule_d.json", "r") as f:
        schema = json.load(f)

    for field in schema["fields"]:
        if field.get("repeat") == "secured_claims":
            field["repeat_capacity"] = 4

    with open("data/forms/schemas/schedule_d.json", "w") as f:
        json.dump(schema, f, indent=2)

if __name__ == "__main__":
    fix_capacity()
