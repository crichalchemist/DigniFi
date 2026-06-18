import json
import sys

def curate():
    with open("data/forms/schemas/schedule_e_f.json", "r") as f:
        schema = json.load(f)

    # Set all defaults to ingested
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
    set_field("Debtor 2", "derived", rule="joint_filer_name")

    # PRIORITY CLAIMS
    # Fields for priority claims are 1, 1_2, 1_3, 1_4, 1_5; 2, 2_2... up to 4
    for i in range(1, 5):
        base = str(i)
        suffix = f"_{i}" if i > 1 else ""
        set_field(base, "asked", binding=f"debts[is_secured=False,is_priority=True][].creditor_name", repeat="priority_claims", row=i)
        set_field(f"{base}_4", "asked", binding=f"debts[is_secured=False,is_priority=True][].amount_owed", repeat="priority_claims", row=i)

        # Flags
        set_field(f"Contingent{suffix}", "asked", binding=f"debts[is_secured=False,is_priority=True][].is_contingent", repeat="priority_claims", row=i)
        set_field(f"Unliquidated{suffix}", "asked", binding=f"debts[is_secured=False,is_priority=True][].is_unliquidated", repeat="priority_claims", row=i)
        set_field(f"Disputed{suffix}", "asked", binding=f"debts[is_secured=False,is_priority=True][].is_disputed", repeat="priority_claims", row=i)

    # NONPRIORITY CLAIMS
    # Creditors Name, Creditors Name_2... Creditors Name_18
    # Amount owed: Let's just map them. In ab_fields_ef.txt, we had Other_2, Other_3, maybe we don't map amounts for now to avoid errors.
    # Actually, the old generator DID map result[f"{base}_4"] = fmt(debt.amount_owed). But base went from 1 to 10. So it used 1_4 to 10_4.
    # We saw "4" up to "4_5". So "5_4" doesn't exist. So amount owed wasn't mapped at all.
    # Let's map Creditors Name correctly.
    for i in range(1, 19):
        # The fields are named "Creditors Name", "Creditors Name_2" ... "Creditors Name_18"
        # Oh, wait! Creditors Name is for row 1. Then Creditors Name_2 for row 2, etc.
        suffix = f"_{i}" if i > 1 else ""
        set_field(f"Creditors Name{suffix}", "asked", binding=f"debts[is_secured=False,is_priority=False][].creditor_name", repeat="nonpriority_claims", row=i)

    # We need to set repeat_capacities
    for field in schema["fields"]:
        if field.get("repeat") == "priority_claims":
            field["repeat_capacity"] = 4
        elif field.get("repeat") == "nonpriority_claims":
            field["repeat_capacity"] = 18

    with open("data/forms/schemas/schedule_e_f.json", "w") as f:
        json.dump(schema, f, indent=2)

if __name__ == "__main__":
    curate()
