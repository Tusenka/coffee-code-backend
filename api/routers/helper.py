from fastapi import APIRouter

from api.constants import SWAGGER_GOALS_EXAMPLE, SWAGGER_SKILLS_EXAMPLE
from api.routers.common import catalog_service
from service.model import TimezoneList, GoalList, SkillList

app = APIRouter(prefix="/api/v1")


@app.get(
    "/skills",
    response_model=SkillList,
    responses={200: SWAGGER_SKILLS_EXAMPLE},
)
async def list_skills():
    return catalog_service.list_skills()


@app.get(
    "/timezones",
    response_model=TimezoneList,
    responses={200: SWAGGER_SKILLS_EXAMPLE},
)
async def list_timezones():
    return catalog_service.list_timezones()


@app.get(
    "/goals",
    response_model=GoalList,
    responses={200: SWAGGER_GOALS_EXAMPLE},
)
async def list_goals():
    return catalog_service.list_goals()
