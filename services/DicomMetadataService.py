from managers.DicomManager import DicomManager
from managers.DynamoDBManager import DynamoDBManager
from managers.S3Manager import S3Manager
from models.DicomMetadata import DicomMetadata
import logging

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
        filename = f"{metadata.S3Path}.json"

        s3_path = f"{self.presigned_json_s3_path}{filename}"

        metadata_dict = metadata.model_dump(exclude_none=True)

        logger.info(f"Uploading metadata JSON to S3: {s3_path}")
        self.s3_manager.upload_json_to_s3(s3_path, metadata_dict)

    def get_metadata_from_db(self, s3_path: str) -> DicomMetadata:
        logger.info(f"Looking up metadata in DB for: {s3_path}")
        ret_val = None
        metadata = self.dynamodb_manager.get_item(s3_path)

        if metadata:
            ret_val = DicomMetadata(**metadata)
            logger.info(f"Metadata found in DB for: {s3_path}")
        else:
            logger.info(f"No metadata in DB for: {s3_path}")

        return ret_val
