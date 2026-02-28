---
name: nav-audit
description: Audit navigation consistency — detect tab count violations, orphaned routes, admin gate misalignment, hidden features, and tutorial content drift. Run after any epic or feature delivery that touches routing or navigation.
---

# Navigation Audit Workflow

**Goal:** Validate that the application's navigation structure remains clean, consistent, and aligned with the NIST AI RMF organizational model. Detect drift before it becomes a structural problem.

**When to run:**
- After completing any epic or feature that adds new routes
- After any change to navigation components (AppHeader, SecondaryNav, Breadcrumbs)
- As part of sprint retrospectives
- When any team member suspects navigation has become cluttered

---

## AUDIT PROCEDURE

### Step 1: Extract Current Navigation State

Read the following files and extract the current structure:

1. **Primary Nav Items** from `packages/frontend/src/components/layout/AppHeader.tsx`
   - Extract the `NAV_ITEMS` array
   - Extract the `isActive()` function logic (which route prefixes map to which sections)

2. **Secondary Nav Items** from `packages/frontend/src/components/layout/SecondaryNav.tsx`
   - Extract the `SECTION_CONFIG` object (all sections and their tab items)
   - Extract the `getActiveSection()` function logic
   - Count items per section

3. **All Routes** from `packages/frontend/src/App.tsx`
   - Extract every `<Route path="..." />` definition
   - Note which routes use `<PermissionGate>` and what roles they require
   - Note redirect routes

4. **Tutorial References** from `packages/tutorial-system/src/data/*.json`
   - Search for references to section counts (e.g., "five key sections", "six key sections")
   - Search for navigation paths mentioned in tutorial content
   - Search for section names (Dashboard, Catalog, Governance, Operations, Strategic, Admin)

---

### Step 2: Run Audit Checks

#### Check 1: Tab Count Limits
- **Rule:** No section should have more than 8 secondary nav items
- **Warning at:** 7 items
- **Fail at:** 9+ items
- Report: List each section with its item count

#### Check 2: Orphaned Routes
- **Rule:** Every route in App.tsx should appear in either:
  - A `SECTION_CONFIG` items array, OR
  - A documented hub page card (GovernanceHubPage), OR
  - An explicitly documented exception (auth pages, error pages, profile page)
- Report: List any routes that appear in App.tsx but have no navigation entry

#### Check 3: Admin Gate Alignment
- **Rule:** Routes using `<PermissionGate roles={['tenant_admin']}>` should be in the Admin or Operations section's secondary nav
- **Exception:** Routes that are sub-pages of a non-admin parent (e.g., a detail page for an admin-gated list)
- Report: List admin-gated routes and which section they appear in

#### Check 4: Hidden Routes
- **Rule:** No feature should be accessible only via direct URL or command palette. Every feature should have a discoverable navigation path (tab, hub card, or in-page link)
- Report: List routes with no clear discovery path

#### Check 5: Section Balance
- **Rule:** Section item counts should be within 3-8 items. Extreme imbalance (one section with 12, another with 2) indicates poor information architecture
- Report: Distribution chart of items per section

#### Check 6: getActiveSection() / isActive() Consistency
- **Rule:** The `getActiveSection()` function in SecondaryNav.tsx and `isActive()` in AppHeader.tsx must agree on which section owns each route prefix
- Report: List any path that would highlight a different primary icon than the secondary nav it shows

#### Check 7: Tutorial Alignment
- **Rule:** Tutorials that mention section counts or list navigation items must match current SECTION_CONFIG
- Report: List any tutorials with outdated section references

#### Check 8: Breadcrumb Coverage
- **Rule:** Every first-level and second-level route segment should have a PATH_LABELS entry in Breadcrumbs.tsx
- Report: List route segments missing breadcrumb labels

---

### Step 3: Generate Report

Output a structured audit report with:

```markdown
# Navigation Audit Report
**Date:** [current date]
**Auditor:** Nav-Audit Workflow

## Summary
- Total primary sections: X
- Total secondary nav items: X
- Total routes in App.tsx: X
- Checks passed: X/8
- Checks with warnings: X
- Checks failed: X

## Results

### [Check Name] — PASS / WARN / FAIL
[Details]

## Recommendations
[Prioritized list of actions to take]
```

---

### Step 4: Remediation Guidance

For each failed check, provide specific remediation:

- **Tab count exceeded:** Suggest which items to move and where
- **Orphaned route:** Suggest which section to add it to
- **Admin gate misalignment:** Suggest moving to Admin section
- **Hidden route:** Suggest adding to appropriate section's SECTION_CONFIG
- **Section imbalance:** Suggest redistribution strategy
- **Tutorial drift:** List specific JSON files and content to update

---

## REFERENCE: Expected Structure (as of Epic 28)

| Section | Expected Items | Max |
|---------|---------------|-----|
| Dashboard | 6 | 8 |
| Catalog | 4 | 8 |
| Governance | 7 | 8 |
| Operations | 5 | 8 |
| Strategic | 7 | 8 |
| Admin | 5 | 8 |

**Key Files:**
- `packages/frontend/src/components/layout/AppHeader.tsx`
- `packages/frontend/src/components/layout/SecondaryNav.tsx`
- `packages/frontend/src/components/layout/Breadcrumbs.tsx`
- `packages/frontend/src/App.tsx`
- `packages/frontend/src/features/governance/pages/GovernanceHubPage.tsx`
- `packages/tutorial-system/src/data/*.json`
