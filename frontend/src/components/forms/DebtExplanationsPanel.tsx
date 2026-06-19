export interface DebtClassification {
  debt_id: number;
  creditor: string;
  debt_type: string;
  dischargeable: boolean;
  reason: string;
  proceeding_needed: boolean;
}

export function DebtExplanationsPanel({ debts }: { debts: DebtClassification[] }) {
  if (debts.length === 0) {
    return <div className="p-4 text-gray-500">No amounts owed to evaluate.</div>;
  }

  const dischargeable = debts.filter((d) => d.dischargeable);
  const nonDischargeable = debts.filter((d) => !d.dischargeable);

  return (
    <div className="debt-explanations p-4 border rounded">
      <h3 className="text-lg font-semibold mb-3">Discharge Summary</h3>
      <p className="text-sm text-gray-600 mb-4">
        In Chapter 7 bankruptcy, most unsecured amounts owed are discharged (eliminated). Some
        amounts owed are non-dischargeable under federal law.
      </p>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-green-50 p-3 rounded">
          <div className="text-2xl font-bold text-green-700">{dischargeable.length}</div>
          <div className="text-sm text-green-600">Dischargeable amounts</div>
        </div>
        <div className="bg-amber-50 p-3 rounded">
          <div className="text-2xl font-bold text-amber-700">{nonDischargeable.length}</div>
          <div className="text-sm text-amber-600">Non-dischargeable amounts</div>
        </div>
      </div>

      {nonDischargeable.length > 0 && (
        <div className="mt-4">
          <h4 className="font-medium mb-2">Non-Dischargeable Amounts</h4>
          {nonDischargeable.map((debt) => (
            <div key={debt.debt_id} className="border-l-4 border-amber-400 pl-3 mb-3">
              <div className="font-medium">{debt.creditor}</div>
              <div className="text-sm text-gray-600">{debt.reason}</div>
              {debt.proceeding_needed && (
                <div className="text-sm text-amber-600 mt-1">
                  This amount owed may require a separate adversary proceeding to request discharge.
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
