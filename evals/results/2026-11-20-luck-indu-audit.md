# LUCK and INDU financial statement audit

Both models received the same September 2026 issuer PDFs and ran once per prompt at temperature 0. LUCK is a 27-page scanned financial-results announcement. INDU is a 26-page text PDF. Checks cover fields mapped by the app and selected note rows. Monetary values in the findings use the filings’ PKR thousands scale unless stated otherwise.

| Filing | Model | Initial checks | Refined checks | Refined request cost |
| --- | --- | ---: | ---: | ---: |
| LUCK | Gemini 3 Flash Preview | 43/46 | 43/46 | $0.01292 |
| LUCK | Gemini 3.1 Flash Lite | 42/46 | 42/46 | $0.00624 |
| INDU | Gemini 3 Flash Preview | 53/58 | 56/58 | $0.01293 |
| INDU | Gemini 3.1 Flash Lite | 53/58 | 57/58 | $0.00631 |

The refined audit requires LUCK’s reported operating profit for both years and EBITDA as mandatory checks. Both models failed LUCK on operating profit and passed INDU. The refined run billed $0.02585 for Flash Preview and $0.01256 for Flash Lite across both filings (51% less). Median request times were 9.09 s and 5.88 s respectively. This is one sample per model and filing.

## LUCK scanned PDF

| Field and source | Expected | Flash Preview, initial → refined | Flash Lite, initial → refined | Finding |
| --- | ---: | --- | --- | --- |
| Borrowings total, PDF p. 4 | `null` | 181,914,953 → 181,914,753 | 183,634,512 → 181,796,847 | The filing shows three borrowing components. Both models read them correctly and supplied an unverified grand total. Python sums the components to 181,915,015. |
| Operating profit, PDF pp. 5 and 15 | 26,630,000 | correct → 24,624,578 | 24,624,578 → 24,624,578 | The returned value matches the subtotal after finance costs on the income statement. The directors’ highlights give operating profit. |
| Prior-year operating profit, PDF pp. 5 and 15 | 26,826,000 | correct → 24,549,184 | 24,549,184 → 24,549,184 | The returned value matches the comparative subtotal after finance costs. |
| EBITDA, PDF p. 15 | 31,959,000 | correct → correct | `null` → correct | Flash Lite initially omitted the EBITDA listed in the directors’ highlights. The reason for the omission is unknown. |
| Period-end shares, PDF p. 4 | `null` | 293,000,000 → `null` | `null` → `null` | The filing shows paid-up capital. The initial Preview value has no direct support as a share count in this packet. |
| Consolidated other-income detail | No itemized rows | One row → empty | Empty → one row | Preview initially returned dividend income from subsidiaries and an associate, a standalone line. Lite later treated a single net other-income line as an itemized breakdown. |

## INDU text PDF

| Field and source | Expected | Flash Preview, initial → refined | Flash Lite, initial → refined | Finding |
| --- | ---: | --- | --- | --- |
| Period-end shares, PDF p. 9 | `null` | 78,600,000 → 78,600,000 | 78,600 → `null` | Preview's value agrees with paid-up capital divided by face value. The filing lacks a direct period-end count. Lite's initial output also used a value 1,000 times smaller than the implied count. |
| Total liabilities, PDF p. 9 | `null` | 75,706,357 → 75,706,357 | 75,706,357 → 75,706,357 | The models correctly added reported current and noncurrent liabilities. This is Python's calculation. |
| Dividend from listed mutual fund units, note 11 | 0 | Omitted → 0 | Omitted → 0 | Both models skipped a row printed as a dash in the initial run. The note count was therefore 7 of 8 before the refinement and 8 of 8 after it. |
| Book value per share, PKR per share | `null` | 1,152.49 → `null` | 1,152.49 → `null` | The returned value is consistent with dividing equity by the implied share count. The filing gives the inputs for an inferred share count and does not state book value per share. |

## Python calculations

The independent calculation fixtures passed 29/29 checks for LUCK and 32/32 for INDU. Balance sheets and cash-flow movements reconciled for both. Quarterly free cash flow was PKR 18,436,325,000 for LUCK and PKR −24,325,326,000 for INDU. Tests verified that trailing ratios require trailing inputs and used separately supplied share counts and illustrative quotes for tests that require them. Passing arithmetic checks establishes the formulas for these inputs. An incorrectly extracted input can still produce an incorrect result.
