from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db

health_router = APIRouter(tags=["health"])

@health_router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for load balancers and monitoring."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
    }
