import { useState, useEffect } from 'react';
import { useIntake } from '../../context/IntakeContext';
import { askModulesAPI } from '../../api/client';
import type { FormUISpec, AnswerPayload } from '../../types/api';

export function DynamicFormWizard({
  formType,
  onComplete,
}: {
  formType: string;
  onComplete: () => void;
}) {
  const { session } = useIntake();
  const [uiSpec, setUiSpec] = useState<FormUISpec | null>(null);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [repeatCounts, setRepeatCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    askModulesAPI
      .getUISpec(formType)
      .then((spec) => {
        setUiSpec(spec);
        // Hydrate initial formData from session
        // (A fully robust hydration would extract from session object based on bindings,
        // for now we initialize empty and rely on contextual form progression)
        setLoading(false);
      })
      .catch(console.error);
  }, [formType, session]);

  if (loading || !uiSpec) return <div>Loading wizard...</div>;

  const isConditionMet = (condition?: string | null) => {
    if (!condition) return true;

    // Check against session context first for known booleans
    if (session?.sofa_report && condition in session.sofa_report) {
      return (session.sofa_report as Record<string, unknown>)[condition] === true;
    }

    // Check local formData buffer
    const conditionKey = Object.keys(formData).find((k) => k.endsWith(`.${condition}`));
    if (conditionKey) {
      const localVal = formData[conditionKey];
      return localVal === 'true' || localVal === 'Yes';
    }

    return false; // Default fail if condition not found
  };

  const steps = uiSpec.steps.filter((step) =>
    step.fields.some((f) => isConditionMet(f.conditional_on))
  );

  if (steps.length === 0) return <div>No steps required.</div>;

  const currentStep = steps[currentStepIndex];

  const handleNext = async () => {
    if (!session) return;

    // Convert local formData dict to array of payloads
    const payloads: AnswerPayload[] = Object.entries(formData).map(([binding, value]) => {
      return { form_type: formType, binding, value };
    });

    setSaving(true);
    try {
      if (payloads.length > 0) {
        await askModulesAPI.bulkUpsertAnswers(session.id, payloads);
      }
      if (currentStepIndex < steps.length - 1) {
        setCurrentStepIndex((curr) => curr + 1);
      } else {
        onComplete();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="dynamic-wizard p-6 bg-white shadow rounded">
      <h2 className="text-xl font-bold mb-4">{currentStep.title}</h2>
      {currentStep.fields
        .filter((f) => isConditionMet(f.conditional_on))
        .map((field) => {
          if (field.widget === 'repeat_group') {
            const count = repeatCounts[field.binding] || 1;
            const subfields = field.fields || [];
            return (
              <div key={field.binding} className="mb-4 border-l-4 border-blue-500 pl-4 py-2">
                <label className="block mb-2 font-medium">{field.prompt}</label>
                {field.help_text && <p className="text-sm text-gray-500 mb-2">{field.help_text}</p>}
                {Array.from({ length: count }).map((_, rowIndex) => (
                  <div
                    key={rowIndex}
                    className="mb-4 p-4 border rounded bg-gray-50 flex flex-wrap gap-4"
                  >
                    {subfields.map((subfield) => {
                      const bindingKey = subfield.binding.replace('[]', `[${rowIndex}]`);
                      return (
                        <div key={subfield.binding} className="flex-1 min-w-[200px]">
                          <label className="block mb-1 text-sm font-medium">
                            {subfield.prompt}
                          </label>
                          <input
                            type="text"
                            className="w-full border p-2 rounded text-sm"
                            value={formData[bindingKey] || ''}
                            onChange={(e) =>
                              setFormData({ ...formData, [bindingKey]: e.target.value })
                            }
                          />
                        </div>
                      );
                    })}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() =>
                    setRepeatCounts((prev) => ({ ...prev, [field.binding]: count + 1 }))
                  }
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  + Add another
                </button>
              </div>
            );
          }

          if (field.widget === 'checkbox') {
            return (
              <div key={field.binding} className="mb-4">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    className="form-checkbox"
                    checked={formData[field.binding] === 'true'}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        [field.binding]: e.target.checked ? 'true' : 'false',
                      })
                    }
                  />
                  <span className="font-medium">{field.prompt}</span>
                </label>
              </div>
            );
          }

          if (field.widget === 'radio') {
            const options = field.options || [
              { label: 'Yes', value: 'Yes' },
              { label: 'No', value: 'No' },
            ];
            return (
              <div key={field.binding} className="mb-4">
                <label className="block mb-2 font-medium">{field.prompt}</label>
                {field.help_text && <p className="text-sm text-gray-500 mb-2">{field.help_text}</p>}
                <div className="space-y-2">
                  {options.map((opt) => (
                    <label key={opt.value} className="flex items-center space-x-2">
                      <input
                        type="radio"
                        name={field.binding}
                        className="form-radio"
                        value={opt.value}
                        checked={formData[field.binding] === opt.value}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            [field.binding]: e.target.value,
                          })
                        }
                      />
                      <span>{opt.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            );
          }

          return (
            <div key={field.binding} className="mb-4">
              <label className="block mb-2 font-medium">{field.prompt}</label>
              {field.help_text && <p className="text-sm text-gray-500 mb-2">{field.help_text}</p>}
              <input
                type="text"
                className="w-full border p-2 rounded"
                value={formData[field.binding] || ''}
                onChange={(e) => setFormData({ ...formData, [field.binding]: e.target.value })}
              />
            </div>
          );
        })}
      <div className="mt-6 flex justify-end">
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          onClick={handleNext}
          disabled={saving}
        >
          {saving ? 'Saving...' : currentStepIndex < steps.length - 1 ? 'Next' : 'Complete'}
        </button>
      </div>
    </div>
  );
}
