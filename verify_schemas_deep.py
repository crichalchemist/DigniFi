import json
import glob
from collections import Counter

files = glob.glob('data/forms/schemas/*.json')
errors_by_file = Counter()
specific_errors = []

for file in files:
    with open(file) as f:
        schema = json.load(f)
        fields = schema.get("fields", [])
        for field in fields:
            source = field.get("source")
            pdf_field = field.get("pdf_field", "")

            if pdf_field in ["Print1", "SaveAs", "attach", "Reset"]:
                continue

            if not source or source == "unmapped":
                errors_by_file[file] += 1
                specific_errors.append(f"{file}: {pdf_field} unmapped")
                continue

            if source == "derived" and not field.get("rule"):
                errors_by_file[file] += 1
                specific_errors.append(f"{file}: {pdf_field} derived no rule")
            elif source == "asked" and not field.get("binding"):
                errors_by_file[file] += 1
                specific_errors.append(f"{file}: {pdf_field} asked no binding")
            elif source == "session" and not field.get("binding"):
                errors_by_file[file] += 1
                specific_errors.append(f"{file}: {pdf_field} session no binding")
            elif source in ("ingested", "db_aggregate") and not field.get("ingest_key"):
                errors_by_file[file] += 1
                specific_errors.append(f"{file}: {pdf_field} {source} no ingest_key")
            elif source == "constant" and "value" not in field:
                errors_by_file[file] += 1
                specific_errors.append(f"{file}: {pdf_field} constant no value")
            elif field.get("repeat") and not field.get("repeat_capacity"):
                errors_by_file[file] += 1
                specific_errors.append(f"{file}: {pdf_field} repeat no capacity")

print("Errors by schema file:")
if not errors_by_file:
    print("No errors! Perfect!")
for file, count in errors_by_file.items():
    print(f"{file}: {count} errors")

for err in specific_errors[:20]:
    print(err)
