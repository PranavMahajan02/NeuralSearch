from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from app.scheduler.cancel import cancel_job

from app.models.auth_models import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse
)

from app.auth.auth_service import (
    register_user,
    login_user
)

from app.auth.auth_dependency import (
    get_current_user
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse
)
def register(
    request: RegisterRequest
):

    try:

        return register_user(
            request.name,
            request.email,
            request.password
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    request: LoginRequest
):

    try:

        return login_user(
            request.email,
            request.password
        )

    except ValueError as e:

        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


@router.get(
    "/profile",
    response_model=UserResponse
)
def profile(

    current_user = Depends(
        get_current_user
    )

):

    return {

        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"]

    }

@router.post("/logout")
def logout(

    current_user=Depends(get_current_user)

):

    cancel_job(

        current_user["id"]

    )

    return {

        "status": "success"

    }