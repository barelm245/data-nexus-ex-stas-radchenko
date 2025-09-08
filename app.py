from flask import Flask, request, jsonify
import config
from services.DicomMetadataService import DicomMetadataService

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"message": "The server is running"}), 200

@app.route('/dicom-metadata', methods=['GET'])
def get_dicom_metadata():
    try:
        s3_path = request.args.get('s3_path')
        if not s3_path:
            return jsonify({"error": "Missing required query parameter: s3_path"}), 400
        
        metadata_service = DicomMetadataService()
        metadata = metadata_service.extract_metadata_from_s3(s3_path)
        return jsonify(metadata.model_dump()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/upload-json-to-s3', methods=['POST'])
def upload_json_to_s3():
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({"error": "Missing JSON payload in request body"}), 400

        from models.DicomMetadata import DicomMetadata
        try:
            metadata = DicomMetadata(**json_data)
        except Exception as e:
            return jsonify({"error": f"Invalid DicomMetadata format: {str(e)}"}), 400

        metadata_service = DicomMetadataService()
        metadata_service.upload_metadata_to_s3(metadata,)

        return '', 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/fetch-dicom-metadata', methods=['GET'])
def fetch_dicom_metadata_from_dynamo():
    try:
        s3_path = request.args.get('s3_path')
        if not s3_path:
            return jsonify({"error": "Missing required query parameter: s3_path"}), 400

        metadata_service = DicomMetadataService()
        metadata = metadata_service.get_metadata_from_db(s3_path=s3_path)
        return jsonify(metadata.model_dump()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=8000, debug=True)