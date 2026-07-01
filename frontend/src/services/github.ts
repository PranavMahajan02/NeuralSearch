import API_BASE_URL from "./api";

export async function connectGithub() {

    const response = await fetch(
        `${API_BASE_URL}/platforms/github/connect`
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.message || "Unable to connect GitHub."
        );
    }

    return data;
}


export async function getGithubStatus() {

    const response = await fetch(
        `${API_BASE_URL}/platforms/github/status`
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            "Unable to fetch GitHub status."
        );
    }

    return data;
}


export async function disconnectGithub() {

    const response = await fetch(
        `${API_BASE_URL}/platforms/github/disconnect`,
        {
            method: "POST"
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.message || "Unable to disconnect GitHub."
        );
    }

    return data;
}