import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { SectionIntro } from '../SectionIntro';
import { FramingLine } from '../FramingLine';
import { PublicRecordNotice } from '../PublicRecordNotice';
import { WhatDoesThisMean } from '../WhatDoesThisMean';
import {
  CLERK_PHONE_EASTERN,
  CLERK_PHONE_WESTERN,
  PUBLIC_RECORD_NOTICE,
  PUBLIC_RECORD_NOTICE_WITH_CLERK,
  SECTION_INTRO_PAUSE,
  WHAT_DOES_THIS_MEAN,
} from '../../../constants/copy';

describe('the frame components', () => {
  it('SectionIntro prints what the step asks, why, how long and that the filer can pause', () => {
    render(
      <SectionIntro asks="This step asks about your business." why="The court asks." minutes={5} />
    );
    expect(screen.getByText('This step asks about your business.')).toBeInTheDocument();
    expect(screen.getByText('The court asks.')).toBeInTheDocument();
    expect(screen.getByText('This step takes about 5 minutes.')).toBeInTheDocument();
    expect(screen.getByText(SECTION_INTRO_PAUSE)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('{n}');
  });

  it('FramingLine renders its child as help text', () => {
    render(<FramingLine>The court asks every filer this.</FramingLine>);
    const line = screen.getByText('The court asks every filer this.');
    expect(line).toHaveClass('form-help-text');
  });

  it('PublicRecordNotice renders the notice as a note', () => {
    render(<PublicRecordNotice division={null} />);
    expect(screen.getByRole('note')).toHaveTextContent(PUBLIC_RECORD_NOTICE);
  });

  it('PublicRecordNotice names the clerk by division and no number before a county is chosen', () => {
    // A Boone County filer files in Rockford, so the Chicago clerk's number would send them to
    // the wrong office (Review Focus 8)
    const { rerender } = render(<PublicRecordNotice division="Western" />);
    expect(screen.getByRole('note')).toHaveTextContent(
      `${PUBLIC_RECORD_NOTICE_WITH_CLERK} ${CLERK_PHONE_WESTERN}.`
    );
    expect(screen.getByRole('note')).not.toHaveTextContent(CLERK_PHONE_EASTERN);

    rerender(<PublicRecordNotice division="Eastern" />);
    expect(screen.getByRole('note')).toHaveTextContent(
      `${PUBLIC_RECORD_NOTICE_WITH_CLERK} ${CLERK_PHONE_EASTERN}.`
    );

    rerender(<PublicRecordNotice division={null} />);
    const note = screen.getByRole('note');
    expect(note.textContent).toBe(PUBLIC_RECORD_NOTICE);
    expect(note.textContent).toMatch(/options exist\.$/);
    expect(note.textContent).not.toMatch(/\(\d{3}\)/);
  });

  it('WhatDoesThisMean is collapsed until the filer opens it, then shows the words and citation', async () => {
    render(
      <WhatDoesThisMean citation="11 U.S.C. section 101">
        The words of the statute.
      </WhatDoesThisMean>
    );
    const details = screen.getByText(WHAT_DOES_THIS_MEAN).closest('details');
    expect(details).not.toHaveAttribute('open');
    await userEvent.click(screen.getByText(WHAT_DOES_THIS_MEAN));
    expect(details).toHaveAttribute('open');
    expect(screen.getByText('The words of the statute.')).toBeVisible();
    expect(screen.getByText('11 U.S.C. section 101')).toBeVisible();
  });

  it('has no accessibility violations with the four together', async () => {
    const { container } = render(
      <main>
        <SectionIntro
          asks="This step asks about your business."
          why="The court asks."
          minutes={5}
        />
        <FramingLine>The court asks every filer this.</FramingLine>
        <PublicRecordNotice division={null} />
        <WhatDoesThisMean citation="11 U.S.C. section 101">
          The words of the statute.
        </WhatDoesThisMean>
      </main>
    );
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  });
});
