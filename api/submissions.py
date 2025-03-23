from supabase import create_client, Client
from dotenv import load_dotenv
import os
import json

load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def handle_submission(data):
    linkedin = data.get("linkedin")
    devpost = data.get("devpost")
    email = data.get("email")

    try:
        response = (
            supabase.table("interested_organizers")
            .insert({"linkedin": linkedin, "devpost": devpost, "email": email})
            .execute()
        )
        return {"message": "Submission successful!"}, 200
    except Exception as e:
        return {"error": str(e)}, 500


def handler(request):
    if request.method == "POST":
        try:
            content_length = int(request.headers.get("Content-Length", 0))
            post_data = request.rfile.read(content_length)
            data = json.loads(post_data)

            response, status_code = handle_submission(data)

            return {
                "statusCode": status_code,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(response),
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e)}),
            }
    else:
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Method not allowed"}),
        }
