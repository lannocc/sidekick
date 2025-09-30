### Proposal: Unifying Balance Sheet Structures Across Profiles

#### 1. Executive Summary

This proposal outlines a refactoring strategy for the `ind`, `biz`, and `fag` profiles. The primary goals are:
1.  To enable all three profiles to support multiple years of balance sheet data (also known as Personal Financial Statements or PFS).
2.  To standardize the structure of assets, liabilities, and balance sheets across all profiles.

Achieving these goals is critical for the development of the `pkg` (Consolidated Package) profile, which needs a consistent data model to aggregate and analyze financial information from multiple underlying profiles. The `biz` profile currently has the most robust multi-year structure, and its design will serve as a model for the other two.

#### 2. The Challenge: Divergent Structures

The profiles have evolved independently, leading to different ways of representing financial data:
*   **`ind` (Individual):** Represents a single point-in-time balance sheet. Assets (`vehicle`, `property`, etc.) and liabilities (`liability`) are defined as top-level lists, and a single set of balance sheet totals is calculated.
*   **`biz` (Business):** Supports multi-year financials through a `doc.tax_year` list, where each year contains a `BalanceSheet` object populated from tax forms (e.g., Schedule L). This is an excellent pattern for historical data.
*   **`fag` (Farm/Ag):** Is structured similarly to `ind`, with top-level asset and liability lists implying a single balance sheet. It lacks a formal structure for multi-year financial statements.

This divergence makes it impossible to create a generic consolidation logic in the `pkg` profile.

#### 3. Proposed Standard Structure

We will introduce a standardized, multi-year structure for financial statements that will be adopted by all three profiles.

##### 3.1. Standard Financial Statement List

Each profile (`ind`, `biz`, `fag`) will contain a primary list for historical financial data. This list will be the single source of truth for multi-year balance sheets and income statements.

```python
# In each profile's v0/__init__.py
# ...
# self.financial_statements = self.FinancialStatementYears(self)
# ...

class FinancialStatementYears(List):
    def _item_(self):
        return self.FinancialStatementYear(self)

    class FinancialStatementYear(Map):
        def _init_(self):
            self.year = Year(self, 'Financial Year')
            self.source = Text(self, 'Data Source', 'e.g., "Tax Return", "PFS"')
            self.balance_sheet = self.BalanceSheet(self)
            self.income_statement = self.IncomeStatement(self) # Structure to be standardized as well
            self._id_ = self.year

        class BalanceSheet(Map):
            # ... standardized fields ...
```

##### 3.2. Standard `BalanceSheet` Class

The `BalanceSheet` class within `FinancialStatementYear` will be standardized with a common set of fields. This ensures that `pkg` can aggregate values using the same field names regardless of the source profile.

**Key Standard Fields:**
*   **Current Assets:** `cash`, `accounts_receivable`, `inventories`, `other_current_assets`, `total_current_assets`.
*   **Fixed & Intermediate Assets:** `net_fixed_assets`, `investments`, `total_assets`.
*   **Liabilities:** `accounts_payable`, `short_term_debt`, `cpltd` (Current Portion of Long-Term Debt), `total_current_liabilities`, `long_term_liabilities`, `total_liabilities`.
*   **Equity:** `retained_earnings`, `net_worth` (or `tnw` for business).

#### 4. Refactoring Plan for Each Profile

##### 4.1. `ind` (Individual) Profile

1.  **Introduce `financial_statements`:** In `./ind/v0/__init__.py`, add the proposed `FinancialStatementYears` list. The existing `document.tax_year` can feed into this structure, but we will also support manually entered Personal Financial Statements (PFS).
2.  **Re-purpose Asset/Liability Lists:** The existing top-level lists (`self.liability`, `self.vehicle`, `self.property`, etc.) will be treated as the inputs for the *most recent* year's `BalanceSheet`.
3.  **Update `computer.py`:** The logic in `./ind/v0/computer.py` will be modified to:
    *   First, populate the `financial_statements` list from historical tax documents (`document.tax_year`).
    *   Second, create a `BalanceSheet` for the current year within the `financial_statements` list by aggregating data from the top-level asset (`vehicle`, `property`) and liability (`liability`) lists. This populates the most recent financial statement.

##### 4.2. `fag` (Farm/Ag) Profile

1.  **Introduce `financial_statements`:** In `./fag/v0/__init__.py`, add the `FinancialStatementYears` list.
2.  **Standardize Assets/Liabilities:** The existing `self.assets` and `self.liability` lists will be refactored to match the granular structure of the `ind` profile (e.g., separate lists for `property`, `vehicles`, `investments`). This provides a richer data model for analysis.
3.  **Update `computer.py`:** The new `./fag/v0/computer.py` logic will build the multi-year `financial_statements` list, using tax documents (`doc.sch_f`) for historical income data and the new asset/liability lists to construct the balance sheet for each year.

##### 4.3. `biz` (Business) Profile

1.  **Align with Standard:** The existing `doc.tax_year` in `./biz/v0/__init__.py` is already very close to the target structure. The primary change is to ensure its internal `BalanceSheet` class (`doc.tax_year.TaxYear.BalanceSheet`) is renamed and/or refactored to match the new standard `BalanceSheet` definition.
2.  **Standardize Field Names:** Field names within the `biz` `BalanceSheet` will be mapped to the new standard names (e.g., `retained_earnings_owner` becomes `net_worth`).
3.  **Update `computer.py`:** The logic in `./biz/v0/computer.py` that populates the balance sheet from Schedule L data will be updated to write to the new standardized field names.

#### 5. Path to `pkg` (Consolidated Package) Profile

With these changes, the `pkg` profile becomes straightforward to implement.

*   The `pkg` profile will contain a list of child profiles (e.g., one `biz` and two `ind` profiles).
*   The `pkg/v0/computer.py` will iterate through these child profiles.
*   For each year, it can access `child.financial_statements[year].balance_sheet`.
*   Because the `BalanceSheet` structure and field names are now identical, it can perform simple aggregations:
    ```python
    # Example logic in pkg/v0/computer.py
    consolidated_cash = 0
    for child_profile in self.children:
        if child_profile.financial_statements.exists(year):
             consolidated_cash += child_profile.financial_statements[year].balance_sheet.cash

    # Set the value in the pkg profile's own consolidated balance sheet
    self.financial_statements[year].balance_sheet.cash.set(consolidated_cash)
    ```

This unified model simplifies consolidation, reduces code duplication, and creates a more robust and scalable system for financial analysis.

