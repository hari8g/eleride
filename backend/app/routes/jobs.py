from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from ..db import get_db
from .. import schemas, crud
import os
from ..services.etl import run_full_etl


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=list[schemas.Job])
def list_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.list_jobs(db, skip=skip, limit=limit)


@router.post("/", response_model=schemas.Job, status_code=201)
def create_job(job_in: schemas.JobCreate, db: Session = Depends(get_db)):
    existing = crud.get_job_by_external_id(db, job_in.external_job_id)
    if existing:
        raise HTTPException(status_code=409, detail="Job with external_job_id already exists")
    return crud.create_job(db, job_in)


@router.get("/{external_job_id}", response_model=schemas.Job)
def get_job(external_job_id: str, db: Session = Depends(get_db)):
    job = crud.get_job_by_external_id(db, external_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/admin/upload-and-run-etl")
def upload_and_run_etl(file: UploadFile = File(...), k: int = 12):
    tmp_path = f"/tmp/{file.filename}"
    with open(tmp_path, "wb") as f:
        f.write(file.file.read())
    try:
        res = run_full_etl(tmp_path, cleaned_csv_out="/data/jobs_clean.csv", k_clusters=k, train_model=True)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    return res
