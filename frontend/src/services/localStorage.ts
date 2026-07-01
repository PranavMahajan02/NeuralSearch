import API_BASE_URL from "./api";

export async function getFolders() {

    const response = await fetch(
        `${API_BASE_URL}/platforms/local/folders`
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error("Unable to load folders.");
    }

    return data;
}


export async function addFolder(folder: string) {

    const response = await fetch(
        `${API_BASE_URL}/platforms/local/folders`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                folder
            })
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Unable to add folder.");
    }

    return data;
}


export async function removeFolder(folder: string) {

    const response = await fetch(
        `${API_BASE_URL}/platforms/local/folders`,
        {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                folder
            })
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Unable to remove folder.");
    }

    return data;
}


export async function indexLocalStorage() {

    const response = await fetch(
        `${API_BASE_URL}/platforms/local/index`,
        {
            method: "POST"
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Indexing failed.");
    }

    return data;
}