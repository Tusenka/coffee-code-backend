"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import os
import sqlalchemy as sa
${imports if imports else ""}
from alembic import context

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}
    if context.get_x_argument(as_dictionary=True).get('data', None):
        data_upgrades()

def data_upgrades():
    for file in os.listdir("db/data"):
        if file.endswith(".sql"):
            with open(f"db/data/{file}", "r") as f:
                op.execute(f.read())


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
