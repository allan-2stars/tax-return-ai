export interface MockTaxYearWorkspace {
  id: string;
  label: string;
}

// TODO(phase-3-workspace): Replace with backend TaxWorkspace model API.
export const MOCK_TAX_YEARS: MockTaxYearWorkspace[] = [
  { id: "fy2025", label: "FY2025" },
  { id: "fy2024", label: "FY2024" },
];
