import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CodebtorsStep } from '../CodebtorsStep';
import type { CodebtorRow } from '../../../../types/api';

// The server refuses a codebtor whose name, street, city or ZIP is longer than its column
// holds, and the wizard can only say it couldn't save, so Continue would never succeed.
// Each box stops at that length instead.

const codebtor: CodebtorRow = {
  id: 3,
  name: 'Sam Doe',
  street_address: '1 Main St',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60601',
  relationship: 'relative',
  _key: '3',
};

/** The wizard's part: it holds the rows the step shows */
function StepWithRows({
  initial,
  onRowsChange = () => {},
  onValidationChange = () => {},
}: {
  initial: CodebtorRow[];
  onRowsChange?: (rows: CodebtorRow[]) => void;
  onValidationChange?: (isValid: boolean) => void;
}) {
  const [rows, setRows] = useState<CodebtorRow[]>(initial);
  return (
    <CodebtorsStep
      rows={rows}
      onRowsChange={(next) => {
        setRows(next);
        onRowsChange(next);
      }}
      onValidationChange={onValidationChange}
    />
  );
}

describe('CodebtorsStep', () => {
  it('keeps each box within the length the server stores, so a long entry never blocks Continue', async () => {
    const onRowsChange = vi.fn();
    render(<StepWithRows initial={[codebtor]} onRowsChange={onRowsChange} />);

    const user = userEvent.setup();
    const typeOver = async (shown: string, text: string) => {
      await user.clear(screen.getByDisplayValue(shown));
      await user.paste(text);
    };
    await typeOver('Sam Doe', 'N'.repeat(300));
    await typeOver('1 Main St', 'S'.repeat(300));
    await typeOver('Chicago', 'C'.repeat(150));
    await typeOver('60601', '60601-1234-99');

    expect(onRowsChange).toHaveBeenLastCalledWith([
      {
        ...codebtor,
        name: 'N'.repeat(255),
        street_address: 'S'.repeat(255),
        city: 'C'.repeat(100),
        zip_code: '60601-1234',
      },
    ]);
  });

  it("ties the missing-name message to the person's name box, so a screen reader hears it there", async () => {
    render(<StepWithRows initial={[codebtor]} />);

    const nameBox = screen.getByRole('textbox', { name: 'Full Name' });
    expect(nameBox).toBeValid();

    await userEvent.setup().clear(nameBox);

    expect(nameBox).toBeInvalid();
    expect(nameBox).toHaveAccessibleDescription("Please enter this person's full name");
  });

  it("the codebtors step no longer promises a joint filer's spouse appears", () => {
    render(<StepWithRows initial={[]} />);
    expect(
      screen.getByText('List anyone who is jointly liable on any of your debts.')
    ).toBeInTheDocument();
    expect(screen.queryByText(/filed jointly/i)).toBeNull();
  });

  it("won't let a stored codebtor go without a name, even with no address", async () => {
    const stored: CodebtorRow = {
      id: 3,
      name: 'Sam Doe',
      street_address: '',
      city: '',
      state: '',
      zip_code: '',
      relationship: 'relative',
      _key: '3',
    };
    const onValidationChange = vi.fn();
    render(<StepWithRows initial={[stored]} onValidationChange={onValidationChange} />);

    const nameBox = screen.getByRole('textbox', { name: 'Full Name' });
    await userEvent.setup().clear(nameBox);

    expect(nameBox).toBeInvalid();
    expect(nameBox).toHaveAccessibleDescription("Please enter this person's full name");
    expect(onValidationChange).toHaveBeenLastCalledWith(false);
  });

  it('names every box for a screen reader', () => {
    render(<StepWithRows initial={[codebtor]} />);

    expect(screen.getByLabelText('Relationship')).toBe(
      screen.getByRole('combobox', { name: 'Relationship' })
    );
    for (const label of ['Street Address', 'City', 'State', 'ZIP']) {
      expect(screen.getByLabelText(label)).toBe(screen.getByRole('textbox', { name: label }));
    }
  });
});
