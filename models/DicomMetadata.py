from pydantic import BaseModel
from typing import Optional

class DicomMetadata(BaseModel):
    PatientID: Optional[str] = None
    StudyDate: Optional[str] = None
    Modality: Optional[str] = None
    InstitutionName: Optional[str] = None
    StudyDescription: Optional[str] = None
    S3Path: Optional[str] = None

