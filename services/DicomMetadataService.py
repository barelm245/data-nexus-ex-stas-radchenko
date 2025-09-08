from managers.DicomManager import DicomManager
from managers.DynamoDBManager import DynamoDBManager
from managers.S3Manager import S3Manager
from models.DicomMetadata import DicomMetadata
import logging
import os

logger = logging.getLogger(__name__)


class DicomMetadataService:
    def __init__(self):
        self.s3_manager = S3Manager()
        self.dicom_manager = DicomManager()
        self.dynamodb_manager = DynamoDBManager()
        self.presigned_json_s3_path = "s3://data-apps-ex/json/"

    def extract_metadata_from_s3(self, s3_path) -> DicomMetadata:
        logger.info(f"Fetching DICOM from S3: {s3_path}")
        file_content = self.s3_manager.get_file_from_s3(s3_path=s3_path)
        extracted_metadata = self.dicom_manager.extract_metadata(file_content=file_content)
        ret_val = DicomMetadata(**extracted_metadata)
        ret_val.S3Path = s3_path
        logger.info(f"Extracted metadata for: {s3_path}")
        return ret_val

    def upload_metadata_to_s3(self, metadata: DicomMetadata) -> None:
        # Build filename from the S3 object's basename, keeping only the anon id (without extension)
        path_without_scheme = metadata.S3Path or ""
        if path_without_scheme.startswith("s3://"):
            path_without_scheme = path_without_scheme[len("s3://"):]
        # strip any leading slashes to normalize
        path_without_scheme = path_without_scheme.lstrip("/")

        # Take the final path segment (the object key's basename)
        basename = path_without_scheme.split('/')[-1]
        # Remove the .dcm extension if present (preserve dots in the anon id)
        name_without_ext, ext = os.path.splitext(basename)

        filename = f"{name_without_ext}.json"

        s3_path = f"{self.presigned_json_s3_path}{filename}"

        metadata_dict = metadata.model_dump(exclude_none=True)

        logger.info(f"Uploading metadata JSON to S3: {s3_path}")
        self.s3_manager.upload_json_to_s3(s3_path, metadata_dict)

    def get_metadata_from_db(self, s3_path: str) -> DicomMetadata:
        logger.info(f"Looking up metadata in DB for: {s3_path}")
        ret_val = None
        key_candidate = s3_path
        if key_candidate.startswith("s3://"):
            key_candidate = key_candidate[len("s3://"):]
        key_candidate = key_candidate.lstrip("/")

        basename = key_candidate.split('/')[-1]
        name_without_ext, _ = os.path.splitext(basename)

        key_name = name_without_ext

        metadata = self.dynamodb_manager.get_item(key_name)

        if metadata:
            ret_val = DicomMetadata(**metadata)
            logger.info(f"Metadata found in DB for: {key_name}")
        else:
            logger.info(f"No metadata in DB for: {key_name}")

        return ret_val
