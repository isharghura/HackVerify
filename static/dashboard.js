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