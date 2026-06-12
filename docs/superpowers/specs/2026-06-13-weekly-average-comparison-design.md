# Weekly Average Comparison Design

## Goal

Add two weekly average comparison charts to the bottom of the China Export
Monitor. Both charts must respond to every active sidebar filter while still
loading enough historical data to compare the selected period with the
previous five years.

## Scope And Definitions

- The active commodity and destination selections apply to both current-year
  and historical comparison data.
- The selected date range determines the displayed month/week window.
- The comparison year is the year containing the selected end date.
- Historical comparison data covers the previous five calendar years.
- A weekly value is the week's total `voy_intake_mt` divided by seven, which is
  labeled as the daily average shipment volume for that week.
- The current incomplete calendar week is excluded.
- The feature uses shipment volume because the current query does not include
  a vessel-record field such as `vsl_name`.

## Data Flow

The existing dashboard query remains date-scoped for the headline metrics,
trend, ranking, and detail table. A second cached query loads the comparison
window, starting five years before the comparison year and ending at the
selected end date. This avoids changing the behavior or cost of existing
dashboard sections.

After normalization, the historical source receives the active commodity and
destination filters. A dedicated analytics helper then:

1. assigns each row to a Monday-starting calendar week;
2. excludes incomplete weeks;
3. sums weekly shipment volume and divides it by seven;
4. maps each week to a stable month/week sequence within its own year;
5. limits displayed sequences to the window selected in the comparison year.

This alignment lets prior years appear on the comparison year's x-axis without
misaligning weeks around calendar-year boundaries.

## Charts

### Current Year Versus History

The first chart shows:

- the selected comparison year's weekly daily-average line;
- up to five individual prior-year lines;
- the historical median;
- the historical 25%-75% band;
- the historical minimum-maximum band.

The chart uses the current dashboard palette and unified hover labels. Its
x-axis shows calendar months, while hover text identifies the month/week
sequence and each line or range value.

### Current Year And Four-Week Average

The second chart shows:

- bars for the selected comparison year's weekly daily-average shipment volume;
- a dotted line for the rolling four-week average.

The rolling average uses available current-year points and `min_periods=1`.

## Placement And Empty States

The new `Weekly average comparison` section appears after the filtered detail
table so it remains the final dashboard section, matching the reference app.
Each chart renders independently. If a chart has insufficient data, the
dashboard displays a concise informational message instead of failing.

## Error Handling

- Empty filtered historical data returns empty analytics frames.
- A selected date range that has no completed weeks returns empty chart data.
- Historical bands are omitted when no prior-year observations exist.
- Existing database configuration and load errors continue to use the current
  dashboard error handling.

## Testing

Analytics tests will verify:

- weekly shipment totals are divided by seven;
- incomplete current weeks are excluded;
- active commodity and destination filters affect comparison data;
- the selected comparison-year date window limits displayed week sequences;
- historical statistics use only the previous five years;
- the four-week rolling average is correct.

UI regression tests will verify that both chart builders and the final section
are wired into `app.py`. The full unit-test suite and Python compilation checks
must pass before completion.
