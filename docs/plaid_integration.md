# Plaid Integration Strategy for DigniFi

**Version:** 1.0  
**Date:** January 4, 2026  
**Status:** Proposed Architecture  

## 1. Executive Summary

Integrating Plaid into DigniFi will automate the collection of critical financial data required for Chapter 7 bankruptcy forms (Forms 101, 106A/B, 106D, 106E/F, 106I, 106J, and 122A-2). This integration aims to:
- **Reduce User Burden:** Eliminate manual entry of dozens of creditors and asset details.
- **Improve Accuracy:** Use verified financial institution data to prevent omission of assets or debts (a common cause of bankruptcy trustee objections).
- **Accelerate Intake:** Reduce the "time-to-petition" from hours to minutes.

## 2. Plaid Product Mapping

We will leverage the following Plaid products, specifically utilizing the **Consumer Report** suite (powered by Plaid Check) to ensure FCRA compliance for data used in legal filings.

| Plaid Product | DigniFi Model | Bankruptcy Form | Purpose |
|---------------|---------------|-----------------|---------|
| **Identity Verification** | `DebtorInfo` | Form 101 | **Critical:** Verify Name, Address, DOB, SSN against government ID and watchlists (CIP/KYC). Ensures the filer is a real person and prevents identity fraud in court filings. |
| **Assets** (Consumer Report) | `AssetInfo` | Schedule A/B | Retrieve verified account balances and ownership data. Snapshot generated is FCRA-compliant, suitable for "proof of funds" or asset declaration. |
| **Liabilities** | `DebtInfo` | Schedule D, E/F | Retrieve credit card balances, loan amounts, interest rates, and creditor names. |
| **Transactions** (Consumer Report) | `ExpenseInfo` | Schedule J | Analyze 90 days of spending to estimate average monthly expenses. |
| **Income** (Consumer Report) | `IncomeInfo` | Schedule I, 122A-2 | **Payroll Income:** Connect to payroll provider (ADP, etc.) for paystubs.<br>**Bank Income:** Analyze deposits to verify net income. |

## 3. Architecture & Data Flow

### 3.1 High-Level Data Flow

1.  **User Initiation:** User clicks "Connect Bank Account" in the React frontend.
2.  **Link Token Creation:** Frontend requests a `link_token` from the Django backend.
    *   *Configuration:* Must specify `user.client_user_id` and `products=['identity_verification', 'assets', 'income']`.
    *   *Consumer Report:* Enable `consumer_report_permissible_purpose` (e.g., "written_instruction" from user).
3.  **Plaid Link:** User authenticates with their bank via Plaid's secure modal.
4.  **Public Token Exchange:** Frontend receives a `public_token` and sends it to the Django backend.
5.  **Access Token Exchange:** Backend exchanges `public_token` for a permanent `access_token` and `item_id`.
6.  **Data Fetch:** Backend uses `access_token` to fetch Assets, Liabilities, etc.
7.  **Normalization:** Backend maps Plaid JSON data to DigniFi models (`AssetInfo`, `DebtInfo`).
8.  **User Review:** User reviews the imported data in the UI (Critical for UPL - user must verify/adopt the data).

### 3.2 Backend Components

-   **Plaid Client:** Singleton wrapper around `plaid-python` SDK.
-   **Webhooks:** Endpoint to handle async updates (e.g., `TRANSACTIONS_SYNC_UPDATES`, `INCOME_VERIFICATION_WEBHOOK`).
-   **Celery Tasks:** Background jobs to fetch and process heavy data (Transactions, Liabilities) to avoid blocking the request.

## 4. Database Schema Updates

To support this integration, we need to introduce a new model to manage Plaid connections and update existing models to link data back to its source.

### 4.1 New Model: `PlaidItem`

This model tracks the connection to a financial institution.

```python
# backend/apps/intake/models.py (or new apps/plaid_integration/models.py)

class PlaidItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    intake_session = models.ForeignKey(IntakeSession, on_delete=models.CASCADE)
    
    # Plaid Identifiers
    item_id = models.CharField(max_length=100, unique=True)
    access_token = EncryptedCharField(max_length=255) # CRITICAL: Must be encrypted
    institution_id = models.CharField(max_length=50)
    institution_name = models.CharField(max_length=100)
    
    # Status
    status = models.CharField(max_length=20, default='active') # active, error, disconnected
    last_sync = models.DateTimeField(null=True, blank=True)
    
    # Consumer Report / Check specific
    link_session_id = models.CharField(max_length=100, blank=True)
    request_id = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
```

### 4.2 Updates to Existing Models

**`AssetInfo`**:
-   Add `plaid_item = ForeignKey(PlaidItem, ...)`
-   Add `plaid_account_id = CharField(...)`
-   Ensure `data_source` is set to "plaid".

**`DebtInfo`**:
-   Add `plaid_item = ForeignKey(PlaidItem, ...)`
-   Add `plaid_account_id = CharField(...)`
-   Update `DATA_SOURCE_CHOICES` to include `("plaid", "Plaid API")`.

**`IncomeInfo`**:
-   Add `plaid_item = ForeignKey(PlaidItem, ...)` (for direct deposit tracking).
-   Add `income_verification_id = CharField(...)` (for Plaid Income check reference).

## 5. Implementation Roadmap

### Phase 1: Infrastructure & Connection (Week 1)
-   Install `plaid-python`.
-   Configure Plaid keys in `settings.py` (Sandbox/Development/Production).
-   Create `PlaidItem` model.
-   Implement `/api/plaid/create_link_token/` endpoint with **Consumer Report** configuration.
-   Implement `/api/plaid/exchange_public_token/` endpoint.
-   Frontend: Integrate `react-plaid-link`.

### Phase 2: Assets & Liabilities (Week 2)
-   Implement `PlaidService.fetch_liabilities()`.
-   Map Credit Card/Loan accounts to `DebtInfo` model.
-   Map Checking/Savings accounts to `AssetInfo` model.
-   Build "Review Imported Data" UI for users to confirm/edit imported items.

### Phase 3: Income & Expenses (Week 3-4)
-   Implement `PlaidService.fetch_transactions()`.
-   Develop categorization logic to map Plaid categories (e.g., "Shops", "Food and Drink") to Bankruptcy Schedule J categories (e.g., "Food and housekeeping supplies").
-   Implement `PlaidService.fetch_income()` (if using Plaid Income product) or infer income from deposit transactions.

### Phase 4: Identity & Compliance (Week 5)
-   Implement `PlaidService.get_identity()`.
-   Cross-reference Plaid identity data with `DebtorInfo` to flag discrepancies.
-   Ensure all data storage complies with encryption standards (Fernet).

## 6. Security & Compliance

-   **Encryption:** `access_token` MUST be stored using `EncryptedCharField` (django-encrypted-model-fields).
-   **Data Minimization:** Only fetch data required for the forms. Do not store full transaction history indefinitely; process into `ExpenseInfo` averages and discard raw transaction logs if possible, or store encrypted.
-   **UPL Disclaimer:** The system must present the imported data as "Found Information" that the user must explicitly "Adopt" or "Verify". The system should not make legal determinations based on the data (e.g., "You qualify for Chapter 7 because Plaid says X"). It should say "Based on the income data imported, the calculator shows..."
-   **FCRA:** If using Plaid for "Consumer Reports" (denying service based on data), FCRA applies. However, DigniFi uses data to *help* the user file, not to deny them. We are acting as a data aggregator for the user's benefit.

## 7. Recommended Configuration

Add to `backend/config/settings/base.py` (via env vars):

```python
PLAID_CLIENT_ID = env("PLAID_CLIENT_ID")
PLAID_SECRET = env("PLAID_SECRET")
PLAID_ENV = env("PLAID_ENV", default="sandbox") # sandbox, development, production
PLAID_PRODUCTS = ["assets", "liabilities", "transactions", "identity"]
PLAID_COUNTRY_CODES = ["US"]
```
