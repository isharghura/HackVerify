document.getElementById("organizerForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const linkedin = document.getElementById("linkedin").value;
    const devpost = document.getElementById("devpost").value;
    const email = document.getElementById("email").value;

    if (!linkedin || !devpost || !email) {
        alert("Please fill in all fields!");
        return;
    }

    try {
        const response = await fetch("/api/submissions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ linkedin, devpost, email }),
        });

        const data = await response.json();
        alert("Thanks, reviewing your submission!");
    } catch (error) {
        console.error("Error:", error);
        alert("Something happened, please try again!");
    }
});

fetch("/dashboard")
    .then(response => {
        if (response.status === 403) {
            alert("You don't have an account yet, we need to verify that you are a hackathon organizer first! Submit your info at https://www.hackverify.com");
        } else {
            console.log("Welcome to the dashboard!");
        }
    });