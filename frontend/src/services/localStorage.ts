import API_BASE_URL from "./api";

function getAuthHeaders() {

    const token = localStorage.getItem("access_token");

    return {

        "Content-Type": "application/json",

        Authorization: `Bearer ${token}`

    };

}

export async function getFolders() {

    const response = await fetch(

        `${API_BASE_URL}/platforms/local/folders`,

        {

            headers: getAuthHeaders()

        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.message || "Unable to load folders."

        );

    }

    return data;

}


export async function addFolder(folder: string) {

    const response = await fetch(

        `${API_BASE_URL}/platforms/local/folders`,

        {

            method: "POST",

            headers: getAuthHeaders(),

            body: JSON.stringify({

                folder

            })

        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.message || "Unable to add folder."

        );

    }

    return data;

}


export async function removeFolder(folder: string) {

    const response = await fetch(

        `${API_BASE_URL}/platforms/local/folders`,

        {

            method: "DELETE",

            headers: getAuthHeaders(),

            body: JSON.stringify({

                folder

            })

        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.message || "Unable to remove folder."

        );

    }

    return data;

}


export async function indexLocalStorage() {

    const response = await fetch(

        `${API_BASE_URL}/platforms/local/index`,

        {

            method: "POST",

            headers: getAuthHeaders()

        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.message || "Indexing failed."

        );

    }

    return data;

}
export async function pickFolder() {

    const token = localStorage.getItem("access_token");

    const response = await fetch(

        `${API_BASE_URL}/platforms/local/pick-folder`,

        {

            method: "POST",

            headers: {

                Authorization: `Bearer ${token}`

            }

        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.message || "Unable to open native picker."

        );

    }

    return data;

}