from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
from flask import Blueprint, current_app, json, jsonify, redirect, render_template, send_from_directory, session, request
from supabase import create_client

from app.routes.auth import check_auth

bp = Blueprint("dashboard", __name__)

load_dotenv(".env.local")

# supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# server static files
@bp.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


# serve index.htm
@bp.route("/")
def index():
    return send_from_directory("templates", "index.html")

# dashboard route
@bp.route("/dashboard")
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
        current_app.logger.error(f"dashboard error: {str(e)}")
        return redirect("/")


# handle form submissions
@bp.route("/submissions", methods=["POST"])
def submissions():
    # is user logged in?
    if "linkedin_id" not in session:
        refresh_response = check_auth()
        if refresh_response.status_code != 200:
            return redirect("/auth/linkedin")

    client_id = session.get("linkedin_id")
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
                        "error": "rate limit exceeded",
                        "message": "only 1 submission allowed every 5 minutes",
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

    try:
        # is it json?
        if not request.is_json:
            return jsonify({"error": "request must be JSON"}), 400

        data = request.get_json()
        if "devpost" not in data:
            return jsonify({"error": "devpost link is required"}), 400
        if "website" not in data:
            return jsonify({"error": "hackathon website link is required"}), 400

        user_response = (
            supabase.table("users")
            .select("*")
            .eq("linkedin_id", session["linkedin_id"])
            .execute()
        )

        if not user_response.data:
            return jsonify({"error": "user not found"}), 404

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
        }

        if existing_submission.data and len(existing_submission.data) > 0:
            existing_id = existing_submission.data[0]["id"]
            response = (
                supabase.table("interested_organizers")
                .update(submission_data)
                .eq("id", existing_id)
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
            current_app.logger.error(f"Supabase error: {response.error}")
            return (
                jsonify({"error": "Database error", "details": str(response.error)}),
                500,
            )

        return jsonify({"message": "submission successful!"}), 200

    except Exception as e:
        current_app.logger.error(f"submission error: {str(e)}", exc_info=True)
        return jsonify({"error": "internal server error", "details": str(e)}), 500


@bp.route("/user-hackathons/<linkedin_id>")
def get_user_hackathons(linkedin_id):
    try:
        if not linkedin_id:
            return jsonify({"error": "Invalid user ID"}), 400

        response = (
            supabase.table("devpost_hackathons")
            .select("linkedin_id, devpost_link, created_at")
            .eq("linkedin_id", linkedin_id)
            .execute()
        )

        if not response.data:
            return jsonify([])

        # cleaning up
        hackathons = []
        for item in response.data:
            try:
                url = item["devpost_link"]
                name = (
                    url.replace("https://", "")
                    .replace("http://", "")
                    .split(".devpost.com")[0]
                )

                hackathons.append(
                    {
                        "linkedin_id": item["linkedin_id"],
                        "devpost_link": url,
                        "name": name,
                        "created_at": item["created_at"],
                    }
                )
            except KeyError as e:
                print(f"missing key in hackathon data: {e}")
                continue

        return jsonify(hackathons)

    except Exception as e:
        print(f"Error fetching hackathons: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/hackathon-details", methods=["GET"])
def get_hackathon_details_route():
    actual_devpost_link = request.args.get("link")

    if not actual_devpost_link:
        return jsonify({"error": "devpost link parameter 'link' is required"}), 400

    try:
        response = (
            supabase.table("devpost_hackathons")
            .select(
                "project_links, github_links, last_scraped_at, datesandtimes, commit_validity_status"
            )
            .eq("devpost_link", actual_devpost_link)
            .maybe_single()
            .execute()
        )

        if not response.data:
            return (
                jsonify(
                    {
                        "message": "no data found for this hackathon yet",
                        "data_exists": False,
                        "devpost_link": actual_devpost_link,
                    }
                ),
                200,
            )

        db_data = response.data

        def parse_json_array_field(field_data):
            parsed_list = []
            if isinstance(field_data, str) and field_data.strip():
                try:
                    parsed_list = json.loads(field_data)
                    if not isinstance(parsed_list, list):
                        parsed_list = []
                except json.JSONDecodeError:
                    parsed_list = []
            elif isinstance(field_data, list):
                parsed_list = field_data
            return parsed_list

        project_links_list = parse_json_array_field(db_data.get("project_links"))
        github_links_list = parse_json_array_field(db_data.get("github_links"))
        commit_status_list = parse_json_array_field(
            db_data.get("commit_validity_status")
        )

        dates_array_for_display = None
        raw_dates = db_data.get("datesandtimes")
        if isinstance(raw_dates, str) and raw_dates.strip():
            try:
                parsed_dates = json.loads(raw_dates)
                if isinstance(parsed_dates, list) and len(parsed_dates) == 2:
                    dates_array_for_display = parsed_dates
            except json.JSONDecodeError:
                print(
                    f"warning: could not decode datesandtimes JSON for {actual_devpost_link}"
                )
        elif isinstance(raw_dates, list) and len(raw_dates) == 2:
            dates_array_for_display = raw_dates

        return (
            jsonify(
                {
                    "data_exists": True,
                    "devpost_link": actual_devpost_link,
                    "project_count": len(project_links_list),
                    "last_scraped_at": db_data.get("last_scraped_at"),
                    "datesandtimes": dates_array_for_display,
                    "project_links": project_links_list,
                    "github_links": github_links_list,
                    "commit_validity_status": commit_status_list,
                }
            ),
            200,
        )

    except Exception as e:
        import traceback

        print(
            f"error fetching hackathon details for {actual_devpost_link}: {str(e)}\n{traceback.format_exc()}"
        )
        return (
            jsonify({"error": f"server error fetching details.", "data_exists": False}),
            500,
        )
