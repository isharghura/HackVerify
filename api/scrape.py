from http.server import BaseHTTPRequestHandler
from bs4 import BeautifulSoup
import requests
import json
import time


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()

            test_url = "https://cuhacking6.devpost.com"
            all_project_links = []
            pg_num = 1
            max_pages = 5

            start_time = time.time()
            time_limit = 8

            # scrape through devpost to find all projects
            while pg_num < max_pages:
                if time.time() - start_time > time_limit:
                    self.wfile.write(
                        f"reached time limit after processing {pg_num-1} pages: ".encode()
                    )
                    break

                print(f"getting all projects on page {pg_num}")
                proj_gallery_url = f"{test_url}/project-gallery?page={pg_num}"

                try:
                    result = requests.get(proj_gallery_url)
                    gallery = BeautifulSoup(result.text, "html.parser")

                    # project link location
                    curr_project_links = gallery.find_all(
                        "a", class_="block-wrapper-link fade link-to-software"
                    )

                    if not curr_project_links:
                        print(f"No projects on page {pg_num}")
                        break

                    for link in curr_project_links:
                        all_project_links.append(link["href"])

                    pg_num += 1

                except Exception as e:
                    self.wfile.write(
                        f"error on page {pg_num}: {str(e)}, processing now".encode()
                    )
                    break

            print(f"found {len(all_project_links)} projects")
            self.wfile.write(
                f"found {len(all_project_links)} projects across {pg_num-1} pages\n".encode()
            )

            all_github_links = []
            max_projects = min(len(all_project_links), 75)

            for i, project_link in enumerate(all_project_links[:max_projects]):
                if time.time() - start_time > time_limit:
                    self.wfile.write(
                        f"reached time limit after processing {pg_num-1} pages: ".encode()
                    )
                    break

                github_link = None
                # scrape through each project
                try:
                    result = requests.get(project_link)
                    project = BeautifulSoup(result.text, "html.parser")

                    # find github repo link
                    for a_tag in project.find_all("a", href=True):
                        if "github.com" in a_tag["href"]:
                            github_link = a_tag["href"]
                            break

                    if github_link:
                        print(f"found {github_link} from {project_link}")
                        all_github_links.append(github_link)
                    else:
                        print("couldn't find github link")
                        all_github_links.append(
                            f"no github link found for: {project_link}"
                        )
                except Exception as e:
                    all_github_links.append(
                        f"could not scrape {project_link}: {str(e)}"
                    )
            self.wfile.write(
                f"processed {len(github_link)} projects in {time.time().start_time:.2f} seconds \n\n".encode()
            )
            self.wfile.write(str(all_github_links).encode())
            return

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(f"server error: {str(e)}".encode())
            return
