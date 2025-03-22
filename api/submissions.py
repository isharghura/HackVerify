from http.server import BaseHTTPRequestHandler
import json
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        linkedin = data.get("linkedin")
        devpost = data.get("devpost")
        email = data.get("email")

        try:
            supabase.table("organizers_interested").insert(
                {"linkedin": linkedin, "devpost": devpost, "email": email}
            ).execute()

            self.send_response(200)
            self.send_header("Content-type", "submissions/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Submission successful!"}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "submissions/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
