import {
  CLERK_PHONE_EASTERN,
  CLERK_PHONE_WESTERN,
  PUBLIC_RECORD_NOTICE,
  PUBLIC_RECORD_NOTICE_WITH_CLERK,
} from '../../constants/copy';

interface PublicRecordNoticeProps {
  /** The county's division, which names the clerk's office; null before a county is chosen */
  division: 'Eastern' | 'Western' | null;
}

/**
 * Tells the filer that what is filed can be seen by the public, wherever an address is asked, with
 * the number of their own division's clerk once the county says which (4b-R6)
 */
export function PublicRecordNotice({ division }: PublicRecordNoticeProps) {
  const phone =
    division === 'Eastern'
      ? CLERK_PHONE_EASTERN
      : division === 'Western'
        ? CLERK_PHONE_WESTERN
        : null;
  return (
    <p role="note" className="form-help-text public-record-notice">
      {phone === null ? PUBLIC_RECORD_NOTICE : `${PUBLIC_RECORD_NOTICE_WITH_CLERK} ${phone}.`}
    </p>
  );
}
