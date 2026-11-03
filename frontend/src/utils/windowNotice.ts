import type { IncomePeriod } from '../types/api';
import {
  WINDOW_NOTICE_ANSWERED_LEAD,
  WINDOW_NOTICE_CHECK,
  WINDOW_NOTICE_NOW_LEAD,
  WINDOW_NOTICE_UNANSWERED_LEAD,
} from '../constants/copy';
import { formatIsoDate } from './formatIsoDate';

const inWords = (period: IncomePeriod) =>
  `${formatIsoDate(period.start)} through ${formatIsoDate(period.end)}`;

/**
 * What to tell the filer about the six months their income figures cover (3e2 spec §10): null
 * when the months they confirmed are the months in force, a request to check when they never
 * confirmed any, and both windows in words when the months have moved.
 */
export function windowNotice(answeredFor: IncomePeriod | null, now: IncomePeriod): string | null {
  if (answeredFor === null) return `${WINDOW_NOTICE_UNANSWERED_LEAD} ${inWords(now)}.`;
  if (answeredFor.start === now.start && answeredFor.end === now.end) return null;
  return `${WINDOW_NOTICE_ANSWERED_LEAD} ${inWords(answeredFor)}. ${WINDOW_NOTICE_NOW_LEAD} ${inWords(now)}. ${WINDOW_NOTICE_CHECK}`;
}
