from app.platforms.registry import platform_manager

platform = platform_manager.get("google_drive")

platform.index()