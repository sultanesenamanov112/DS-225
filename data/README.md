# Data files

## bike_daily.csv

An unmodified copy of `day.csv` from the **UCI Bike Sharing Dataset**: 731 daily
records (2011-01-01 through 2012-12-31) from the Capital Bikeshare system in
Washington, DC, with weather and calendar attributes joined in by the dataset's
authors. Used throughout module 11 (time series); notebooks load it at runtime
from this repo's raw GitHub URL rather than from a local path.

- Source: https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset
- Citation: Fanaee-T, Hadi, and Gama, Joao. "Event labeling combining ensemble
  detectors and background knowledge." *Progress in Artificial Intelligence*
  (2013). Springer.
- License: CC BY 4.0 (per the UCI repository listing). Ride data originally
  published by Capital Bikeshare; weather data from freemeteo.com.

### Columns

| Column | Meaning |
|---|---|
| `instant` | Row number (1-based) |
| `dteday` | Date |
| `season` | 1 = spring, 2 = summer, 3 = fall, 4 = winter |
| `yr` | 0 = 2011, 1 = 2012 |
| `mnth` | Month, 1–12 |
| `holiday` | 1 if the day is a DC holiday |
| `weekday` | Day of week, 0 = Sunday through 6 = Saturday |
| `workingday` | 1 if neither weekend nor holiday |
| `weathersit` | 1 = clear/partly cloudy, 2 = mist/fog, 3 = light rain or snow (no category-4 days occur in the daily file) |
| `temp` | Temperature, normalized to 0–1 (divided by 41 °C) |
| `atemp` | Feeling temperature, normalized to 0–1 (divided by 50 °C) |
| `hum` | Humidity, normalized to 0–1 |
| `windspeed` | Wind speed, normalized to 0–1 (divided by 67) |
| `casual` | Rentals by non-members |
| `registered` | Rentals by members |
| `cnt` | Total rentals: `casual` + `registered` |

The module 11 notebooks keep only `dteday`, `season`, `weathersit`, `temp`,
`casual`, `registered`, and `cnt`; the calendar columns are deliberately left
out because the notebooks derive them from the `DatetimeIndex` instead.
