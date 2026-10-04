import API_BASE_URL from "./api";

export async function startIndexing(
    priorityPlatform: string,
    platforms: string[]
) {

    const token = localStorage.getItem("access_token");

    const response = await fetch(
        `${API_BASE_URL}/index/`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                priority_platform: priorityPlatform,
                platforms
            })
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.detail || data.message || "Unable to start indexing."
        );
    }

    return data;
}

// ===============================
// ADD THIS FUNCTION
// ===============================

export async function getIndexJobs() {

    const token = localStorage.getItem("access_token");

    const response = await fetch(
        `${API_BASE_URL}/index/jobs`,
        {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.detail || data.message || "Unable to fetch indexing jobs."
        );
    }

    return data;
}