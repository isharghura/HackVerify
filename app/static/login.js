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