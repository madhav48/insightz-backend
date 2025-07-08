from flask import Blueprint, send_from_directory

download_bp = Blueprint("download", __name__)

@download_bp.route("/api/download/<filename>", methods=["GET"])
def download(filename):
    return send_from_directory("static/reports", filename)
