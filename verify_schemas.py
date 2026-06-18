import json
import glob
import sys

files = glob.glob('data/forms/schemas/*.json')
total_fields = 0
unmapped_fields = []

for file in files:
    with open(file) as f:
        schema = json.load(f)
        fields = schema.get("fields", [])
        for field in fields:
            total_fields += 1
            source = field.get("source")
            pdf_field = field.get("pdf_field", "")

            # Identify purely unmapped fields
            if source == "unmapped" or not source:
                # ignore print/saveas/attach buttons
                if pdf_field not in ["Print1", "SaveAs", "attach", "Reset"]:
                    unmapped_fields.append(f"{file}: {pdf_field}")

print(f"Total fields checked: {total_fields}")
if unmapped_fields:
    print(f"Found {len(unmapped_fields)} unmapped fields:")
    for m in unmapped_fields[:50]:
        print(m)
    sys.exit(1)
else:
    print("All fields mapped!")
