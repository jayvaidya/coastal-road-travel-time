# Road Segment Travel-Time Study

## Purpose

This project measures how long it actually takes to drive a single road segment
connecting the Coastal Road and Napean Sea Road in Mumbai, and records how that
time changes through the day and across the week. The aim is to collect accurate
data on this question using a method that anyone can inspect and reproduce.

The project takes no position on any policy question. Its only goal is to put a
measured, public record in place of estimates and anecdote.

## What is measured

The main quantity is **travel time, in seconds**, for the segment in a single
direction of travel. Each reading also records the **free-flow time** (how long
the same segment would take with no traffic). The ratio of the two gives a
**Travel Time Index**, a congestion multiplier where 1.0 means an unobstructed
road and, say, 2.5 means the trip took two and a half times as long as it would
on an empty road.

Readings are grouped by hour of day and day of week. For each group we report the
median along with a range of percentiles (such as the 10th, 80th and 95th), so the
summary shows both the typical trip and how much it varies.

## Method, and why the data is collected live

Travel times are sampled from the Google Routes API every ten minutes through
the day, roughly between 7 am and 11 pm, over a period of several weeks. Each
reading is stored with the exact time it was taken.

Sampling is done live on purpose. A live reading reflects the road as it actually
is at the moment of measurement, so it captures real congestion: incidents,
stalled traffic, weather-related slowdowns, and other one-off disruptions, as
they happen. This is different from a modeled or predictive travel time, which is
essentially a long-run average for a given time slot and tends to smooth away the
irregular events that shape the real experience of the road. Collecting live
samples over time builds a record of what conditions were, not a model of what
they usually are.

## Why this repository is public

The data and the code that collects it are published openly so that the work can
be checked:

1. **The method is visible.** The full collection logic, the sampling interval,
   and the coordinates are all in the repository. Nothing is hidden.
2. **The history is tamper-evident.** Each reading is committed to version control
   as it is recorded, which produces a timestamped, append-only log. Any change to
   past data would show up in the commit history.
3. **The results are reproducible.** Anyone can read the method, run the collector
   against the same source, and check the results for themselves.

## How the data can be trusted

- The raw readings are published in full and never deleted, so the complete
  record stays open to inspection.
- Two kinds of reading are left out of the summary statistics, and both remain
  visible in the raw data: failed API requests, and readings whose route distance
  shows the service snapped to the wrong path (for example, a U-turn), which would
  otherwise distort the travel time.
- Every reading carries an exact timestamp and notes its data source.
- The travel times come from the Google Routes API, the same routing service
  available to the public, applied the same way to every reading.
- The analysis code is open, so the summary figures can be regenerated from the
  raw data by anyone.

## Repository contents

| File | Purpose |
|---|---|
| `config.json` | The measured segment (origin and destination coordinates) |
| `collect.py` | Samples the routing API and appends one timestamped reading |
| `analyze.py` | Aggregates readings by day of week and hour of day |
| `index.html` | The public web page that charts the readings |
| `data/travel_times.csv` | The complete raw record of readings |
| `.github/workflows/collect.yml` | The scheduled collection job |

## Reproducing the analysis

```bash
python analyze.py   # prints the hour-by-hour summary and writes summary.csv
```

Several weeks of collection are needed before the numbers mean much, so that each
hour-of-day and day-of-week group holds enough readings to be informative.
