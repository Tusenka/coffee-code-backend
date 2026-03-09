import pytest
import pytz

from db.constants import GoalName
from db.user_helper_repository import UserHelperRepository


class TestUserHelperRepo:
    @pytest.mark.parametrize(
        "goal_name",
        [GoalName.MENTOR_GOAL, GoalName.MENTEE_GOAL, GoalName.EXPERIENCE_EXCHANGE],
    )
    def test_get_goal_by_name(
        self, user_helper_repo: UserHelperRepository, goal_name: GoalName
    ):
        assert user_helper_repo.get_goal_by_name(goal_name=goal_name).id

    def test_correct_timezones_data(self, user_helper_repo: UserHelperRepository):
        # assert correctness for all timezones in the repo
        assert all([pytz.timezone(t.ian) for t in user_helper_repo.list_timezones()])
