/**
 * Form 101 line 11 (forms step 4b spec §6.7), asked on Contracts & Leases after the contracts, in
 * the form's words: whether the filer rents their residence and, under its Yes, whether the
 * landlord has an eviction judgment. Under both Yes answers, the notice: the forms' own sentences,
 * quoted (formText.ts, owner answer Q2), DigniFi's own sentences and the court's two pages, in
 * PF2-T9-4's order, in two parts with Form 101A's landlord block between them (4b2-R4): the form
 * asks for the landlord's name and address before its certification. Form 101A's certification and
 * its two boxes come before paragraph (a), so (a)'s "both boxes above" has them (owner ruling Q11).
 * Information, never advice: nothing here says whether to stay or to pay. An eviction answer stored
 * under a rent No stays stored and never shows the notice (spec §6.7); it is hidden with a line
 * that offers Show and Delete (T9-eviction-hidden), and so are landlord answers kept under an
 * eviction No or a rent No (4b2-R6). The landlord is a detail, never a gate (§5.7). The step's one
 * status region names the gate (rentGap, PF2-T9-6).
 */
import { useState } from 'react';
import type { FocusEvent } from 'react';
import { FormField, FormSelect } from '../../../common';
import { YesNoThenDetails } from '../../YesNoThenDetails';
import {
  CLERK_PHONE_EASTERN,
  CLERK_PHONE_WESTERN,
  COURT_FORM_101A_URL,
  COURT_FORM_101B_URL,
  FORM_101A_BOXES_BLANK,
  FORM_101A_DEPOSIT,
  FORM_101A_DEPOSIT_WITH_CLERK,
  FORM_101A_LINK,
  FORM_101_LINE_11_LEAD,
  FORM_101A_SAYS,
  FORM_101B_LINK,
  FORM_101B_NOT_PREPARED,
  HIDDEN_ANSWERS,
  LANDLORD_PICK_HINT,
  LANDLORD_PICK_LABEL,
  LANDLORD_PICK_PLACEHOLDER,
} from '../../../../constants/copy';
import {
  FORM_101_LINE_11_EVICTION,
  FORM_101_LINE_11_NOTICE,
  FORM_101_LINE_11_RENT,
  FORM_101A_CERTIFICATION_BOX_1,
  FORM_101A_CERTIFICATION_BOX_2,
  FORM_101A_CERTIFICATION_HEADING,
  FORM_101A_CERTIFICATION_SENTENCE,
  FORM_101A_GATE_SENTENCE,
  FORM_101A_LANDLORD_ADDRESS,
  FORM_101A_LANDLORD_NAME,
  FORM_101A_SERVICE_CONDITIONS,
  FORM_101A_SERVICE_SENTENCE,
  FORM_101A_STAY_HEADING_A,
  FORM_101A_STAY_HEADING_B,
  FORM_101A_STAY_SENTENCE_A,
  FORM_101B_STAY_SENTENCE,
} from '../../../../constants/formText';
import { PETITION_TEXT_LIMITS } from '../../../../constants/petitionLimits';
import type { ContractRow, PetitionAnswers, YesNo } from '../../../../types/api';
import { landlordFromLease, residentialLeases } from './landlord';
import { PartyAddressFields } from './PartyAddressFields';
import { HiddenLine } from './PetitionQuestions';
import { LANDLORD_KEYS } from './petitionGaps';

interface RentQuestionProps {
  answers: PetitionAnswers;
  onChange: (next: PetitionAnswers) => void;
  /** The step has seen the filer pass the block (PF2-T8-10): an unanswered gate says so */
  touched: boolean;
  /** Focus has left the block */
  onLeave: () => void;
  /** The step's contracts, whose residential leases the landlord can be copied from (4b2-R7) */
  leaseRows: ContractRow[];
  /** The county's division, which names the clerk's number in the deposit sentence (4b2-R5) */
  division: 'Eastern' | 'Western' | null;
}

const yesNo = (value: unknown): YesNo | null => (value === 'yes' || value === 'no' ? value : null);

const NO_LANDLORD = Object.fromEntries(LANDLORD_KEYS.map((key) => [key, null])) as Pick<
  PetitionAnswers,
  (typeof LANDLORD_KEYS)[number]
>;

/** Form 101 line 11's Yes instruction, Form 101A's opening words, DigniFi's sentence and the link */
// DRAFT: counsel C-40
function NoticeHead() {
  // `.info-box` is a flex row, so the pieces sit in one child and read top to bottom
  return (
    <div className="info-box eviction-notice">
      <div>
        <p className="info-message">{FORM_101_LINE_11_LEAD}</p>
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
        <p className="info-message">
          <a href={COURT_FORM_101A_URL} target="_blank" rel="noopener noreferrer">
            {FORM_101A_LINK}
          </a>
        </p>
      </div>
    </div>
  );
}

/** The certification and its two boxes, DigniFi's words under them, then the stay passage */
// DRAFT: counsel C-40
// DRAFT: counsel C-46
function NoticeCertification({ division }: { division: 'Eastern' | 'Western' | null }) {
  const phone =
    division === 'Eastern'
      ? CLERK_PHONE_EASTERN
      : division === 'Western'
        ? CLERK_PHONE_WESTERN
        : null;
  return (
    <div className="info-box eviction-notice">
      <div>
        <p className="info-message">{FORM_101A_SAYS}</p>
        <blockquote>
          <p className="info-message">{FORM_101A_GATE_SENTENCE}</p>
          <p className="info-message">{FORM_101A_CERTIFICATION_HEADING}</p>
          <p className="info-message">{FORM_101A_CERTIFICATION_SENTENCE}</p>
          <ul>
            <li>{FORM_101A_CERTIFICATION_BOX_1}</li>
            <li>{FORM_101A_CERTIFICATION_BOX_2}</li>
          </ul>
        </blockquote>
        <p className="info-message">{FORM_101A_BOXES_BLANK}</p>
        <p className="info-message">
          {phone ? `${FORM_101A_DEPOSIT_WITH_CLERK} ${phone}.` : FORM_101A_DEPOSIT}
        </p>
        <p className="info-message">{FORM_101A_SAYS}</p>
        <blockquote>
          <p className="info-message">{FORM_101A_STAY_HEADING_A}</p>
          <p className="info-message">{FORM_101A_STAY_SENTENCE_A}</p>
          <p className="info-message">{FORM_101A_STAY_HEADING_B}</p>
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

export function RentQuestion({
  answers,
  onChange,
  touched,
  onLeave,
  leaseRows,
  division,
}: RentQuestionProps) {
  const [shown, setShown] = useState(false);
  const set = (changes: Partial<PetitionAnswers>) => onChange({ ...answers, ...changes });
  const rent = yesNo(answers.rents_residence);
  const eviction = yesNo(answers.eviction_judgment);
  const pair = rent === 'yes' && eviction === 'yes';
  const hasLandlord = LANDLORD_KEYS.some((key) => {
    const value = answers[key];
    return typeof value === 'string' && value.trim() !== '';
  });
  const leases = residentialLeases(leaseRows);

  const leave = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) onLeave();
  };

  return (
    <div className="petition-questions" onBlur={leave}>
      <YesNoThenDetails
        question={FORM_101_LINE_11_RENT}
        name="rents_residence"
        value={rent}
        onChange={(next) => {
          // Show opens a hidden eviction answer once: a new rent answer hides it again
          setShown(false);
          set({ rents_residence: next });
        }}
        unanswered={touched && rent === null}
      >
        {rent === 'yes' || (rent === 'no' && shown) ? (
          <YesNoThenDetails
            question={FORM_101_LINE_11_EVICTION}
            name="eviction_judgment"
            value={eviction}
            onChange={(next) => set({ eviction_judgment: next })}
            unanswered={rent === 'yes' && touched && eviction === null}
            required={rent === 'yes'}
          >
            {pair && <NoticeHead />}
            {(pair || (shown && (eviction === 'yes' || hasLandlord))) && (
              // DRAFT: counsel C-46
              <div className="landlord-block">
                {leases.length > 0 && (
                  <FormSelect
                    label={LANDLORD_PICK_LABEL}
                    name="landlord_pick"
                    options={leases.map((lease) => ({ value: lease.key, label: lease.label }))}
                    placeholder={LANDLORD_PICK_PLACEHOLDER}
                    helpText={LANDLORD_PICK_HINT}
                    value=""
                    onChange={(key) => {
                      const lease = leases.find((candidate) => candidate.key === key);
                      if (lease) set(landlordFromLease(lease.row));
                    }}
                  />
                )}
                <FormField
                  label={FORM_101A_LANDLORD_NAME}
                  name="landlord_name"
                  type="text"
                  maxLength={PETITION_TEXT_LIMITS.landlord_name}
                  value={answers.landlord_name ?? ''}
                  onChange={(e) => set({ landlord_name: e.target.value })}
                />
                <p id="landlord-address-label" className="form-label">
                  {FORM_101A_LANDLORD_ADDRESS}
                </p>
                <div role="group" aria-labelledby="landlord-address-label">
                  <PartyAddressFields
                    answers={answers}
                    onChange={set}
                    streetKey="landlord_street"
                    cityKey="landlord_city"
                    stateKey="landlord_state"
                    zipKey="landlord_zip"
                  />
                </div>
              </div>
            )}
            {pair && <NoticeCertification division={division} />}
            {rent === 'yes' && eviction === 'no' && hasLandlord && !shown && (
              <HiddenLine
                sentence={HIDDEN_ANSWERS}
                onShow={() => setShown(true)}
                onDelete={() => set(NO_LANDLORD)}
              />
            )}
          </YesNoThenDetails>
        ) : (
          rent === 'no' &&
          (eviction !== null || hasLandlord) && (
            <HiddenLine
              sentence={HIDDEN_ANSWERS}
              onShow={() => setShown(true)}
              onDelete={() => set({ eviction_judgment: null, ...NO_LANDLORD })}
            />
          )
        )}
      </YesNoThenDetails>
    </div>
  );
}
