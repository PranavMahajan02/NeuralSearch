from app.platforms.registry import platform_manager


def open_result(request):

    platform = platform_manager.get(
        request.platform
    )

    if platform is None:

        return {
            "status": "error",
            "message": "Platform not found."
        }

    return platform.open(
        request.path,
        request.file_id
    )