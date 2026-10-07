class PlatformPreconditionError(Exception):
    # Stored as the job's error_message without the exception class name:
    # these messages are written for the user ("reconnect ...").
    """The platform cannot run at all (not connected, auth failure, rate limit).

    Raised from anywhere inside a platform's index(): per-file error handling
    re-raises it, and the worker fails the whole job with this message.
    """
