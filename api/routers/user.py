from __future__ import annotations

import datetime
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, UploadFile
from starlette.responses import JSONResponse

from api.constants import (
    SWAGGER_OK_EXAMPLE,
    SWAGGER_UNAUTHORIZED_EXAMPLE,
    SWAGGER_USER_PROFILE_EXAMPLE,
)
from api.exceptions import Unauthorized
from api.routers.common import user_repo, user_service
from db.model import User
from api.schemas import UserUpdate, ContactUpdate
from service.model import (
    UserProfile,
)
from service.timequant_service import UserInterval, TimeQuantService
from utils.auth.schemes import JWTUser, UserTelegram
from utils.auth.token import generate_jwt_token, get_auth_user_data
from utils.auth.validator import validate_telegram_user

app = APIRouter(prefix="/api/v1")

logger = logging.getLogger(__name__)


async def get_auth_user(request: Request) -> User:
    if not request.cookies.get("Authorization"):
        logger.error(
            "Пользователь %s не выполнил вход, так как куки авторизации отсутствуют в запросе.",
            request.body,
        )
        raise Unauthorized()
    jwt_user = get_auth_user_data(token=request.cookies.get("Authorization"))

    return user_repo.get_user_by_id(user_id=jwt_user["id"])


@app.post(
    "/login",
    response_model=UserProfile,
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE},
)
async def login(telegram_user: UserTelegram):
    validate_telegram_user(data=telegram_user)
    user = user_service.save_or_get_user_from_telegram(telegram_user=telegram_user)

    jwt_user = JWTUser(id=str(user.id))

    token = generate_jwt_token(user=jwt_user)

    response = JSONResponse(
        UserProfile.from_dao(
            user=user,
            to_user_intervals_with_offset=TimeQuantService.to_user_intervals_with_offset,
        ).model_dump_json(
            by_alias=True
            # exclude_none=True, exclude_unset=True, exclude_computed_fields=True
        ),
        status_code=200,
    )
    response.set_cookie(
        key="Authorization",
        value=token,
        expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=3),
    )
    logger.info("Куки выданы пользователю %r.", user)

    return response


@app.get(
    "/profile",
    response_model=UserProfile,
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def get_user_data(user: User = Depends(get_auth_user)):
    profile = user_service.get_user_profile(user_id=user.id)

    response = JSONResponse(
        profile.model_dump_json(
            by_alias=True
            # exclude_none=True, exclude_unset=True, exclude_computed_fields=True
        ),
        status_code=200,
    )
    return response


@app.patch(
    "/profile",
    response_model=dict,
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def update_user_data(
    user_data: UserUpdate, auth_user: User = Depends(get_auth_user)
):
    user_service.update_user_data(user_data=user_data, user_id=auth_user.id)
    response = JSONResponse(
        {"message": f"Личная информация пользователя {auth_user} изменена."},
        status_code=200,
    )

    return response


@app.patch(
    "/contacts",
    response_model=dict,
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def update_user_contact(
    contact_data: list[ContactUpdate], auth_user: User = Depends(get_auth_user)
):
    user_service.update_contacts(contact_data=contact_data, user_id=auth_user.id)
    response = JSONResponse(
        {"message": f"Контакты пользователя {auth_user} изменены."}, status_code=200
    )

    return response


@app.patch(
    "/contact/{contact_name}",
    response_model=dict,
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def update_user_contact(
    contact_name: str, auth_user: User = Depends(get_auth_user)
):
    user_service.delete_contact(contact_name=contact_name, user_id=auth_user.id)
    response = JSONResponse(
        {"message": f"Данные пользователя {auth_user} удалены."}, status_code=200
    )

    return response


@app.post(
    "/user_photo",
    response_model=dict,
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def update_user_photo(
    photo_type: str, photo: UploadFile, auth_user: User = Depends(get_auth_user)
):
    user_service.update_user_photo(
        photo_type=photo_type, photo=photo, user_id=auth_user.id
    )
    response = JSONResponse(
        {"message": f"Фотография пользователя {auth_user} изменена."}, status_code=200
    )

    return response


@app.post(
    "/skills",
    response_model=dict,
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def update_user_skills(
    skills: list[UUID], auth_user: User = Depends(get_auth_user)
):
    user_service.update_user_skills(skills=skills, user_id=auth_user.id)
    response = JSONResponse(
        {"message": f"Навыки пользователя {auth_user} изменены."}, status_code=200
    )

    return response


@app.post(
    "/skills_can_teach",
    response_model=dict,
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def update_user_mentor_skills(
    skills: list[UUID], auth_user: User = Depends(get_auth_user)
):
    user_service.update_user_mentor_skills(skills=skills, user_id=auth_user.id)
    response = JSONResponse(
        {"message": f"Компетенции обучающего у пользователя {auth_user} изменены."},
        status_code=200,
    )

    return response


@app.post(
    "/skills_want_learn",
    response_model=dict,
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def update_user_mentee_skills(
    skills: list[UUID], auth_user: User = Depends(get_auth_user)
):
    user_service.update_user_mentee_skills(skills=skills, user_id=auth_user.id)
    response = JSONResponse(
        {"message": f"Компетенции обучаемого у пользователя {auth_user} изменены."},
        status_code=200,
    )

    return response


@app.post(
    "/goals",
    response_model=dict,
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def update_user_goals(
    goals: list[UUID], auth_user: User = Depends(get_auth_user)
):
    user_service.update_user_goals(goals=goals, user_id=auth_user.id)
    response = JSONResponse(
        {"message": f"Цели пользователя {auth_user} изменены."}, status_code=200
    )

    return response


@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="Authorization")
    response.status_code = 200

    return {"status": f"Пользователь {response.body} выполнил выход."}


@app.post(
    "/user_intervals",
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def update_intervals(
    intervals: list[UserInterval], auth_user: User = Depends(get_auth_user)
):
    user_service.update_user_quants(intervals=intervals, user_id=auth_user.id)
    response = JSONResponse(
        {"message": f"Календарь пользователя {auth_user} изменён."}, status_code=200
    )

    return response
