import API_BASE_URL from "./api";

export async function searchFiles(
    query: string,
    platform: string = "all",
    searchType: string = "all"
) {

    const response = await fetch(
        `${API_BASE_URL}/search/`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                query,
                platform,
                search_type: searchType
            })
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.message || "Search failed."
        );
    }

    return data.results;
}