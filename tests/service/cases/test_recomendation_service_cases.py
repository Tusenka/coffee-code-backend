import dataclasses

from db.constants import GoalName
from service.timequant_models import UserInterval


@dataclasses.dataclass
class MeetCriteriaCase:
    initiator_user_goals: list
    expected_common_goals: list
    target_user_goals: list


meet_cases = [
    MeetCriteriaCase(
        initiator_user_goals=[GoalName.MENTOR_GOAL],
        target_user_goals=[GoalName.MENTOR_GOAL],
        expected_common_goals=[],
    ),
    MeetCriteriaCase(
        initiator_user_goals=[GoalName.MENTEE_GOAL],
        target_user_goals=[GoalName.MENTOR_GOAL],
        expected_common_goals=[GoalName.MENTEE_GOAL],
    ),
    MeetCriteriaCase(
        initiator_user_goals=[GoalName.MENTOR_GOAL],
        target_user_goals=[GoalName.MENTEE_GOAL],
        expected_common_goals=[GoalName.MENTOR_GOAL],
    ),
    MeetCriteriaCase(
        initiator_user_goals=[GoalName.MENTOR_GOAL, GoalName.BRAINSTORM],
        target_user_goals=[GoalName.MENTEE_GOAL, GoalName.BRAINSTORM],
        expected_common_goals=[GoalName.MENTOR_GOAL, GoalName.BRAINSTORM],
    ),
    MeetCriteriaCase(
        initiator_user_goals=[
            GoalName.MENTOR_GOAL,
            GoalName.MENTEE_GOAL,
            GoalName.BRAINSTORM,
        ],
        target_user_goals=[
            GoalName.MENTEE_GOAL,
            GoalName.MENTOR_GOAL,
            GoalName.BRAINSTORM,
        ],
        expected_common_goals=[
            GoalName.MENTOR_GOAL,
            GoalName.BRAINSTORM,
            GoalName.MENTEE_GOAL,
        ],
    ),
]
