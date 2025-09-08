from flask import Flask, request, jsonify
import config

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"message": "The server is running"}), 200

@app.route('/dicom-metadata', methods=['GET'])
def get_dicom_metadata():
    raise NotImplementedError("This method is not implemented yet")

@app.route('/upload-json-to-s3', methods=['POST'])
def upload_json_to_s3():
    raise NotImplementedError("This method is not implemented yet")

@app.route('/fetch-dicom-metadata', methods=['GET'])
def fetch_dicom_metadata_from_dynamo():
    raise NotImplementedError("This method is not implemented yet")

if __name__ == '__main__':
    app.run(debug=True)
