from flask import Blueprint, request, jsonify
from controllers.query_parser import QueryParser

query_bp = Blueprint("query", __name__)
query_parser = QueryParser()

@query_bp.route("/api/query", methods=["POST"])
def query():
    messages = request.json.get("messages")
    query_summary = request.json.get("summary")
    response = query_parser.handle_query(messages, query_summary)

    print(response)
    return jsonify({
        "message": response,
        "summary": query_summary
    })