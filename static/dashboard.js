document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById("verificationForm");
    if (form) {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const devpostInput = document.getElementById("devpost");
            const websiteInput = document.getElementById("website");

            if (!devpostInput || !devpostInput.value) {
                alert("Please enter your hackathon's Devpost link!");
                return;
            }
            if (!websiteInput || !websiteInput.value) {
                alert("Please enter your hackathon's website link!");
                return;
            }

            const cleanedDevpostLink = cleanDevpostLink(devpostInput.value);

            try {
                const response = await fetch("/api/submissions", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        devpost: cleanDevpostLink,
                        website: document.getElementById("website").value
                    }),
                    credentials: "include"
                });

                if (!response.ok) {
                    const errorResponse = response.clone();
                    let errorData;
                    try {
                        errorData = await errorResponse.json();
                    } catch {
                        errorData = { error: await errorResponse.text() };
                    }
                    throw new Error(errorData.error || errorData.message || "submission failed");
                }

                const data = await response.json();
                alert("Thanks, reviewing your submission!");
                form.reset();
            } catch (error) {
                console.error("submission error:", error);
                alert(error.message || "Submission failed. Please try again.");
            }
        });
    } else {
        console.warn("Verfication form not found");
    }

    checkDashboardAccess();

    const logoutButton = document.querySelector('.logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
    } else {
        console.warn("Logout button not found");
    }
});

function checkDashboardAccess() {
    fetch("/dashboard", {
        credentials: "include"
    })
        .then(response => {
            if (response.status === 403 || response.status === 401) {
                alert("Please login first!");
            } else if (response.ok) {
                console.log("welcome to the dashboard!");
            }
        })
        .catch(error => {
            console.error("Error:", error);
        });
}

async function handleLogout() {
    try {
        const response = await fetch("/logout", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            credentials: "include"
        });

        if (!response.ok) {
            const errorResponse = response.clone();
            let errorData;
            try {
                errorData = await errorResponse.json();
            } catch {
                errorData = { error: await errorResponse.text() };
            }
            throw new Error(errorData.error || "logout failed");
        }

        const data = await response.json();
        console.log("logout successful", data);
        alert("Logged out successfully!");
        window.location.href = "/";
    } catch (error) {
        console.error("logout error:", error);
        alert("Logout failed. Please try again.");
    }
}

// get user's hackathons if they've been verified
// when user clicks hackathon displays its data
document.addEventListener('DOMContentLoaded', function () {
    const linkedinId = document.body.dataset.linkedinId;

    const submitHackathonView = document.getElementById('submit-hackathon-view');
    const hackathonDetailContainer = document.getElementById('hackathon-detail-view-container');

    const hackathonsListDiv = document.querySelector('.hackathons-list');
    const submitHackathonTab = document.getElementById('submit-hackathon-tab');

    const detailHackathonName = document.getElementById('hackathon-detail-name');
    const detailDevpostLink = document.getElementById('hackathon-detail-devpost-link');
    const detailInfoDiv = document.getElementById('hackathon-detail-info');
    const fetchDataButton = document.getElementById('fetch-data-button');
    const fetchStatusDiv = document.getElementById('fetch-process-status');

    let currentActiveHackathonLink = null;

    // changing tabs
    function setActiveView(viewToShow) {
        submitHackathonView.style.display = 'none';
        hackathonDetailContainer.style.display = 'none';
        viewToShow.style.display = 'block';
    }

    // activating tab
    function setActiveSidebarTab(activeTabElement) {
        document.querySelectorAll('.sidebar .sidebar-tab.active').forEach(tab => {
            tab.classList.remove('active');
        });
        if (activeTabElement) {
            activeTabElement.classList.add('active');
        }
    }

    submitHackathonTab.addEventListener('click', () => {
        setActiveSidebarTab(submitHackathonTab);
        setActiveView(submitHackathonView);
        currentActiveHackathonLink = null;
    });

    // load the user's hackathons
    function loadUserHackathons() {
        if (!linkedinId) {
            hackathonsListDiv.innerHTML = `<div class="no-hackathons"><i class="fa-solid fa-circle-exclamation"></i> LinkedIn ID not found.</div>`;
            return;
        }
        hackathonsListDiv.innerHTML = `<div class="loading-hackathons"><i class="fa-solid fa-spinner fa-spin"></i> Loading your hackathons...</div>`;

        fetch(`/api/user-hackathons/${linkedinId}`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(hackathons => {
                hackathonsListDiv.innerHTML = '';
                if (hackathons.length === 0) {
                    hackathonsListDiv.innerHTML = `<div class="no-hackathons"><i class="fa-solid fa-folder-open"></i> No verified hackathons yet.</div>`;
                    return;
                }
                hackathons.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                hackathons.forEach(hackathon => createHackathonSidebarTab(hackathon));
            })
            .catch(error => {
                console.error('Error fetching hackathons:', error);
                hackathonsListDiv.innerHTML = `<div class="no-hackathons error-message"><i class="fa-solid fa-triangle-exclamation"></i> Error loading hackathons.</div>`;
            });
    }

    // sidebar creation
    function createHackathonSidebarTab(hackathon) {
        const hackathonTab = document.createElement('div');
        hackathonTab.className = 'sidebar-tab hackathon-item';
        hackathonTab.innerHTML = `<i class="fa-solid fa-trophy"></i> <span class="hackathon-name">${hackathon.name}</span>`;
        hackathonTab.dataset.devpostLink = hackathon.devpost_link;
        hackathonTab.dataset.hackathonName = hackathon.name;

        hackathonTab.addEventListener('click', function () {
            setActiveSidebarTab(this);
            setActiveView(hackathonDetailContainer);
            currentActiveHackathonLink = this.dataset.devpostLink;
            displayHackathonDetails(this.dataset.hackathonName, this.dataset.devpostLink);
        });
        hackathonsListDiv.appendChild(hackathonTab);
    }

    // display hackathon's details that was clicked
    async function displayHackathonDetails(name, devpostLink) {
        const cleanedDevpostLink = cleanDevpostLink(devpostLink);
        detailDevpostLink.href = cleanedDevpostLink;

        detailHackathonName.textContent = name;
        detailDevpostLink.href = devpostLink;
        const displayDevpostName = devpostLink.replace(/^(https?:\/\/)?(www\.)?/, '').split('/')[0];
        detailDevpostLink.textContent = displayDevpostName ? displayDevpostName : "View on Devpost";

        const detailInfoDiv = document.getElementById('hackathon-detail-info');
        const fetchStatusDiv = document.getElementById('fetch-process-status');
        const fetchDataButton = document.getElementById('fetch-data-button');

        // spinning wheel
        detailInfoDiv.innerHTML = `<div class="loading-details"><i class="fa-solid fa-spinner fa-spin"></i> Loading hackathon details...</div>`;
        fetchStatusDiv.innerHTML = '';
        if (fetchDataButton) fetchDataButton.disabled = true;

        try {
            // see if backend already has hackathon's data
            const initialDetailsResponse = await fetch(`/api/hackathon-details?link=${encodeURIComponent(cleanedDevpostLink)}`);
            if (!initialDetailsResponse.ok) {
                const errorData = await initialDetailsResponse.json().catch(() => ({ error: "failed to parse error response" }));
                throw new Error(`failed to fetch initial details (${initialDetailsResponse.status}): ${errorData.error || initialDetailsResponse.statusText}`);
            }
            const initialData = await initialDetailsResponse.json();

            if (initialData.error) {
                throw new Error(`${initialData.error}`);
            }

            let {
                project_links: projectLinks,
                github_links: githubLinks,
                commit_validity_status: commitStatus,
            } = initialData

            projectLinks = projectLinks || [];
            githubLinks = githubLinks || [];
            commitStatus = commitStatus || [];

            // do we need to validate data or can we just pull from our database without doing any checks
            if (projectLinks.length > 0 && commitStatus.length === 0 || projectLinks.length > commitStatus.length) {
                let verificationReason = commitStatus.length === 0
                    ? "Commit not yet verified."
                    : `New projects detected, re-validating.`;

                fetchStatusDiv.innerHTML = `<p class="status-info"><i class="fa-solid fa-gears fa-spin"></i> ${verificationReason} Validating now...</p>`;
                detailInfoDiv.innerHTML = `<p class="status-info"><i class="fa-solid fa-gears fa-spin"></i> Please wait, running commit validation for ${projectLinks.length} projects, this might take a while...</p>`;

                try {
                    const validateResponse = await fetch('/validate_commits', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ devpost_link_to_check: cleanedDevpostLink })
                    });
                    const validationResult = await validateResponse.json();

                    if (!validateResponse.ok || validationResult.error) {
                        throw new Error(validationResult.error || `commit verification call failed (${validateResponse.status})`);
                    }

                    // verified, now we can update commit status
                    commitStatus = validationResult.commit_validity_status || [];
                    initialData.commit_validity_status = commitStatus;
                    fetchStatusDiv.innerHTML = `<p class="status-success"><i class="fa-solid fa-check-circle"></i> Commit verification complete!</p>`;
                } catch (validationError) {
                    console.error("error during commit verification:", validationError);
                    fetchStatusDiv.innerHTML = `<p class="status-error"><i class="fa-solid fa-triangle-exclamation"></i> Auto commit verification failed: ${validationError.message}, try again!</p>`;
                }
            } else if (projectLinks.length === 0) {
                fetchStatusDiv.innerHTML = `<p class="status-info">No projects found for this hackathon, fetch the hackathon's data first!</p>`;
            } else {
                fetchStatusDiv.innerHTML = `<p class="status-info">Project details and commits loaded</p>`;
            }

            // update ui
            updateDetailInfo({
                data_exists: initialData.data_exists,
                last_scraped_at: initialData.last_scraped_at,
                datesandtimes: initialData.datesandtimes,
                project_links: projectLinks,
                github_links: githubLinks,
                commit_validity_status: commitStatus
            });

        } catch (error) {
            console.error("error in displayHackathonDetails:", error);
            detailInfoDiv.innerHTML = `<p class="error-message"><i class="fa-solid fa-triangle-exclamation"></i> Error loading details: ${error.message}</p>`;
            fetchStatusDiv.innerHTML = `<p class="status-error"><i class="fa-solid fa-triangle-exclamation"></i> Failed to display hackathon details: ${error.message}</p>`;
        } finally {
            if (fetchDataButton) fetchDataButton.disabled = false;
        }
    }
    
    // update the info that is currently known about the hackathon
    function updateDetailInfo(data) {
        const detailInfoDiv = document.getElementById('hackathon-detail-info');
        if (!detailInfoDiv) {
            console.error("detailInfoDiv not found!");
            return;
        }

        if (data.data_exists === false || !data.project_links || data.project_links.length === 0) {
            detailInfoDiv.innerHTML = `<p><i class="fa-solid fa-info-circle"></i> No project data has been fetched or found for this hackathon yet</p>`;
            return;
        }

        let basicInfoHtml = '';
        let datesHtml = "Not available";
        if (data.datesandtimes && Array.isArray(data.datesandtimes) && data.datesandtimes.length === 2) {
            try {
                // clean formatting
                const startDate = new Date(data.datesandtimes[0]).toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                const endDate = new Date(data.datesandtimes[1]).toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                datesHtml = `<strong>Period:</strong> ${startDate} - ${endDate}`;
            } catch (e) { console.warn("error formatting dates:", e); }
        }

        basicInfoHtml = `
            <p><strong>Last Fetched:</strong> ${data.last_scraped_at ? new Date(data.last_scraped_at).toLocaleString() : 'Never'}</p>
            <p>${datesHtml}</p>
            <p><strong>Total Projects Processed:</strong> ${data.project_links ? data.project_links.length : 'N/A'}</p>
        `;

        // projects that are flagged or don't have a github link in them
        const flaggedProjects = [];
        const naGithubProjects = [];

        const projectLinks = data.project_links || [];
        const githubLinks = data.github_links || [];
        const commitStatus = data.commit_validity_status || [];

        // indexing is correlated between projectLinks, githubLinks, and commitStatus
        for (let i = 0; i < projectLinks.length; i++) {
            const projectLink = projectLinks[i];
            const githubLink = githubLinks.length > i ? githubLinks[i] : "Data missing";
            const status = commitStatus.length > i ? commitStatus[i] : "Data missing";

            if (status === false) {
                flaggedProjects.push({ projectLink, githubLink });
            } else if (status === "NA") {
                naGithubProjects.push({ projectLink, githubLink });
            }
        }

        // dropdown menu for flagged projs
        let flaggedProjectsHtml = '';
        if (flaggedProjects.length > 0) {
            const listItems = flaggedProjects.map(item => {
                const ghLinkText = (item.githubLink && item.githubLink !== "no GitHub link found" && item.githubLink !== "Data missing")
                    ? `<a href="${item.githubLink}" target="_blank" class="project-entry-github">GitHub: ${item.githubLink.split('/').slice(-2).join('/')}</a>`
                    : `<span class="project-entry-github no-github-text">(GitHub: Not found)</span>`;
                return `<li>
                            <a href="${item.projectLink}" target="_blank" class="project-entry-devpost">Project: ${item.projectLink.substring(item.projectLink.lastIndexOf('/') + 1)}</a>
                            ${ghLinkText}
                        </li>`;
            }).join('');

            flaggedProjectsHtml = `
                <details id="flagged-projects-details">
                    <summary>${flaggedProjects.length} project(s) flagged (commits outside timeframe)</summary>
                    <ul>${listItems}</ul>
                </details>
            `;
        } else {
            flaggedProjectsHtml = `<p><i class="fa-solid fa-check-circle" style="color: green;"></i> No projects flagged for commiting outside the timeframe!</p>`;
        }

        // dropdown menu for NA github links
        let naGithubProjectsHtml = '';
        if (naGithubProjects.length > 0) {
            const listItems = naGithubProjects.map(item => {
                const ghText = (item.githubLink === "no GitHub link found" || item.githubLink === "Data missing")
                    ? `<span class="project-entry-github no-github-text">(No GitHub link found on Devpost project page)</span>`
                    : `<span class="project-entry-github no-github-text">(GitHub status: ${item.githubLink})</span>`;

                return `<li>
                            <a href="${item.projectLink}" target="_blank" class="project-entry-devpost">Project: ${item.projectLink.substring(item.projectLink.lastIndexOf('/') + 1)}</a>
                            ${ghText}
                        </li>`;
            }).join('');

            naGithubProjectsHtml = `
                <details id="na-github-projects-details">
                    <summary>${naGithubProjects.length} project(s) where GitHub link was not found on Devpost</summary>
                    <ul>${listItems}</ul>
                </details>
            `;
        } else {
            naGithubProjectsHtml = `<p><i class="fa-solid fa-check-circle" style="color: green;"></i> GitHub links were found for all applicable projects!</p>`;
        }

        // combine all details
        detailInfoDiv.innerHTML = basicInfoHtml + flaggedProjectsHtml + naGithubProjectsHtml;
    }    

    // call our apis to get data
    if (fetchDataButton) {
        fetchDataButton.addEventListener('click', async function () {
            const button = this;

            // error checking
            if (!currentActiveHackathonLink) {
                document.getElementById('fetch-process-status').innerHTML = `<p class="status-error">error: No active hackathon selected to fetch data for</p>`;
                return;
            }

            const cleanedDevpostLink = cleanDevpostLink(currentActiveHackathonLink);

            // extracting data / loading message
            button.disabled = true;
            button.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing...`;
            const localFetchStatusDiv = document.getElementById('fetch-process-status');
            localFetchStatusDiv.innerHTML = `<p class="status-info">Step 1/2: Scraping Devpost for project links...</p>`;

            // scrape the hackathon's devpost link
            try {
                const scrapeResponse = await fetch('/scrape_devpost_link', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ devpost_link: cleanedDevpostLink })
                });
                const scrapeResult = await scrapeResponse.json();
                if (!scrapeResponse.ok) throw new Error(scrapeResult.error || `scraping devpost failed (${scrapeResponse.status})`);

                const projectsMsg = scrapeResult.message || (scrapeResult.project_links ? `Found ${scrapeResult.project_links.length} projects.` : "Projects fetched");
                localFetchStatusDiv.innerHTML = `<p class="status-info">Step 1/2: ${projectsMsg}<br>Step 2/2: Fetching GitHub links...</p>`;

                const githubResponse = await fetch('/get_all_github_links', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ devpost_link: currentActiveHackathonLink })
                });
                const githubResult = await githubResponse.json();
                if (!githubResponse.ok) throw new Error(githubResult.error || `fetching GitHub links failed (${githubResponse.status})`);

                const githubsMsg = Array.isArray(githubResult) ? `Found ${githubResult.length} GitHub links.` : "GitHub links processed";
                localFetchStatusDiv.innerHTML = `<p class="status-success"><i class="fa-solid fa-check-circle"></i> Data fetch complete! ${githubsMsg} Refreshing details and verifying commits if needed...</p>`;

            } catch (error) {
                console.error('error during hackathon data fetch process:', error);
                localFetchStatusDiv.innerHTML = `<p class="status-error"><i class="fa-solid fa-triangle-exclamation"></i> Fetch Error: ${error.message}</p>`;
            } finally {
                button.disabled = false;
                button.innerHTML = '<i class="fa-solid fa-cloud-download"></i> Fetch Hackathon Data';
                if (currentActiveHackathonLink) {
                    displayHackathonDetails(detailHackathonName.textContent || "Selected Hackathon", currentActiveHackathonLink);
                }
            }
        });
    }

    // setup
    setActiveView(submitHackathonView);
    setActiveSidebarTab(submitHackathonTab);
    loadUserHackathons();
});

// clean devpost url
function cleanDevpostLink(url) {
    if (!url) return url;
    try {
        const parsed = new URL(url);
        return `${parsed.protocol}//${parsed.hostname}${parsed.pathname}`.replace(/\/$/, '');
    } catch (e) {
        console.error("Invalid URL:", url);
        return url;
    }
}