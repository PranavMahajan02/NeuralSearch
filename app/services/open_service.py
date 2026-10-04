from app.platforms.registry import platform_manager


def open_result(request):

    platform_name = request.platform

    if platform_name == "local_storage":
        platform_name = "local"

    platform = platform_manager.get(platform_name)

    if platform is None:

        return {
            "status": "error",
            "message": "Platform not found."
        }

    return platform.open(
        request.path,
        request.file_id
    )