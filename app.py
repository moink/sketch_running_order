from flask import Flask, request, jsonify

import lp_running_order
from handle_request import create_error_response, convert_request_to_sketches, convert_result_to_json

app = Flask(__name__)


# Handle the running order request
@app.route("/optimize", methods=["POST"])
def optimize_running_order():
    try:
        request_data = request.json
    except Exception as e:
        return create_error_response(repr(e)), 400
    try:
        converted = convert_request_to_sketches(request_data)
        optimal_order = lp_running_order.optimize_running_order(
            converted.sketches, converted.precedence
        )
    except Exception as e:
        return create_error_response(repr(e)), 500
    return jsonify(convert_result_to_json(converted.sketches, optimal_order, converted.id_to_index, True))


if __name__ == "__main__":
    app.run(debug=True)
