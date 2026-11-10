import { legacyGaps } from '../legacyGaps';
import { fill } from '../claimNames';
import type { LinkedSums } from '../linkedPayments';
import * as copy from '../../../../../constants/copy';

// A stored car or other-property payment the links don't cover is named on Amounts Owed, so the
// filer can add the rest to a row or remove the figure.

// Every sum differs, so a comparison with the wrong sum fails
const sums = (over: Partial<LinkedSums> = {}): LinkedSums => ({
  allLinked: 1800,
  vehicleTotal: 1000,
  otherRealProperty: 500,
  firstMortgage: 300,
  ...over,
});

describe('legacyGaps', () => {
  it("names a stored car payment the links don't cover", () => {
    const result = legacyGaps(
      { vehicle_payment: '350.00', other_property_mortgages: null },
      sums({ vehicleTotal: 200 })
    );

    expect(result).toEqual([
      {
        field: 'vehicle_payment',
        sentence: fill(copy.CLAIM_GAP_LEGACY_VEHICLE, { typed: '350.00', linked: '200.00' }),
      },
    ]);
  });

  it('compares the other-property figure with mortgages on other property', () => {
    const result = legacyGaps(
      { vehicle_payment: null, other_property_mortgages: '600.00' },
      sums()
    );

    expect(result).toEqual([
      {
        field: 'other_property_mortgages',
        sentence: fill(copy.CLAIM_GAP_LEGACY_OTHER, { typed: '600.00', linked: '500.00' }),
      },
    ]);
  });

  it('names nothing once the links cover it', () => {
    const result = legacyGaps(
      { vehicle_payment: '350.00', other_property_mortgages: null },
      sums({ vehicleTotal: 350 })
    );

    expect(result).toEqual([]);
  });

  it('names nothing with no stored figure', () => {
    expect(legacyGaps({ vehicle_payment: null, other_property_mortgages: null }, sums())).toEqual(
      []
    );
    expect(legacyGaps(undefined, sums())).toEqual([]);
  });

  it("writes the figures as the server's sentence does", () => {
    const result = legacyGaps(
      { vehicle_payment: '1200.00', other_property_mortgages: null },
      sums({ vehicleTotal: 0 })
    );

    expect(result[0].sentence).toBe(
      fill(copy.CLAIM_GAP_LEGACY_VEHICLE, { typed: '1,200.00', linked: '0.00' })
    );
    expect(result[0].sentence).not.toContain('1200.00');
  });

  it('lists the car payment before the other-property mortgages', () => {
    const result = legacyGaps(
      { vehicle_payment: '5000.00', other_property_mortgages: '6000.00' },
      sums()
    );

    expect(result.map((gap) => gap.field)).toEqual(['vehicle_payment', 'other_property_mortgages']);
  });
});
