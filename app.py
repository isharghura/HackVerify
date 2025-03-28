from flask import (
    Flask,
    jsonify,
    redirect,
    request,
    send_from_directory,
    render_template,
    session,
)
import os
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv(".env.local")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(24)

# supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        if not code:
            return "Missing authorization code", 400

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
            app.logger.error(f"Token error: {token_data}")
            return f"LinkedIn token error: {token_data.get('error_description')}", 400

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        if "error" in token_data:
            return f"LinkedIn token error: {token_data['error_description']}", 400

        profile_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        profile_data = profile_response.json()

        if "error" in profile_data:
            app.logger.error(f"Profile error: {profile_data}")
            return f"LinkedIn API error: {profile_data['message']}", 400

        user_data = {
            "email": profile_data.get("email", ""),
            "linkedin_id": profile_data["sub"],
            "full_name": profile_data.get("name", ""),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat(),
            "email_verified": profile_data.get("email_verified"),
            "locale": profile_data.get("locale"),
            "given_name": profile_data.get("given_name"),
            "family_name": profile_data.get("family_name"),
            "picture": profile_data.get("picture"),
        }

        response = (
            supabase.table("users")
            .upsert(
                user_data,
                on_conflict="linkedin_id",  # update if linkedin_id exists
            )
            .execute()
        )

        # set up a session
        session.clear()
        session["linkedin_id"] = profile_data.get("sub")
        session["access_token"] = access_token
        session.permanent = True

        return redirect("/dashboard")

    except Exception as e:
        print("Callback error:", str(e))
        return "Authentication failed", 500


# dashboard route
@app.route("/dashboard")
def dashboard():
    if "linkedin_id" not in session:
        return redirect("/auth/linkedin")
    try:
        response = (
            supabase.table("users")
            .select("*")
            .eq("linkedin_id", session["linkedin_id"])
            .execute()
        )

        if not response.data:
            return redirect("/auth/linkedin")

        return render_template("dashboard.html", user=response.data[0])

    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        return redirect("/")


@app.route("/check-auth")
def check_auth():
    try:
        # is user in a session
        if "linkedin_id" not in session:
            return redirect("/auth/linkedin")

        # retrieve user
        user_data = (
            supabase.table("users")
            .select("*")
            .eq("linkedin_id", session["linkedin_id"])
            .execute()
            .data
        )

        if not user_data:
            return {"status": "unauthenticated"}, 401

        user = user_data[0]

        # does token need refreshing?
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
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                token_data = token_response.json()

                if "error" in token_data:
                    return {"status": "token_refresh_failed"}, 401

                # update user tokens in db
                expires_at = datetime.now() + timedelta(
                    seconds=token_data["expires_in"]
                )
                supabase.table("users").update(
                    {
                        "access_token": token_data["access_token"],
                        "expires_at": expires_at.isoformat(),
                    }
                ).eq("linkedin_id", session["linkedin_id"]).execute()

                # update session with new token
                session["access_token"] = token_data["access_token"]

            except Exception as e:
                app.logger.error(f"Token refresh failed: {str(e)}")
                return {"status": "token_refresh_failed"}, 401

        return {
            "status": "authenticated",
            "user": {
                "email": user["email"],
                "name": user["full_name"],
                "linkedin_id": user["linkedin_id"],
            },
        }, 200

    except Exception as e:
        app.logger.error(f"Auth check failed: {str(e)}")
        return {"status": "error", "message": str(e)}, 500


# handle form submissions
@app.route("/api/submissions", methods=["POST"])
def submissions():
    client_id = session.get("linkedin_id") or request.remote_addr
    current_time = datetime.now(timezone.utc)

    # get last request
    rate_check = (
        supabase.table("rate_limits")
        .select("created_at")
        .eq("client_id", client_id)
        .eq("endpoint", "submissions")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    # was there actually a request made before?
    if rate_check.data and len(rate_check.data) > 0:
        last_request_time = datetime.fromisoformat(
            rate_check.data[0]["created_at"]
        ).replace(tzinfo=timezone.utc)
        if current_time - last_request_time < timedelta(minutes=5):
            return (
                jsonify(
                    {
                        "error": "Rate limit exceeded",
                        "message": "Only 1 submission allowed every 5 minutes",
                    }
                ),
                429,
            )

    # update submission time
    supabase.table("rate_limits").upsert(
        {
            "client_id": client_id,
            "endpoint": "submissions",
            "created_at": current_time.isoformat(),
        },
        on_conflict="client_id,endpoint",
    ).execute()

    # is user logged in?
    if "linkedin_id" not in session:
        return redirect("/auth/linkedin")

    try:
        # is it json?
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if "devpost" not in data:
            return jsonify({"error": "Devpost link is required"}), 400
        if "website" not in data:
            return jsonify({"error": "Hackathon website link is required"}), 400

        user_response = (
            supabase.table("users")
            .select("*")
            .eq("linkedin_id", session["linkedin_id"])
            .execute()
        )

        if not user_response.data:
            return jsonify({"error": "User not found"}), 404

        user = user_response.data[0]

        existing_submission = (
            supabase.table("interested_organizers")
            .select("*")
            .eq("linkedin_id", user["linkedin_id"])
            .eq("devpost", data["devpost"])
            .execute()
        )

        submission_data = {
            "devpost": data["devpost"],
            "website": data["website"],
            "email": user["email"],
            "linkedin_id": user["linkedin_id"],
            "name": user.get("full_name", ""),
            "updated_at": current_time.isoformat(),
        }

        if existing_submission.data:
            response = (
                supabase.table("interested_organizers")
                .update(submission_data)
                .eq("id", existing_submission.data["id"])
                .execute()
            )
        else:
            submission_data["created_at"] = current_time.isoformat()
            response = (
                supabase.table("interested_organizers")
                .insert(submission_data)
                .execute()
            )

        # was insertion successful?
        if hasattr(response, "error") and response.error:
            app.logger.error(f"Supabase error: {response.error}")
            return (
                jsonify({"error": "Database error", "details": str(response.error)}),
                500,
            )

        return jsonify({"message": "Submission successful!"}), 200

    except Exception as e:
        app.logger.error(f"Submission error: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


def lambda_handler(event, context):
    from werkzeug.wrappers import Request, Response
    from werkzeug.wsgi import responder
    from werkzeug.exceptions import HTTPException

    @responder
    def application(environ, start_response):
        try:
            return app(environ, start_response)
        except HTTPException as e:
            return e

    return Request(event).get_response(application)


# run flask app
if __name__ == "__main__":
    app.run(port=8000)
    # app.run()

else:

    def create_app():
        return app

    api = create_app()
