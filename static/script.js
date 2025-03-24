document.getElementById("organizerForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const linkedin = document.getElementById("linkedin").value;
    const devpost = document.getElementById("devpost").value;

    if (!linkedin || !devpost) {
        alert("Please fill in all fields!");
        return;
    }

    try {
        const response = await fetch("/api/submissions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ linkedin, devpost }),
        });

        const data = await response.json();
        alert("Thanks, reviewing your submission!");
    } catch (error) {
        console.error("Error:", error);
        alert("Something happened, please try again!");
    }
});

function checkDashboardAccess() {
    fetch("/dashboard")
        .then(response => {
            if (response.status === 403) {
                alert("You don't have an account yet, we need to verify that you are a hackathon organizer first! Submit your info at https://www.hackverify.com");
            } else {
                console.log("Welcome to the dashboard!");
            }
        })
        .catch(error => {
            console.error("Error:", error);
        });
}

document.getElementById("loginButton").addEventListener("click", async (event) => {
    event.preventDefault();

    const email = localStorage.getItem("user_email");
    if (email) {
        const response = await fetch(`/check-auth?email=${encodeURIComponent(email)}`);
        if (response.ok) {
            window.location.href = "/dashboard";
            return;
        }
    }

    window.location.href = "/auth/linkedin";
});