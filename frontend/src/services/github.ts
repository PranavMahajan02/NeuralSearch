import API_BASE_URL from "./api";

function getToken() {
    return localStorage.getItem("access_token");
}

export async function connectGithub() {

    const response = await fetch(

        `${API_BASE_URL}/platforms/github/connect`,

        {

            headers: {

                Authorization: `Bearer ${getToken()}`

            }

        }

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

        `${API_BASE_URL}/platforms/github/status`,

        {

            headers: {

                Authorization: `Bearer ${getToken()}`

            }

        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.message || "Unable to fetch GitHub status."

        );

    }

    return data;

}


export async function disconnectGithub() {

    const response = await fetch(

        `${API_BASE_URL}/platforms/github/disconnect`,

        {

            method: "POST",

            headers: {

                Authorization: `Bearer ${getToken()}`

            }

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