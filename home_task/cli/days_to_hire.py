import argparse
import uuid
from typing import List, Optional, Tuple
import numpy as np
from home_task.db import get_session
from home_task.models import JobPosting, JobPostingStats

def get_standard_job_ids(session) -> List[str]:
     """Get all standard job IDs from the database."""
     results = session.query(JobPosting.standard_job_id).distinct().all()
     return [row[0] for row in results]

def get_country_codes(session) -> List[str]:
    """Get all country codes from the database. Exclude NULL."""
    results = session.query(JobPosting.country_code).filter(
        JobPosting.country_code.isnot(None)
    ).distinct().all()
    return [row[0] for row in results]

def get_job_postings_data(session, standard_job_id: str, country_code: Optional[str] = None) -> List[int]:
    """
    Get job postings days-to-hire data for a specific standard job and country.
    """
    query = session.query(JobPosting.days_to_hire).filter(
        JobPosting.standard_job_id == standard_job_id,
        JobPosting.days_to_hire.isnot(None) # 84 out of 500 have NULL days-to-hire, so we filter them out.
    )
    
    if country_code is not None:
        query = query.filter(JobPosting.country_code == country_code)
    # and if it *is* None, we don't need to filter anything.
    
    results = query.all()
    return [row[0] for row in results]

def calculate_stats(days_to_hire_values: List[int]) -> Tuple[float, float, float, int]:
    """
    Calculate stats for days to hire values.
    This does not cut off by min_threshold - that is handled in a separate function.
    """
    if len(days_to_hire_values) == 0:
        return 0.0, 0.0, 0.0, 0
    
    values = np.array(days_to_hire_values)
    
    # Calculate 10th and 90th percentiles
    p10 = np.percentile(values, 10)
    p90 = np.percentile(values, 90)

    # Filter values between 10th and 90th percentiles
    filtered_values = values[(values >= p10) & (values <= p90)]
    
    if len(filtered_values) == 0:
        return 0.0, 0.0, 0.0, 0
    
    min_days = float(np.min(filtered_values))
    avg_days = float(np.mean(filtered_values))
    max_days = float(np.max(filtered_values))
    count = len(filtered_values)
    
    return min_days, avg_days, max_days, count

def save_stats(session, standard_job_id: str, country_code: Optional[str], min_days: float, avg_days: float, max_days: float, count: int):
    """
    Save stats for a specific standard job and country.
    """
    existing_stats = session.query(JobPostingStats).filter(
        JobPostingStats.standard_job_id == standard_job_id,
        JobPostingStats.country_code == country_code
    ).first()
    if existing_stats:
        print(f"Stats already exist, updating with: min_days={min_days}, avg_days={avg_days}, max_days={max_days}, job_postings_number={count}")
        existing_stats.min_days = min_days
        existing_stats.avg_days = avg_days
        existing_stats.max_days = max_days
        existing_stats.job_postings_number = count
        session.commit()
    else:
        print(f"Stats do not exist, creating new with: min_days={min_days}, avg_days={avg_days}, max_days={max_days}, job_postings_number={count}")
        stats = JobPostingStats(
            id=str(uuid.uuid4()),
            standard_job_id=standard_job_id,
            country_code=country_code if country_code is not None else "World",
            min_days=min_days,
            avg_days=avg_days,
            max_days=max_days,
            job_postings_number=count
        )
        session.add(stats)
        session.commit()

def process_job_postings(session, standard_job_id: str, country_code: Optional[str], min_threshold: int):
    """
    Process job postings for a specific standard job and country.
    """
    days_to_hire_values = get_job_postings_data(session, standard_job_id, country_code)
    if len(days_to_hire_values) < min_threshold:
        print(f"Skipping due to insufficient data: {len(days_to_hire_values)} job postings, threshold is {min_threshold}.")
        return False
    
    min_days, avg_days, max_days, count = calculate_stats(days_to_hire_values)
    if count < min_threshold:
        print(f"Skipping due to insufficient data: {count} job postings, threshold is {min_threshold}.")
        return False
    
    save_stats(session, standard_job_id, country_code, min_days, avg_days, max_days, count)
    return True

def main():
    """Main function containing the bulk of the logic."""
    parser = argparse.ArgumentParser(description="Calculate days to hire statistics")
    
    # Minimum threshold is required by the specifications; the other options were helpful for testing and I decided to keep them.
    parser.add_argument("--min-threshold", type=int, default=5, help="Minimum number of job postings required to save statistics (default: 5)")
    parser.add_argument("--standard-job-id", type=str, help="Calculate statistics for specific standard job ID only")
    parser.add_argument("--country-code", type=str, help="Calculate statistics for specific country code only")
    args = parser.parse_args()

    # Initialize SQL session, connecting to the Docker database.
    session = get_session()

    try:
        # Get jobs and countries to process.
        if args.standard_job_id:
            standard_jobs = [args.standard_job_id]
        else:
            standard_jobs = get_standard_job_ids(session)
        
        if args.country_code:
            countries = [args.country_code]
        else:
            countries = get_country_codes(session)

        total_processed = 0
        total_saved = 0

        print(f"Minimum threshold: {args.min_threshold} job postings.")
        print(f"Processing {len(standard_jobs)} standard jobs and {len(countries)} countries...")
        
        for standard_job_id in standard_jobs:
            print(f"Processing standard job: {standard_job_id}...")
            
            for country_code in countries:
                total_processed += 1
                print(f"Processing country: {country_code}...")
                if process_job_postings(session, standard_job_id, country_code, args.min_threshold):
                    total_saved += 1
                print(f"Processed country: {country_code}.")
            
            # Process world statistics (all country codes, including NULL).
            # But if country_code is specified, assume we only want that specific country.
            if not args.country_code:
                total_processed += 1
                print("Processing world...")
                if process_job_postings(session, standard_job_id, None, args.min_threshold):
                    total_saved += 1
                print(f"Processed world.")

        print(f"Completed!")
        print(f"Total combinations processed: {total_processed}.")
        print(f"Stats saved: {total_saved}.")
        print(f"Stats skipped: {total_processed - total_saved}.")

    except Exception as e:
        # As mentioned in the task specifications, we should rollback the transaction if an error occurs.
        session.rollback()
        print(f"An error occurred: {e}.")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting days to hire statistics calculation...")
    main()
