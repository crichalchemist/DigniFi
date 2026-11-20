import { createRef } from 'react';
import { render, screen } from '@testing-library/react';
import { YesNoThenDetails } from '../YesNoThenDetails';
import { NOT_ANSWERED_YET } from '../../../constants/copy';

function ask(props: Partial<Parameters<typeof YesNoThenDetails>[0]> = {}) {
  return render(
    <YesNoThenDetails
      question="Did you own a business?"
      name="owned_business"
      value={null}
      onChange={() => {}}
      {...props}
    />
  );
}

describe('YesNoThenDetails', () => {
  it('offers No before Yes with nothing checked while unanswered', () => {
    ask({ unanswered: true });
    const radios = screen.getAllByRole('radio');
    expect(radios.map((radio) => (radio as HTMLInputElement).value)).toEqual(['no', 'yes']);
    expect(radios.some((radio) => (radio as HTMLInputElement).checked)).toBe(false);
  });

  it('the details render inside the fieldset after the answer', () => {
    ask({ value: 'yes', children: <p>Say what kind of business.</p> });
    const fieldset = screen.getByRole('group', { name: /Did you own a business/ });
    expect(fieldset).toContainElement(screen.getByText('Say what kind of business.'));
    expect(screen.getByRole('radio', { name: 'Yes' })).toBeChecked();
  });

  it('says Not answered yet only when the caller says so', () => {
    const { unmount } = ask({ unanswered: true });
    expect(screen.getByText(NOT_ANSWERED_YET)).toBeInTheDocument();
    unmount();
    ask();
    expect(screen.queryByText(NOT_ANSWERED_YET)).not.toBeInTheDocument();
  });

  it('without unanswered nothing is added below the answer', () => {
    ask({ children: <span>details</span> });
    const fieldset = screen.getByRole('group', { name: /Did you own a business/ });
    expect(fieldset.textContent).toBe('Did you own a business?*NoYesdetails');
  });

  it('the legend takes focus through its ref', () => {
    const legendRef = createRef<HTMLLegendElement>();
    ask({ legendRef });
    legendRef.current?.focus();
    expect(document.activeElement).toBe(legendRef.current);
  });
});
