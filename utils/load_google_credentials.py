import os
import base64


def setup_google_credentials():
    key_b64 = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if key_b64:
        key_json = base64.b64decode(key_b64).decode("utf-8")
        with open("gemini-key.json", "w") as f:
            f.write(key_json)

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gemini-key.json"