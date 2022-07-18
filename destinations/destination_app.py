from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/health')
def health_check():
    print('Checking Health')
    return jsonify(message="up", status=200)


@app.route("/mock/rudderstack", methods=['POST'])
def mock_rudderstack():
    auth_header = request.headers.get('Authorization', 'Basic dummy_id')
    req_id = auth_header.split(' ')[1]
    req = request.json
    print(req)

    for rec in req.get('batch'):
        if 'userId' not in rec:
            print(rec)
            # TODO return actual 400 w/ this message
            return "Invalid request. Check destination_app logs"
    
    return "Check destination_app logs"


@app.route('/mock/poll/<id>', methods=['PUT'])
def poll_for_status(id):
    req = request.json
    print(req)

    return jsonify(message=f"received status for {id}", status=200)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
