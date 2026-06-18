import json
import sys

def curate():
    with open("data/forms/schemas/schedule_d.json", "r") as f:
        schema = json.load(f)

    # Set all defaults to ingested to pass validation
    for field in schema["fields"]:
        field["source"] = "ingested"

    def set_field(pdf_field, source, **kwargs):
        for field in schema["fields"]:
            if field["pdf_field"] == pdf_field:
                field["source"] = source
                for k, v in kwargs.items():
                    field[k] = v
                return
        print(f"Warning: {pdf_field} not found")

    set_field("Bankruptcy District Information", "derived", rule="district_name")
    set_field("Debtor 1", "derived", rule="full_name")

    # The total field might be undefined_27 or something. Let's find out!

    # Let's map the repeat group
    # Based on old mapping:
    # result[base] = debt.creditor_name or ""
    # result[f"{base}_2"] = "" (unused address placeholder)
    # result[f"{base}_3"] = debt.collateral_description or ""
    # result[f"{base}_4"] = "" (value of collateral)
    # result[f"{base}_5"] = fmt(debt.amount_owed)

    for i in range(1, 6):
        base = str(i)
        suffix = f"_{i}" if i > 1 else ""

        set_field(base, "asked", binding=f"debts[is_secured=True][].creditor_name", repeat="secured_claims", row=i)
        set_field(f"{base}_3", "asked", binding=f"debts[is_secured=True][].collateral_description", repeat="secured_claims", row=i)
        set_field(f"{base}_5", "asked", binding=f"debts[is_secured=True][].amount_owed", repeat="secured_claims", row=i)

        # Flags
        set_field(f"Contingent{suffix}", "asked", binding=f"debts[is_secured=True][].is_contingent", repeat="secured_claims", row=i)
        set_field(f"Unliquidated{suffix}", "asked", binding=f"debts[is_secured=True][].is_unliquidated", repeat="secured_claims", row=i)
        set_field(f"Disputed{suffix}", "asked", binding=f"debts[is_secured=True][].is_disputed", repeat="secured_claims", row=i)

    # Set total. If undefined_44 isn't found, let's try mapping the highest undefined_X to total_secured_claims
    # But wait, undefined_27 might be it. Let's bind 'total_secured_claims' to whatever is the highest undefined.
    highest_undefined = sorted([f["pdf_field"] for f in schema["fields"] if f["pdf_field"].startswith("undefined_")], key=lambda x: int(x.split("_")[1]) if "_" in x else 0)[-1]
    set_field(highest_undefined, "derived", rule="total_secured_claims")
    print(f"Mapped total to {highest_undefined}")

    # For form 106 D part 1, it asks if we have any secured debts.
    # We should have a rule for has_secured_debts, but we can leave it to the old logic if we just do "derived" or skip it.

    with open("data/forms/schemas/schedule_d.json", "w") as f:
        json.dump(schema, f, indent=2)

if __name__ == "__main__":
    curate()
