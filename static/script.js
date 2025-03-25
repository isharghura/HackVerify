document.getElementById("devpostForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const devpost = document.getElementById("devpost").value;

    if (!devpost) {
        alert("Please enter a Devpost link!");
        return;
    }

    try {
        const response = await fetch("/api/submissions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ devpost }),
            credentials: "include"
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        const data = await response.json();
        alert("Thanks, reviewing your submission!");
    } catch (error) {
        console.error("Error:", error);
        alert("Something happened, please try again!");
    }
});

function checkDashboardAccess() {
    fetch("/dashboard", {
        credentials: "include"
    })
        .then(response => {
            if (response.status === 403 || response.status === 401) {
                alert("You don't have an account yet, we need to verify that you are a hackathon organizer first! Submit your info at https://www.hackverify.com");
            } else if (response.ok) {
                console.log("Welcome to the dashboard!");
            }
        })
        .catch(error => {
            console.error("Error:", error);
        });
}

document.getElementById("linkedin-login-btn").addEventListener("click", async (event) => {
    event.preventDefault();
    try {
        const response = await fetch("/check-auth", {
            credentials: "include"
        });

        if (response.ok) {
            window.location.href = "/dashboard";
        } else {
            window.location.href = "/auth/linkedin";
        }
    } catch (error) {
        console.error("Error:", error);
        window.location.href = "/auth/linkedin";
    }
});