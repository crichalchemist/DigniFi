import { describe, expect, it } from 'vitest';
import {
  SCHEDULE_I_GATE_J24,
  SCHEDULE_I_GATE_LINE_11,
  SCHEDULE_I_GATE_LINE_13,
} from '../../../../../constants/copy';
import { lineTwentyFourGate, scheduleIGate } from '../scheduleIGaps';

describe("step 2's gates (Schedule I lines 11 and 13)", () => {
  it('names line 11 first while nothing is answered, as Complete lists it', () => {
    expect(scheduleIGate({})).toBe(SCHEDULE_I_GATE_LINE_11);
  });

  it('names line 13 once line 11 is answered, whichever way', () => {
    expect(scheduleIGate({ line_11_answer: 'no' })).toBe(SCHEDULE_I_GATE_LINE_13);
    expect(scheduleIGate({ line_11_answer: 'yes', line_11_amount: '50.00' })).toBe(
      SCHEDULE_I_GATE_LINE_13
    );
  });

  it('is open for line 11 even when line 13 is answered', () => {
    expect(scheduleIGate({ line_13_answer: 'no' })).toBe(SCHEDULE_I_GATE_LINE_11);
  });

  it('treats a null answer as unanswered, as the server does', () => {
    expect(scheduleIGate({ line_11_answer: null, line_13_answer: null })).toBe(
      SCHEDULE_I_GATE_LINE_11
    );
  });

  it('is closed when both are answered, so a Yes with no amount still lets Continue through', () => {
    expect(scheduleIGate({ line_11_answer: 'yes', line_13_answer: 'yes' })).toBeNull();
    expect(scheduleIGate({ line_11_answer: 'no', line_13_answer: 'no' })).toBeNull();
  });

  it("never holds step 2 for step 4's line 24", () => {
    expect(scheduleIGate({ line_11_answer: 'no', line_13_answer: 'no' })).toBeNull();
  });
});

describe("step 4's gate (Schedule J line 24)", () => {
  it('is open until line 24 is answered', () => {
    expect(lineTwentyFourGate({})).toBe(SCHEDULE_I_GATE_J24);
    expect(lineTwentyFourGate({ schedule_j_line_24_answer: null })).toBe(SCHEDULE_I_GATE_J24);
  });

  it('is closed under either answer', () => {
    expect(lineTwentyFourGate({ schedule_j_line_24_answer: 'no' })).toBeNull();
    expect(lineTwentyFourGate({ schedule_j_line_24_answer: 'yes' })).toBeNull();
  });

  it("never holds step 4 for step 2's lines", () => {
    expect(lineTwentyFourGate({ schedule_j_line_24_answer: 'no' })).toBeNull();
  });
});
