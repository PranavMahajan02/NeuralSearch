import API_BASE_URL from "./api";

export async function getLoginState() {

    const token = localStorage.getItem("access_token");

    const response = await fetch(

        `${API_BASE_URL}/auth/login-state`,

        {

            headers: {

                Authorization: `Bearer ${token}`

            }

        }

    );

    if (!response.ok) {

        throw new Error("Unable to load login state.");

    }

    return await response.json();

}