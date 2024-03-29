from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/health')
def health_check():
    print('Checking Health')
    return jsonify(message="up", status=200), 200


@app.route('/mock/destination', methods=['POST'])
def mock_destination():
    req = request.json
    print(req)
    print(f"Recieved request with {len(req)} records.")

    return jsonify(message=f"Recieved request with {len(req)} records.", status=200), 200


@app.route("/mock/rudderstack", methods=['POST'])
def mock_rudderstack():
    auth_header = request.headers.get('Authorization', 'Basic dummy_id')
    req_id = auth_header.split(' ')[1]
    req = request.json
    print(req)

    if not req.get('batch'):
        print("Invalid request. Data must be under the 'batch' key")
        return jsonify(message="Invalid request. Data must be under the 'batch' key", status=400), 400

    for rec in req.get('batch'):
        if 'userId' not in rec:
            print(f"Invalid request. Data must be under the 'userId' key: {rec}")
            return jsonify(message="Invalid request. Every record must have a 'userId' field", status=400), 400

    return jsonify(message="Check api_destination logs", status=200), 200


@app.route('/mock/poll/<id>', methods=['PUT'])
def poll_for_status(id):
    req = request.json
    print(req)

    return jsonify(message=f"received status for {id}", status=200), 200


@app.route('/mock/error/<code>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
def return_error(code):
    req = request.json
    # print(req)
    resp_code = int(code)

    return jsonify(message="Mock error", status=resp_code), resp_code


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
