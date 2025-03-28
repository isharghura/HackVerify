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
                    throw new Error(errorData.error || errorData.message || "Submission failed");
                }

                const data = await response.json();
                alert("Thanks, reviewing your submission!");
                form.reset();
            } catch (error) {
                console.error("Submission error:", error);
                alert(error.message || "Submission failed. Please try again.");
            }
        });
    } else {
        console.warn("Verfication form not found");
    }

    checkDashboardAccess();
});

function checkDashboardAccess() {
    fetch("/dashboard", {
        credentials: "include"
    })
        .then(response => {
            if (response.status === 403 || response.status === 401) {
                alert("Please login first!");
            } else if (response.ok) {
                console.log("Welcome to the dashboard!");
            }
        })
        .catch(error => {
            console.error("Error:", error);
        });
}