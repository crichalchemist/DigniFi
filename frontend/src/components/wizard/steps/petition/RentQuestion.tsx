/**
 * Form 101 line 11 (forms step 4b spec §6.7), asked on Contracts & Leases after the contracts, in
 * the form's words: whether the filer rents their residence and, under its Yes, whether the
 * landlord has an eviction judgment. Under both Yes answers, the notice: the forms' own sentences,
 * quoted (formText.ts, owner answer Q2), DigniFi's own sentences and the court's two pages, in
 * PF2-T9-4's order. Information, never advice: nothing here says whether to stay or to pay. A
 * stored eviction Yes under a rent No shows nothing (spec §6.7). The step's one status region
 * names the gate (rentGap, PF2-T9-6).
 */
import type { FocusEvent } from 'react';
import { YesNoThenDetails } from '../../YesNoThenDetails';
import {
  COURT_FORM_101A_URL,
  COURT_FORM_101B_URL,
  FORM_101A_LINK,
  FORM_101A_NOT_YET,
  FORM_101A_SAYS,
  FORM_101B_LINK,
  FORM_101B_NOT_PREPARED,
} from '../../../../constants/copy';
import {
  FORM_101_LINE_11_EVICTION,
  FORM_101_LINE_11_NOTICE,
  FORM_101_LINE_11_RENT,
  FORM_101A_SERVICE_CONDITIONS,
  FORM_101A_SERVICE_SENTENCE,
  FORM_101B_STAY_SENTENCE,
} from '../../../../constants/formText';
import type { PetitionAnswers, YesNo } from '../../../../types/api';

interface RentQuestionProps {
  answers: PetitionAnswers;
  onChange: (next: PetitionAnswers) => void;
  /** The step has seen the filer pass the block (PF2-T8-10): an unanswered gate says so */
  touched: boolean;
  /** Focus has left the block */
  onLeave: () => void;
}

const yesNo = (value: unknown): YesNo | null => (value === 'yes' || value === 'no' ? value : null);

/** Form 101 line 11's Yes instruction, Form 101A's words, DigniFi's sentences and the two links */
// DRAFT: counsel C-40
function EvictionNotice() {
  // `.info-box` is a flex row, so the pieces sit in one child and read top to bottom
  return (
    <div className="info-box eviction-notice">
      <div>
        <blockquote>
          <p className="info-message">{FORM_101_LINE_11_NOTICE}</p>
        </blockquote>
        <p className="info-message">{FORM_101A_SAYS}</p>
        <blockquote>
          <p className="info-message">{FORM_101A_SERVICE_SENTENCE}</p>
          <ul>
            {FORM_101A_SERVICE_CONDITIONS.map((condition) => (
              <li key={condition}>{condition}</li>
            ))}
          </ul>
        </blockquote>
        <p className="info-message">{FORM_101A_NOT_YET}</p>
        <p className="info-message">
          <a href={COURT_FORM_101A_URL} target="_blank" rel="noopener noreferrer">
            {FORM_101A_LINK}
          </a>
        </p>
        <p className="info-message">{FORM_101A_SAYS}</p>
        <blockquote>
          <p className="info-message">{FORM_101B_STAY_SENTENCE}</p>
        </blockquote>
        <p className="info-message">{FORM_101B_NOT_PREPARED}</p>
        <p className="info-message">
          <a href={COURT_FORM_101B_URL} target="_blank" rel="noopener noreferrer">
            {FORM_101B_LINK}
          </a>
        </p>
      </div>
    </div>
  );
}

export function RentQuestion({ answers, onChange, touched, onLeave }: RentQuestionProps) {
  const set = (changes: Partial<PetitionAnswers>) => onChange({ ...answers, ...changes });
  const rent = yesNo(answers.rents_residence);
  const eviction = yesNo(answers.eviction_judgment);

  const leave = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) onLeave();
  };

  return (
    <div className="petition-questions" onBlur={leave}>
      <YesNoThenDetails
        question={FORM_101_LINE_11_RENT}
        name="rents_residence"
        value={rent}
        onChange={(next) => set({ rents_residence: next })}
        unanswered={touched && rent === null}
      >
        {rent === 'yes' && (
          <YesNoThenDetails
            question={FORM_101_LINE_11_EVICTION}
            name="eviction_judgment"
            value={eviction}
            onChange={(next) => set({ eviction_judgment: next })}
            unanswered={touched && eviction === null}
          >
            {eviction === 'yes' && <EvictionNotice />}
          </YesNoThenDetails>
        )}
      </YesNoThenDetails>
    </div>
  );
}
