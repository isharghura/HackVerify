import sys
import os
from supabase import create_client
from datetime import datetime, timezone

# function to test
from app import scrape_devpost_link, SUPABASE_KEY, SUPABASE_URL

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def test_find_projects():
    TEST_URL = "https://cuhacking6.devpost.com"
    print(f"testing with {TEST_URL}")

    scrape_devpost_link(TEST_URL)

    # verify
    result = (
        supabase.table("devpost_hackathons")
        .select("*")
        .eq("devpost_link", TEST_URL)
        .execute()
    )

    if result.data:
        print(f"Found {len(result.data[0]['project_links'])} projects")
    else:
        print("No data found")


if __name__ == "__main__":
    test_find_projects()
