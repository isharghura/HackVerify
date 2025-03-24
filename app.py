from flask import Flask, redirect, request, send_from_directory, render_template
import os
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv(".env.local")

app = Flask(__name__)

# supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# linkedin oauth
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

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
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        expires_at = datetime.now() + timedelta(seconds=expires_in)

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
            "email": profile_data.get("email", ""),
            "linkedin_id": profile_data["sub"],
            "full_name": profile_data.get("name", ""),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat(),
        }

        supabase.table("users").upsert(
            user_data,
            on_conflict="linkedin_id",  # update if linkedin_id exists
        ).execute()

        return redirect(f"/dashboard?email={profile_data.get('email')}")

    except Exception as e:
        print("Error:", str(e))
        return "Authentication failed", 500


# dashboard route
@app.route("/dashboard")
def dashboard():
    user_email = request.args.get("email")

    response = supabase.table("users").select("*").eq("email", user_email).execute()

    if not response.data:
        return "User not found", 404

    user_data = response.data[0]

    return render_template("dashboard.html", user=user_data)


@app.route("/check-auth")
def check_auth():
    email = request.args.get("email")
    if not email:
        return "Email required", 400

    user = supabase.table("users").select("*").eq("email", email).execute().data[0]

    if not user:
        return redirect("/auth/linkedin")

    # does token need refresh?
    if datetime.now() > datetime.fromisoformat(user["expires_at"]):
        try:
            token_response = requests.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": user["refresh_token"],
                    "client_id": LINKEDIN_CLIENT_ID,
                    "client_secret": LINKEDIN_CLIENT_SECRET,
                },
            )
            token_data = token_response.json()
            # update user tokens in db
            supabase.table("users").update(
                {
                    "access_token": token_data["access_token"],
                    "expires_at": (
                        datetime.now() + timedelta(seconds=token_data["expires_in"])
                    ).isoformat(),
                }
            ).eq("email", email).execute()
        except:
            return redirect("/auth/linkedin")

    return {"status": "authenticated"}


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
