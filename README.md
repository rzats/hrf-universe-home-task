This is an overview of my solution - the original task specifications have been moved to the `TASK.md` file.

## 1. Create a table in the database to store "days to hire" statistics. 

This uses the column names mentioned elsewhere in the task specifications:
- `min_days`
- `avg_days`
- `max_days`
- `job_postings_number`
Otherwise it is self-explanatory.

## 2. Write a CLI script to calculate and store "days for hire" statistics.

Implemented in `home_task/cli/days_to_hire.py`. Sample run:

```bash
$ python home_task/cli/days_to_hire.py --help
Starting days to hire statistics calculation...
usage: days_to_hire.py [-h] [--min-threshold MIN_THRESHOLD] [--standard-job-id STANDARD_JOB_ID] [--country-code COUNTRY_CODE]

Calculate days to hire statistics

optional arguments:
  -h, --help            show this help message and exit
  --min-threshold MIN_THRESHOLD
                        Minimum number of job postings required to save statistics (default: 5)
  --standard-job-id STANDARD_JOB_ID
                        Calculate statistics for specific standard job ID only
  --country-code COUNTRY_CODE
                        Calculate statistics for specific country code only
```
```bash
$ python home_task/cli/days_to_hire.py --min-threshold 10 --country-code UK --standard-job-id
 c83e576e-fa9a-4aef-afb3-f495fca9a6bb
Starting days to hire statistics calculation...
Minimum threshold: 10 job postings.
Processing 1 standard jobs and 1 countries...
Processing standard job: c83e576e-fa9a-4aef-afb3-f495fca9a6bb...
Processing country: UK...
Stats already exist, updating with: min_days=12.0, avg_days=42.575, max_days=76.0, job_postings_number=80
Processed country: UK.
Completed!
Total combinations processed: 1.
Stats saved: 1.
Stats skipped: 0.
```

This script:
- Connects to the database;
- Queries the `job_posting` table;
- Calculates the minimum, average and maximum values of `days_to_hire` with the thresholds in mind, and the number of job postings used in the calculation;
- Inserts the results into `job_posting_stats` or updates the data if present.

Notes on the requirements from the task notes:
- ORM was used instead of raw SQL queries.
- Transactions were used to ensure that the database does not get corrupted, and there is a general rollback mechanism.
- Only the rows for a specific job ID and country combination are loaded at any given time. If in the real world that is still too large to be saved in-memory, we can move the calculations to raw SQL, using the `percentile_disc()` function to get the 10th and 90th percentiles.

## 3. Create REST API with one endpoint to get "days to hire" statistics.

Implemented in `home_task/api/api.py.` This provides a single endpoint accepting `standard_job_id` (required) and `country_code` (optional) parameters. Sample run:

```bash
$ python home_task/api/api.py
INFO:     Started server process [12881]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```
```bash
$ curl "http://localhost:8000/stats/days-to-hire?standard_job_id=c83e576e-fa9a-4aef-afb3-f495fca9a6bb"
{"standard_job_id":"c83e576e-fa9a-4aef-afb3-f495fca9a6bb","country_code":"World","min_days":11.0,"avg_days":41.7710843373494,"max_days":76.0,"job_postings_number":166}
```
