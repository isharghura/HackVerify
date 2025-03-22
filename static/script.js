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
        const response = await fetch("/api/submit", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ linkedin, devpost, email }),
        });

        const data = await response.json();
        alert("Thanks, reviewing your application!");
    } catch (error) {
        console.error("Error:", error);
        alert("Something happened, please try again!");
    }
});