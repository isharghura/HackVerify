from supabase import create_client, Client
from dotenv import load_dotenv
import os

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
