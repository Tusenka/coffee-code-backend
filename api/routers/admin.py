import datetime
from uuid import UUID

from fastapi import APIRouter
from fastapi.params import Depends
from starlette.responses import JSONResponse

from api.constants import SWAGGER_OK_EXAMPLE
from api.routers.common import catalog_service, recommendation_service, user_service
from api.schemas import (
    CreateAdminMeetSchema,
    CreateAdminMeetScoreSchema,
    TransferAdminMeetSchema,
)
from utils.auth.schemes import JWTUser
from utils.auth.token import generate_jwt_token


async def check_admin_token(auth_token: str):
    assert check_admin_token(auth_token)


app = APIRouter(prefix="/api/v1/admin", dependencies=[Depends(check_admin_token)])


@app.patch(
    "/reload_cities",
    responses={200: SWAGGER_OK_EXAMPLE},
)
async def reload_cities():
    catalog_service.populate_cities()

    response = JSONResponse(
        {"message": "Информация о городах обновлена."}, status_code=200
    )

    return response


@app.patch(
    "/reload_skills",
    responses={200: SWAGGER_OK_EXAMPLE},
)
async def reload_tags():
    catalog_service.populate_tags()
    catalog_service.populate_goals()

    response = JSONResponse(
        {"message": "Категории для целей и компетенций обновлены."}, status_code=200
    )

    return response


@app.patch(
    "/reset_db",
    responses={200: SWAGGER_OK_EXAMPLE},
)
async def reset_tags():
    catalog_service.reset_tags()

    response = JSONResponse(
        {"message": "Категории для целей и компетенций были удалены."}, status_code=200
    )

    return response


@app.post(
    "/meet",
    responses={200: SWAGGER_OK_EXAMPLE},
)
async def create_meet(meet: CreateAdminMeetSchema):
    match_id = recommendation_service.create_match(meet=meet)

    return JSONResponse(
        {"message": "Встреча создана", "match_id": str(match_id)}, status_code=200
    )


@app.post(
    "/meet_status",
    responses={200: SWAGGER_OK_EXAMPLE},
)
async def transfer_meet_status(transfer_meet: TransferAdminMeetSchema):
    match_id = recommendation_service.transfer_meet_status(transfer_meet=transfer_meet)

    return JSONResponse(
        {"message": "Встреча переведена", "match_id": str(match_id)}, status_code=200
    )


@app.post(
    "/review",
    responses={200: SWAGGER_OK_EXAMPLE},
)
async def create_meet_score(score: CreateAdminMeetScoreSchema):
    recommendation_service.add_review(score=score, user_id=score.user_id)

    return JSONResponse({"message": "Ревью на встречу отправлено"}, status_code=200)


@app.post(
    "/login",
    responses={200: SWAGGER_OK_EXAMPLE},
)
async def login_as_an_user(user_id: UUID):
    jwt_user = JWTUser(id=str(user_id))
    token = generate_jwt_token(user=jwt_user)
    response = JSONResponse(
        {"message": f"Пользователь {user_id} выполнил вход как администратор."},
        status_code=200,
    )

    response.set_cookie(
        key="Authorization",
        value=token,
        expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=3),
    )

    return response


@app.get("/list_users", responses={200: SWAGGER_OK_EXAMPLE}, response_model=list[UUID])
async def list_users():
    return user_service.list_users(limit=100)
