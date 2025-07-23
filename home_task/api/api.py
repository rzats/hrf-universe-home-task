from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from home_task.db import get_session
from home_task.models import JobPostingStats

app = FastAPI(
    title="Days to Hire Stats API",
    description="API for retrieving days to hire stats.",
    version="1.0.0"
)

class DaysToHireStats(BaseModel):
    """Response model for days to hire stats."""
    standard_job_id: str
    # These should technically never be None, but we match the database schema.
    country_code: Optional[str] = None
    min_days: Optional[float] = None
    avg_days: Optional[float] = None
    max_days: Optional[float] = None
    job_postings_number: Optional[int] = None


@app.get("/stats/days-to-hire", response_model=DaysToHireStats)
async def get_days_to_hire_stats(
    standard_job_id: str,
    country_code: Optional[str] = None
):
    session = get_session()
    
    try:
        # Get the stats for the specified ID.
        query = session.query(JobPostingStats).filter(
            JobPostingStats.standard_job_id == standard_job_id
        )
        
        # We already modified the country_code to "World" in the CLI script.
        if country_code is not None:
            query = query.filter(JobPostingStats.country_code == country_code)
        else:
            query = query.filter(JobPostingStats.country_code == "World")
        
        # Use first() to get one record (in case of duplicates).
        stats = query.first()
        
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"No statistics found for standard_job_id {standard_job_id} and country_code {country_code if country_code else 'World'}. "
            )
        
        return DaysToHireStats(
            standard_job_id=stats.standard_job_id,
            country_code=stats.country_code,
            min_days=stats.min_days,
            avg_days=stats.avg_days,
            max_days=stats.max_days,
            job_postings_number=stats.job_postings_number
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
