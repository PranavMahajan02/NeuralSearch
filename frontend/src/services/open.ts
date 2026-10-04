import API_BASE_URL from "./api";

export async function openFile(
    platform: string,
    path?: string,
    file_id?: string
) {
    const response = await fetch(
        `${API_BASE_URL}/open/`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                platform,
                path,
                file_id
            })
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Unable to open file.");
    }

    return data;
}