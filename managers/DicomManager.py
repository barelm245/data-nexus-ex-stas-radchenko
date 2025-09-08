import io
import logging

from pydicom import dcmread

logger = logging.getLogger(__name__)

class DicomManager:
    def extract_metadata(self, file_content) -> dict:
        try:
            logger.info("Starting DICOM metadata extraction")
            # Convert bytes to BytesIO if necessary
            if isinstance(file_content, bytes):
                file_content = io.BytesIO(file_content)

            # Read DICOM file from the stream
            dicom_dataset = dcmread(file_content)
            logger.info("DICOM file parsed successfully")

            # Extract required ret_val fields
            ret_val = {}

            # PatientID
            ret_val['PatientID'] = str(getattr(dicom_dataset, 'PatientID', ''))

            # StudyDate
            ret_val['StudyDate'] = str(getattr(dicom_dataset, 'StudyDate', ''))

            # Modality
            ret_val['Modality'] = str(getattr(dicom_dataset, 'Modality', ''))

            # InstitutionName
            ret_val['InstitutionName'] = str(getattr(dicom_dataset, 'InstitutionName', ''))

            # StudyDescription
            ret_val['StudyDescription'] = str(getattr(dicom_dataset, 'StudyDescription', ''))

            logger.info(f"Extracted PatientID={ret_val.get('PatientID','')} StudyDate={ret_val.get('StudyDate','')}")
            return ret_val

        except Exception as e:
            logger.exception("Failed to extract DICOM metadata")
            raise Exception(f"Error extracting DICOM ret_val: {str(e)}")

    def extract_metadata_from_s3(self, s3_manager, s3_path):
        try:
            logger.info(f"Fetching file from S3 for metadata extraction: {s3_path}")
            file_content = s3_manager.get_file_from_s3(s3_path)
            logger.info(f"File fetched from S3: {s3_path}")
            return self.extract_metadata(file_content)
        except Exception as e:
            logger.exception("Failed to extract metadata from S3")
            raise Exception(f"Error extracting metadata from S3 file: {str(e)}")