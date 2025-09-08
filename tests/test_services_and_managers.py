import os
import logging
from unittest.mock import Mock

import pytest

from managers.DicomManager import DicomManager
from services.DicomMetadataService import DicomMetadataService
from models.DicomMetadata import DicomMetadata

logging.basicConfig(level=logging.INFO)

TEST_DIR = os.path.dirname(__file__)
SAMPLE_DCM = os.path.join(TEST_DIR, 'sample.dcm')


def load_sample_bytes():
    with open(SAMPLE_DCM, 'rb') as f:
        return f.read()


def test_dicom_manager_extract_from_bytes():
    dm = DicomManager()
    data = load_sample_bytes()

    result = dm.extract_metadata(data)

    assert isinstance(result, dict)
    # Expect keys to be present (may be empty strings)
    for key in ['PatientID', 'StudyDate', 'Modality', 'InstitutionName', 'StudyDescription']:
        assert key in result
        assert isinstance(result[key], str)


def test_dicom_manager_extract_from_s3_with_mock():
    dm = DicomManager()
    sample_bytes = load_sample_bytes()

    fake_s3 = Mock()
    fake_s3.get_file_from_s3.return_value = sample_bytes

    result = dm.extract_metadata_from_s3(fake_s3, 's3://fake-bucket/path/sample.dcm')

    assert isinstance(result, dict)
    assert 'PatientID' in result


def test_dicomm_metadata_service_end_to_end_upload_and_extract():
    service = DicomMetadataService()

    # Replace managers with mocks / real where appropriate
    sample_bytes = load_sample_bytes()

    fake_s3 = Mock()
    fake_s3.get_file_from_s3.return_value = sample_bytes
    fake_s3.upload_json_to_s3 = Mock()

    service.s3_manager = fake_s3
    service.dicom_manager = DicomManager()

    # Ensure DB returns no entry for the path
    service.dynamodb_manager = Mock()
    service.dynamodb_manager.get_item.return_value = None

    s3_path = 's3://test-bucket/path/sample.dcm'

    # Extract metadata
    metadata = service.extract_metadata_from_s3(s3_path)
    assert isinstance(metadata, DicomMetadata)
    assert metadata.S3Path == s3_path

    # Upload metadata JSON
    service.upload_metadata_to_s3(metadata)
    fake_s3.upload_json_to_s3.assert_called_once()
    called_args = fake_s3.upload_json_to_s3.call_args[0]
    assert len(called_args) >= 2
    uploaded_s3_path = called_args[0]
    uploaded_payload = called_args[1]
    assert uploaded_s3_path.startswith('s3://')
    assert isinstance(uploaded_payload, dict)


def test_get_metadata_from_db_found_and_not_found():
    service = DicomMetadataService()

    # Override managers to avoid AWS calls
    service.s3_manager = Mock()
    service.dicom_manager = Mock()

    sample_meta = {
        'PatientID': 'P123',
        'StudyDate': '20250101',
        'Modality': 'CT',
        'InstitutionName': 'Test Hospital',
        'StudyDescription': 'Test Study',
        'S3Path': 's3://bucket/key'
    }

    fake_db = Mock()
    # First call returns data, second returns None
    fake_db.get_item.side_effect = [sample_meta, None]

    service.dynamodb_manager = fake_db

    m1 = service.get_metadata_from_db('s3://bucket/key')
    assert isinstance(m1, DicomMetadata)
    assert m1.PatientID == 'P123'

    m2 = service.get_metadata_from_db('s3://no/key')
    assert m2 is None

