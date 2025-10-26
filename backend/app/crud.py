from sqlalchemy.orm import Session
from sqlalchemy import select
from . import models, schemas


def create_job(db: Session, job_in: schemas.JobCreate) -> models.Job:
    job = models.Job(**job_in.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job_by_external_id(db: Session, external_job_id: str) -> models.Job | None:
    stmt = select(models.Job).where(models.Job.external_job_id == external_job_id)
    return db.scalar(stmt)


def list_jobs(db: Session, skip: int = 0, limit: int = 100) -> list[models.Job]:
    stmt = select(models.Job).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


