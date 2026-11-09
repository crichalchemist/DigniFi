/**
 * The words the claim steps and Review use for the server's choices. The server holds the keys
 * in `apps/intake/models.py`; `test_claims_frontend_copy.py` pins the keys, in order.
 */
import type { CodebtorRelationship, ContractType, DebtInfo, ExecutoryContract } from '../types/api';

export const DEBT_TYPE_WORDS: Record<DebtInfo['debt_type'], string> = {
  credit_card: 'Credit card',
  medical: 'Medical bill',
  personal_loan: 'Personal loan',
  student_loan: 'Student loan',
  auto_loan: 'Car or vehicle loan',
  mortgage: 'Mortgage or home loan',
  utility: 'Utility bill',
  other: 'Other amount owed',
};

export const CONTRACT_TYPE_WORDS: Record<ContractType, string> = {
  lease: 'Lease',
  contract: 'Executory Contract',
  other: 'Other',
};

export const CODEBTOR_RELATIONSHIP_WORDS: Record<CodebtorRelationship, string> = {
  spouse: 'Spouse',
  former_spouse: 'Former Spouse',
  relative: 'Relative',
  friend: 'Friend',
  business_partner: 'Business Partner',
  other: 'Other',
};

export const LEASE_KIND_WORDS: Record<NonNullable<ExecutoryContract['lease_kind']>, string> = {
  residential: 'Residential',
  vehicle: 'Vehicle',
  other_personal_property: 'Other personal property',
  other: 'Other',
};
