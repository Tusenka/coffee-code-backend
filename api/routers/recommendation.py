from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse

from api.constants import (
    SWAGGER_UNAUTHORIZED_EXAMPLE,
    SWAGGER_USER_PROFILE_EXAMPLE,
    SWAGGER_OK_EXAMPLE,
)
from api.exceptions import Unauthorized
from api.routers.common import user_repo, recommendation_service
from api.schemas import MeetScoreSchema
from db.model import User
from service.model import (
    UserProfileL1Access,
    UserProfileL1AccessList,
    UserProfileL2Access,
    MeetList,
    Match,
)
from utils.auth.token import get_auth_user_data

import logging

logger = logging.getLogger(__name__)

app = APIRouter(prefix="/api/v1")


async def get_auth_user(request: Request) -> User:
    if not request.cookies.get("Authorization"):
        logger.error(
            "Пользователь %s не выполнил вход, так как куки авторизации отсутствуют в запросе.",
            request.body,
        )
        raise Unauthorized()
    jwt_user = get_auth_user_data(token=request.cookies.get("Authorization"))

    return user_repo.get_user_by_id(user_id=jwt_user["id"])


@app.get(
    "/recommended_profiles",
    response_model=UserProfileL1AccessList,
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def list_recommended_profiles(auth_user: User = Depends(get_auth_user)):
    return recommendation_service.list_user_l1_recommended_profiles(
        user_id=auth_user.id
    )


@app.get(
    "/profile_preview/{target_user_id}",
    response_model=UserProfileL1Access,
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def get_l1_access_profile(
    target_user_id: UUID, auth_user: User = Depends(get_auth_user)
):
    return recommendation_service.get_user_l1_profile(
        target_user_id=target_user_id, initiator_user_id=auth_user.id
    )


@app.get(
    "/profile/{target_user_id}",
    response_model=UserProfileL2Access,
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def get_l2_access_profile(
    target_user_id: UUID, auth_user: User = Depends(get_auth_user)
):
    return recommendation_service.check_and_get_user_l2_profile(
        target_user_id=target_user_id, initiator_user_id=auth_user.id
    )


@app.get(
    "/profile/{target_user_id}",
    response_model=UserProfileL1Access,
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def get_l1_access_profile(
    target_user_id: UUID, auth_user: User = Depends(get_auth_user)
):
    return recommendation_service.get_user_l1_profile(
        target_user_id=target_user_id, initiator_user_id=auth_user.id
    )


@app.post(
    "/profile/{user_id}/send",
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def send_request_matched_profile(
    user_id: UUID, auth_user: User = Depends(get_auth_user)
):
    recommendation_service.send_match_request(
        initiator_user_id=auth_user.id, target_user_id=user_id
    )
    response = JSONResponse(
        {"message": f"{auth_user.id} отправил запрос на образование пары с {user_id}."},
        status_code=200,
    )
    return response


@app.post(
    "/profile/{user_id}/accept",
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def accept_matched_profile(
    user_id: UUID, auth_user: User = Depends(get_auth_user)
):
    recommendation_service.accept_match_request(
        initiator_user_id=auth_user.id, target_user_id=user_id
    )

    response = JSONResponse(
        {"message": f"{auth_user.id} принял запрос на образование пары с {user_id}."},
        status_code=200,
    )

    return response


@app.post(
    "/profile/{user_id}/reject",
    responses={200: SWAGGER_USER_PROFILE_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def reject_matched_profile(
    user_id: UUID, auth_user: User = Depends(get_auth_user)
):
    recommendation_service.reject_match_request(
        initiator_user_id=auth_user.id, target_user_id=user_id
    )

    response = JSONResponse(
        {"message": f"{auth_user.id} отклонил запрос на образование пары с {user_id}."},
        status_code=200,
    )

    return response


@app.get(
    "/meets",
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
    response_model=MeetList,
)
async def list_meet(auth_user: User = Depends(get_auth_user)):
    return recommendation_service.list_user_matches(user_id=auth_user.id)


@app.patch(
    "/review",
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def add_meet_review(
    score: MeetScoreSchema, auth_user: User = Depends(get_auth_user)
):
    recommendation_service.add_review(score=score, user_id=auth_user.id)

    response = JSONResponse(
        {"message": f"{auth_user.id} создал ревью."},
        status_code=200,
    )

    return response


@app.get(
    "/meet/{meet_id}",
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
    response_model=Match,
)
async def get_meet(meet_id: UUID, auth_user: User = Depends(get_auth_user)):
    return recommendation_service.get_user_match(match_id=meet_id, user_id=auth_user.id)


@app.delete(
    "/meet/{meet_id}",
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def cancel_meet(meet_id: UUID, auth_user: User = Depends(get_auth_user)):
    recommendation_service.cancel_match(match_id=meet_id)

    response = JSONResponse(
        {"message": f"{auth_user.id} отменил встречу {meet_id}."},
        status_code=200,
    )

    return response


@app.patch(
    "/meet/{meet_id}/complete",
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def complete_meet(meet_id: UUID, auth_user: User = Depends(get_auth_user)):
    recommendation_service.complete_match(match_id=meet_id)

    response = JSONResponse(
        {"message": f"{auth_user.id} завершил встречу {meet_id}."},
        status_code=200,
    )
    return response


@app.patch(
    "/meet/{meet_id}/skip",
    responses={200: SWAGGER_OK_EXAMPLE, 401: SWAGGER_UNAUTHORIZED_EXAMPLE},
)
async def skip_meet(meet_id: UUID, auth_user: User = Depends(get_auth_user)):
    recommendation_service.complete_match(match_id=meet_id)

    response = JSONResponse(
        {"message": f"{auth_user.id} пометил встречу как {meet_id} как пропущенную."},
        status_code=200,
    )

    return response
