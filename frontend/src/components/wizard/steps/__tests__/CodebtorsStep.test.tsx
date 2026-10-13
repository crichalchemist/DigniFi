import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CodebtorsStep } from '../CodebtorsStep';
import type { Codebtor } from '../../../../types/api';

// The server refuses a codebtor whose name, street, city or ZIP is longer than its column
// holds, and the wizard can only say it couldn't save, so Continue would never succeed.
// Each box stops at that length instead.

const codebtor: Codebtor = {
  id: 3,
  name: 'Sam Doe',
  street_address: '1 Main St',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60601',
  relationship: 'relative',
};

describe('CodebtorsStep', () => {
  it('keeps each box within the length the server stores, so a long entry never blocks Continue', async () => {
    const onDataChange = vi.fn();
    render(
      <CodebtorsStep
        initialData={[codebtor]}
        onDataChange={onDataChange}
        onValidationChange={() => {}}
      />
    );

    const user = userEvent.setup();
    const typeOver = async (shown: string, text: string) => {
      await user.clear(screen.getByDisplayValue(shown));
      await user.paste(text);
    };
    await typeOver('Sam Doe', 'N'.repeat(300));
    await typeOver('1 Main St', 'S'.repeat(300));
    await typeOver('Chicago', 'C'.repeat(150));
    await typeOver('60601', '60601-1234-99');

    expect(onDataChange).toHaveBeenLastCalledWith([
      {
        ...codebtor,
        name: 'N'.repeat(255),
        street_address: 'S'.repeat(255),
        city: 'C'.repeat(100),
        zip_code: '60601-1234',
      },
    ]);
  });
});
