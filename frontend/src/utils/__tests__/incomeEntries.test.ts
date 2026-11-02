import {
  entriesToSend,
  flooredNet,
  hydrateEntries,
  kindNet,
  newIncomeEntry,
} from '../incomeEntries';
import type { EntryRow } from '../incomeEntries';
import type { IncomeEntry } from '../../types/api';

const rideshare = [
  {
    id: 1,
    kind: 'business',
    description: 'Rideshare and delivery driving',
    gross: '4200.00',
    expenses: '830.00',
    current_gross: null,
    current_expenses: null,
  },
] as unknown as IncomeEntry[];

describe('the Income step’s business and rental list', () => {
  it('an entry nobody answered is not sent, and an unanswered list stays null', () => {
    expect(entriesToSend([newIncomeEntry('new-1')], false)).toBeNull();
    expect(entriesToSend([newIncomeEntry('new-1')], true)).toEqual([]);
  });

  it('a touched entry is sent with every question, null for the unanswered ones', () => {
    expect(entriesToSend([{ ...newIncomeEntry('new-1'), kind: 'business' }], false)).toEqual([
      {
        _key: 'new-1',
        kind: 'business',
        description: null,
        gross: null,
        expenses: null,
        current_gross: null,
        current_expenses: null,
      },
    ]);
  });

  it('a loaded entry is always sent, with its id', () => {
    const loaded = hydrateEntries([
      {
        id: 4,
        kind: null,
        description: null,
        gross: null,
        expenses: null,
        current_gross: null,
        current_expenses: null,
      },
    ]);
    const sent = entriesToSend(loaded, false);
    expect(sent).toHaveLength(1);
    expect(sent?.[0].id).toBe(4);
    expect(sent?.[0]._key).toBe('4');
    // A list never loaded has no rows
    expect(hydrateEntries(null)).toEqual([]);
    expect(hydrateEntries(undefined)).toEqual([]);
  });

  it('loaded amounts become numbers, so they add', () => {
    const rows = hydrateEntries(rideshare);
    expect(rows[0].gross).toBe(4200);
    expect(rows[0].expenses).toBe(830);
    expect(kindNet(rows, 'business', false)).toBe(3370);
  });

  it('the floor is on each kind’s sum, never one entry, and a loss never crosses kinds', () => {
    const rows: EntryRow[] = [
      { ...newIncomeEntry('a'), kind: 'business', gross: 1000, expenses: 1500 },
      { ...newIncomeEntry('b'), kind: 'business', gross: 2000, expenses: 1200 },
      { ...newIncomeEntry('c'), kind: 'rental', gross: 500, expenses: 900 },
    ];
    expect(kindNet(rows, 'business', false)).toBe(300);
    expect(flooredNet(rows, 'business', false)).toBe(300);
    expect(kindNet(rows, 'rental', false)).toBe(-400);
    expect(flooredNet(rows, 'rental', false)).toBe(0);

    // The current pair is read on its own, and a blank counts as 0
    const now: EntryRow[] = [
      { ...rows[0], current_gross: 700 },
      { ...rows[1], current_expenses: 100 },
    ];
    expect(kindNet(now, 'business', true)).toBe(600);
    expect(kindNet(now, 'rental', true)).toBe(0);
  });

  it('a body built from loaded rows equals one built again', () => {
    const first = JSON.stringify(entriesToSend(hydrateEntries(rideshare), false));
    const second = JSON.stringify(entriesToSend(hydrateEntries(rideshare), false));
    expect(first).toBe(second);
    const [row] = entriesToSend(hydrateEntries(rideshare), false) ?? [];
    expect(Object.keys(row)).toEqual([
      '_key',
      'id',
      'kind',
      'description',
      'gross',
      'expenses',
      'current_gross',
      'current_expenses',
    ]);
  });
});
