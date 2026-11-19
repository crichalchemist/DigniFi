import { PUBLIC_RECORD_NOTICE } from '../../constants/copy';

/** Tells the filer that what is filed can be seen by the public, wherever an address is asked */
export function PublicRecordNotice() {
  return (
    <p role="note" className="form-help-text public-record-notice">
      {PUBLIC_RECORD_NOTICE}
    </p>
  );
}
