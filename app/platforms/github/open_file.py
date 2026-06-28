import webbrowser


def open_github_file(owner, repo, path):

    url = (
        f"https://github.com/"
        f"{owner}/{repo}/blob/main/{path}"
    )

    webbrowser.open(url)

    return url