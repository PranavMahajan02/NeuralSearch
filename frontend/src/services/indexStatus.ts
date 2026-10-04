import API_BASE_URL from "./api";
import { getToken } from "./auth";

export async function getIndexJobs() {

    const response = await fetch(
        `${API_BASE_URL}/index/jobs`,
        {
            headers: {
                Authorization: `Bearer ${getToken()}`
            }
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Unable to fetch index jobs.");
    }

    return data;
}