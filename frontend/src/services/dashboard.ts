import API_BASE_URL from "./api";

function getAuthHeaders() {

    const token = localStorage.getItem("access_token");

    return {
        Authorization: `Bearer ${token}`
    };

}

export async function getDashboardStats() {

    const response = await fetch(

        `${API_BASE_URL}/dashboard/stats`,

        {
            headers: getAuthHeaders()
        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.message || "Unable to load dashboard statistics."

        );

    }

    return data;

}

export async function getDashboardPlatforms() {

    const response = await fetch(

        `${API_BASE_URL}/dashboard/platforms`,

        {
            headers: getAuthHeaders()
        }

    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(

            data.message || "Unable to load dashboard platforms."

        );

    }

    return data;

}   