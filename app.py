from flask import Flask, redirect, request, send_from_directory
import json
import os
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(".env.local")

app = Flask(__name__)

# supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# linkedin oauth
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = "http://localhost:8000/auth/linkedin/callback"
# LINKEDIN_REDIRECT_URI = "https://hackverify.com/auth/linkedin/callback"


# server static files
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


# serve index.htm
@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


# linkedin oauth routes
@app.route("/auth/linkedin")
def linkedin_auth():
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&"
        f"client_id={LINKEDIN_CLIENT_ID}&"
        f"redirect_uri={LINKEDIN_REDIRECT_URI}&"
        f"scope=openid%20profile%20email&"
        f"state=anti_csrf_token"
    )
    return redirect(auth_url)


@app.route("/auth/linkedin/callback")
def linkedin_callback():
    try:
        code = request.args.get("code")
        token_response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LINKEDIN_REDIRECT_URI,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_data = token_response.json()

        if "error" in token_data:
            return f"LinkedIn token error: {token_data['error_description']}", 400

        access_token = token_data["access_token"]

        profile_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        profile_data = profile_response.json()

        if "error" in profile_data:
            return f"LinkedIn API error: {profile_data['message']}", 400

        user_data = {
            "linkedin_id": profile_data["sub"],
            "full_name": profile_data.get("name", ""),
            "email": profile_data.get("email", ""),
            "access_token": access_token,
        }

        supabase.table("users").upsert(user_data).execute()

        return redirect(f"/dashboard?id={profile_data['sub']}")

    except Exception as e:
        print("Error:", str(e))
        return "Authentication failed", 500


# dashboard route
@app.route("/dashboard")
def dashboard():
    linkedin_username = request.args.get("username")

    # does the user have access?
    if linkedin_username in ["ishar-ghura"]:
        return "Welcome to the dashboard!"
    else:
        return (
            "You don't have an account yet, we need to verify that you are a hackathon organizer first! Submit your info at https://www.hackverify.com",
            403,
        )


# handle form submissions
@app.route("/api/submissions", methods=["POST"])
def submissions():
    data = request.get_json()
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


# run flask app
if __name__ == "__main__":
    app.run(port=8000)
