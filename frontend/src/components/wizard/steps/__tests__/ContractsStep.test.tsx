import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ContractsStep } from '../ContractsStep';
import type { ExecutoryContract } from '../../../../types/api';

// The server refuses a contract whose other party's name is longer than its column holds,
// and the wizard can only say it couldn't save, so Continue would never succeed. The box
// stops at that length instead.

const lease: ExecutoryContract = {
  id: 4,
  counterparty_name: 'Oak Street Apartments',
  contract_type: 'lease',
  description: 'Apartment lease',
};

describe('ContractsStep', () => {
  it("keeps the other party's name within the length the server stores, so a long name never blocks Continue", async () => {
    const onDataChange = vi.fn();
    render(
      <ContractsStep
        initialData={[lease]}
        onDataChange={onDataChange}
        onValidationChange={() => {}}
      />
    );

    const user = userEvent.setup();
    await user.clear(screen.getByDisplayValue('Oak Street Apartments'));
    await user.paste('O'.repeat(300));

    expect(onDataChange).toHaveBeenLastCalledWith([
      { ...lease, counterparty_name: 'O'.repeat(255) },
    ]);
  });

  it("ties the missing-name message to the other party's name box, so a screen reader hears it there", async () => {
    render(
      <ContractsStep initialData={[lease]} onDataChange={() => {}} onValidationChange={() => {}} />
    );

    const nameBox = screen.getByRole('textbox', { name: 'Counterparty Name' });
    expect(nameBox).toBeValid();

    await userEvent.setup().clear(nameBox);

    expect(nameBox).toBeInvalid();
    expect(nameBox).toHaveAccessibleDescription('Please enter the name of the other party');
  });
});
