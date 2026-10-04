import API_BASE_URL from "./api";

const TOKEN_KEY = "access_token";


export async function login(
    email: string,
    password: string
) {

    const response = await fetch(

        `${API_BASE_URL}/auth/login`,

        {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                email,
                password

            })

        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.detail || "Login failed."

        );

    }

    localStorage.setItem(
        TOKEN_KEY,
        data.access_token
    );

    return data;
}


export async function register(

    name: string,
    email: string,
    password: string

) {

    const response = await fetch(

        `${API_BASE_URL}/auth/register`,

        {

            method: "POST",

            headers: {

                "Content-Type": "application/json"

            },

            body: JSON.stringify({

                name,
                email,
                password

            })

        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.detail || "Registration failed."

        );

    }

    return data;
}


export async function getProfile() {

    const token = localStorage.getItem(
        TOKEN_KEY
    );

    const response = await fetch(

        `${API_BASE_URL}/auth/profile`,

        {

            headers: {

                Authorization: `Bearer ${token}`

            }

        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.detail || "Unable to fetch profile."

        );

    }

    return data;
}


export async function logout() {

    const token = localStorage.getItem(TOKEN_KEY);

    if (token) {

        try {

            await fetch(

                `${API_BASE_URL}/auth/logout`,

                {

                    method: "POST",

                    headers: {

                        Authorization: `Bearer ${token}`

                    }

                }

            );

        }

        catch (e) {

            console.error(e);

        }

    }

    localStorage.removeItem(TOKEN_KEY);

}


export function getToken() {

    return localStorage.getItem(
        TOKEN_KEY
    );

}


export function isLoggedIn() {

    return getToken() !== null;

}