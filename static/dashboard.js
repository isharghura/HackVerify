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

            try {
                const response = await fetch("/api/submissions", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        devpost: document.getElementById("devpost").value,
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
        detailHackathonName.textContent = name;
        detailDevpostLink.href = devpostLink;
        detailDevpostLink.textContent = devpostLink.replace(/^(https?:\/\/)?(www\.)?/, '').split('/')[0];

        detailInfoDiv.innerHTML = `<div class="loading-details"><i class="fa-solid fa-spinner fa-spin"></i> Loading hackathon details...</div>`;
        fetchStatusDiv.innerHTML = '';
        fetchDataButton.disabled = false;
        fetchDataButton.innerHTML = '<i class="fa-solid fa-cloud-download"></i> Fetch/Refresh Hackathon Data';


        try {
            const response = await fetch(`/api/hackathon-details?link=${encodeURIComponent(devpostLink)}`);
            if (!response.ok) throw new Error(`failed to fetch details: ${response.statusText}`);
            const data = await response.json();

            if (data.error) {
                detailInfoDiv.innerHTML = `<p class="error-message"><i class="fa-solid fa-circle-exclamation"></i> error: ${data.error}</p>`;
                return;
            }

            updateDetailInfo(data);

        } catch (error) {
            console.error("error loading hackathon details:", error);
            detailInfoDiv.innerHTML = `<p class="error-message"><i class="fa-solid fa-triangle-exclamation"></i> could not load details ${error.message}</p>`;
        }
    }

    function updateDetailInfo(data) {
        if (data.data_exists === false || (data.project_count === 0 && data.github_count === 0 && !data.last_scraped_at)) {
            detailInfoDiv.innerHTML = `<p><i class="fa-solid fa-info-circle"></i> No data has been fetched for this hackathon yet.</p>`;
        } else {
            let datesHtml = "not available";
            if (data.datesandtimes && Array.isArray(data.datesandtimes) && data.datesandtimes.length === 2) {
                try {
                    const startDate = new Date(data.datesandtimes[0]).toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                    const endDate = new Date(data.datesandtimes[1]).toLocaleString([], { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                    datesHtml = `<strong>Period:</strong> ${startDate} - ${endDate}`;
                } catch (e) { console.warn("error formatting dates:", e); }
            }

            detailInfoDiv.innerHTML = `
                <p><strong>Last fetched:</strong> ${data.last_scraped_at ? new Date(data.last_scraped_at).toLocaleString() : 'Never'}</p>
                <p>${datesHtml}</p>
                <p><strong>Projects Found:</strong> ${data.project_count !== undefined ? data.project_count : 'N/A'}</p>
                <p><strong>GitHub Links Found:</strong> ${data.github_count !== undefined ? data.github_count : 'N/A'}</p>
            `;
        }
    }

    // call apis to get data
    fetchDataButton.addEventListener('click', async function () {
        if (!currentActiveHackathonLink) {
            fetchStatusDiv.innerHTML = `<p class="status-error">Error: No active hackathon selected.</p>`;
            return;
        }

        this.disabled = true;
        this.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing...`;
        fetchStatusDiv.innerHTML = `<p class="status-info">Step 1/2: Scraping Devpost for project links...</p>`;

        try {
            // scrape devpost
            const scrapeResponse = await fetch('/scrape_devpost_link', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ devpost_link: currentActiveHackathonLink })
            });
            const scrapeResult = await scrapeResponse.json();
            if (!scrapeResponse.ok) {
                throw new Error(scrapeResult.error || `Scraping Devpost failed (${scrapeResponse.status})`);
            }
            const projectsMsg = scrapeResult.message || (scrapeResult.project_links ? `Found ${scrapeResult.project_links.length} projects.` : "Projects found.");
            fetchStatusDiv.innerHTML = `<p class="status-info">Step 1/2: ${projectsMsg}<br>Step 2/2: Fetching GitHub links...</p>`;

            // get github links
            const githubResponse = await fetch('/get_all_github_links', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ devpost_link: currentActiveHackathonLink })
            });
            const githubResult = await githubResponse.json();
            if (!githubResponse.ok) {
                throw new Error(githubResult.error || `Fetching GitHub links failed (${githubResponse.status})`);
            }
            const githubsMsg = Array.isArray(githubResult) ? `Found ${githubResult.length} GitHub links.` : "GitHub links processed.";
            fetchStatusDiv.innerHTML = `<p class="status-success"><i class="fa-solid fa-check-circle"></i> Processing complete! ${githubsMsg}</p>`;

            // display these results
            await displayHackathonDetails(detailHackathonName.textContent, currentActiveHackathonLink);

        } catch (error) {
            console.error('error during hackathon data fetch process:', error);
            fetchStatusDiv.innerHTML = `<p class="status-error"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${error.message}</p>`;
        } finally {
            this.disabled = false;
            this.innerHTML = '<i class="fa-solid fa-cloud-download"></i> Fetch/Refresh Hackathon Data';
        }
    });

    // setup
    setActiveView(submitHackathonView);
    setActiveSidebarTab(submitHackathonTab);
    loadUserHackathons();
});