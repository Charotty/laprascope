#!/usr/bin/env python3
"""
Metadata API endpoint for displacement data.
Provides GET /api/v1/metadata/{job_id} endpoint.
"""

from fastapi import APIRouter, HTTPException, Path
from pathlib import Path
import json
import logging
from typing import Dict, Any

from ..services.displacement_parser import get_displacement_for_patient, generate_metadata, find_csv_files
from ..config import JOBS_DIR, BASE_DIR

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/metadata/{job_id}")
async def get_metadata(job_id: str = Path(..., min_length=1, max_length=100)):
    """
    Get metadata including displacement vectors for a job.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JSON metadata with displacement data
    """
    job_dir = JOBS_DIR / job_id
    
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Try to load existing metadata file first
    metadata_file = job_dir / "metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading existing metadata for job {job_id}: {e}")
            # Continue to generate
    
    # Generate metadata from displacement data
    try:
        # Check if we have patient info in job status
        status_file = job_dir / "status.json"
        patient_fio = None
        
        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    status = json.load(f)
                    # Try to get patient name from status (might be set during upload)
                    patient_fio = status.get("patient_fio")
            except Exception as e:
                logger.warning(f"Could not read status file for job {job_id}: {e}")
        
        # If no patient FIO specified, we can't generate displacement data
        if not patient_fio:
            logger.warning(f"No patient FIO specified for job {job_id}, generating minimal metadata")
            metadata = generate_metadata(None, job_id)
        else:
            # Find CSV files and get displacement data
            csv_files = find_csv_files(BASE_DIR)
            displacement_data = None
            
            for csv_file in csv_files:
                displacement_data = get_displacement_for_patient(csv_file, patient_fio)
                if displacement_data:
                    logger.info(f"Found displacement data for {patient_fio} in {csv_file}")
                    break
            
            if not displacement_data:
                logger.warning(f"No displacement data found for patient {patient_fio}")
                metadata = generate_metadata(None, job_id)
                metadata["warning"] = f"No displacement data found for patient {patient_fio}"
            else:
                metadata = generate_metadata(displacement_data, job_id)
        
        # Save metadata for future requests
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving metadata for job {job_id}: {e}")
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error generating metadata for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate metadata: {str(e)}")


@router.post("/metadata/{job_id}/link-patient")
async def link_patient_to_job(
    job_id: str = Path(..., min_length=1, max_length=100),
    patient_fio: str = None
):
    """
    Link a patient (by FIO) to a job for displacement metadata generation.
    
    Args:
        job_id: Job identifier
        patient_fio: Patient name from CSV files
        
    Returns:
        Success status
    """
    job_dir = JOBS_DIR / job_id
    
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if not patient_fio or not patient_fio.strip():
        raise HTTPException(status_code=400, detail="Patient FIO is required")
    
    # Update job status with patient info
    status_file = job_dir / "status.json"
    status = {}
    
    if status_file.exists():
        try:
            with open(status_file, 'r') as f:
                status = json.load(f)
        except Exception as e:
            logger.warning(f"Could not read status file for job {job_id}: {e}")
    
    status["patient_fio"] = patient_fio.strip()
    
    try:
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
        
        # Delete existing metadata to force regeneration
        metadata_file = job_dir / "metadata.json"
        if metadata_file.exists():
            metadata_file.unlink()
        
        return {"status": "success", "message": f"Patient '{patient_fio}' linked to job {job_id}"}
        
    except Exception as e:
        logger.error(f"Error linking patient to job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to link patient: {str(e)}")
