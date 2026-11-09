/**
 * What the claim steps (Amounts Owed, Contracts, Codebtors) share: how a row is named in a
 * sentence, when an address or a link counts as given, and the bounds the server holds. Each
 * function copies one in apps/intake/claims.py (3c3 Task 6), so a step's sentence and Complete's
 * agree.
 */
import { ASSET_LINES, type AssetLineShape } from '../../../../constants/assetLines';
import { REVIEW_ASSET_ROW } from '../../../../constants/copy';
import { fill, rowName } from '../assets/assetGaps';
import type { AssetInfo, WizardRow } from '../../../../types/api';

export { fill };

// The widest date the server stores (DebtInfo.DATE_INCURRED_MAX_LENGTH, R21)
export const DATE_INCURRED_MAX_LENGTH = 15;
// The most people or companies one debt can list (MAX_NOTICE_PARTIES, R5)
export const MAX_NOTICE_PARTIES = 10;

export interface AddressValue {
  street_address: string;
  street_2: string;
  city: string;
  state: string;
  zip_code: string;
  outside_us: boolean;
}

/** The row's name once trimmed, or the words for a row with none */
export function claimRowName(name: string | undefined | null, nameless: string): string {
  return (name ?? '').trim() || nameless;
}

const blank = (value: string | undefined | null) => (value ?? '').trim() === '';

/**
 * Whether the address lacks what the court needs: the street or city blank, or, unless it is
 * ticked outside the US, a state that isn't two letters or a blank ZIP
 */
export function addressMissing(address: Partial<AddressValue>): boolean {
  if (blank(address.street_address) || blank(address.city)) return true;
  if (address.outside_us) return false;
  return !/^\p{L}{2}$/u.test((address.state ?? '').trim()) || blank(address.zip_code);
}

/** A link is live when the row it names is still held on the Assets step (or the list it names) */
export function linkIsLive(id: number | null | undefined, held: { id?: number }[]): boolean {
  return id !== null && id !== undefined && held.some((row) => row.id === id);
}

/** Whether a line's own rows ask who has an interest. An old row, with no line, asks none. */
export function asksWho(shape: AssetLineShape | undefined): boolean {
  return shape === 'place' || shape === 'vehicle' || shape === 'vehicle_no_mileage';
}

/** Rows in the server's id order: ids ascending, rows with no id after them as held (B37) */
export function inIdOrder<T extends { id?: number }>(rows: T[]): T[] {
  const stored = rows.filter((row) => row.id !== undefined);
  const added = rows.filter((row) => row.id === undefined);
  return [...stored.sort((a, b) => (a.id as number) - (b.id as number)), ...added];
}

/** The picker's words for an Assets row: its line, then what tells it from the others */
export function assetLabel(row: WizardRow<AssetInfo>): string {
  const shape = ASSET_LINES.find((line) => line.key === row.ab_line)?.shape;
  let name = '';
  if (shape === 'vehicle' || shape === 'vehicle_no_mileage') {
    const { year, make, model } = row.details ?? {};
    name = [year, make, model]
      .map((part) => (part ?? '').trim())
      .filter((part) => part !== '')
      .join(' ');
  }
  return fill(REVIEW_ASSET_ROW, { key: row.ab_line ?? '', name: name || rowName(row) });
}
