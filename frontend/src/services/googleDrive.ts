import API_BASE_URL from "./api";

export async function connectGoogleDrive() {

    const response = await fetch(
        `${API_BASE_URL}/platforms/google-drive/connect`
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Unable to connect Google Drive.");
    }

    return data;
}

export async function getGoogleDriveStatus() {

    const response = await fetch(
        `${API_BASE_URL}/platforms/google-drive/status`
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error("Unable to get Google Drive status.");
    }

    return data;
}

export async function disconnectGoogleDrive() {

    const response = await fetch(
        `${API_BASE_URL}/platforms/google-drive/disconnect`,
        {
            method: "POST"
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Unable to disconnect Google Drive.");
    }

    return data;
}