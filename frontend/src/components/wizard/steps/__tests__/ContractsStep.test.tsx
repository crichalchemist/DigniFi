import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ContractsStep } from '../ContractsStep';
import type { ContractRow } from '../../../../types/api';

// The server refuses a contract whose other party's name is longer than its column holds,
// and the wizard can only say it couldn't save, so Continue would never succeed. The box
// stops at that length instead.

const leaseRow: ContractRow = {
  id: 4,
  counterparty_name: 'Oak Street Apartments',
  contract_type: 'lease',
  description: 'Apartment lease',
  _key: '4',
};

/** The wizard's part: it holds the rows the step shows */
function StepWithRows({
  initial,
  onRowsChange,
  onValidationChange,
}: {
  initial: ContractRow[];
  onRowsChange: (rows: ContractRow[]) => void;
  onValidationChange: (isValid: boolean) => void;
}) {
  const [rows, setRows] = useState<ContractRow[]>(initial);
  return (
    <ContractsStep
      rows={rows}
      onRowsChange={(next) => {
        setRows(next);
        onRowsChange(next);
      }}
      onValidationChange={onValidationChange}
    />
  );
}

describe('ContractsStep', () => {
  it("keeps the other party's name within the length the server stores, so a long name never blocks Continue", async () => {
    const onRowsChange = vi.fn();
    render(
      <StepWithRows
        initial={[leaseRow]}
        onRowsChange={onRowsChange}
        onValidationChange={() => {}}
      />
    );

    const user = userEvent.setup();
    await user.clear(screen.getByDisplayValue('Oak Street Apartments'));
    await user.paste('O'.repeat(300));

    expect(onRowsChange).toHaveBeenLastCalledWith([
      { ...leaseRow, counterparty_name: 'O'.repeat(255) },
    ]);
  });

  it("ties the missing-name message to the other party's name box, so a screen reader hears it there", async () => {
    render(
      <StepWithRows initial={[leaseRow]} onRowsChange={() => {}} onValidationChange={() => {}} />
    );

    const nameBox = screen.getByRole('textbox', { name: 'Counterparty Name' });
    expect(nameBox).toBeValid();

    await userEvent.setup().clear(nameBox);

    expect(nameBox).toBeInvalid();
    expect(nameBox).toHaveAccessibleDescription('Please enter the name of the other party');
  });

  it("won't let a stored contract go without its other party's name, even with nothing else typed", async () => {
    const gym: ContractRow = {
      id: 5,
      counterparty_name: 'Metro Gym',
      contract_type: 'contract',
      description: '',
      _key: '5',
    };
    const onValidationChange = vi.fn();
    render(
      <StepWithRows
        initial={[gym]}
        onRowsChange={() => {}}
        onValidationChange={onValidationChange}
      />
    );

    const nameBox = screen.getByRole('textbox', { name: 'Counterparty Name' });
    await userEvent.setup().clear(nameBox);

    expect(nameBox).toBeInvalid();
    expect(nameBox).toHaveAccessibleDescription('Please enter the name of the other party');
    expect(onValidationChange).toHaveBeenLastCalledWith(false);
  });

  it('names every box for a screen reader', () => {
    render(
      <StepWithRows initial={[leaseRow]} onRowsChange={() => {}} onValidationChange={() => {}} />
    );

    expect(screen.getByLabelText('Type')).toBe(screen.getByRole('combobox', { name: 'Type' }));
    expect(screen.getByLabelText('Description')).toBe(
      screen.getByRole('textbox', { name: 'Description' })
    );
  });

  it('gives a lease, not a loan, as its example', () => {
    render(
      <StepWithRows initial={[leaseRow]} onRowsChange={() => {}} onValidationChange={() => {}} />
    );

    expect(screen.getByPlaceholderText('e.g., Apartment lease, car lease')).toBeInTheDocument();
  });
});
