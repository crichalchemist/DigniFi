import { SECTION_INTRO_PAUSE, SECTION_INTRO_TIME } from '../../constants/copy';

interface SectionIntroProps {
  /** What the step asks about */
  asks: string;
  /** Why the court's forms ask it */
  why: string;
  /** How long the step takes: 2 or more, since the sentence says "minutes" */
  minutes: number;
}

/** The four lines every new step opens with: what it asks, why, how long, and that it can wait */
export function SectionIntro({ asks, why, minutes }: SectionIntroProps) {
  return (
    <div className="section-intro">
      <p className="section-description">{asks}</p>
      <p className="form-help-text">{why}</p>
      <p className="form-help-text">{SECTION_INTRO_TIME.replace('{n}', String(minutes))}</p>
      <p className="form-help-text">{SECTION_INTRO_PAUSE}</p>
    </div>
  );
}
