import json
import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api.routers import admin, helper, user, healthcheck, recommendation

import logging.config

app = FastAPI()
path = os.path.join(os.path.dirname(__file__), "../utils/logger/config.json")
with open(path) as config:
    logging.config.dictConfig(json.load(config))
    logging.getLogger().addFilter(
        lambda log_record: log_record.filename.startswith("db.")
    )
    logging.getLogger().addFilter(
        lambda log_record: log_record.filename.startswith("agent.")
    )
    logging.getLogger("uvicorn.access").addFilter(
        lambda log_record: log_record.getMessage().find("/health") == -1
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://pseudoanatomically-uneulogised-coraline.ngrok-free.dev",
        "https://coffee-code.ru",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(user.app)
app.include_router(helper.app)
app.include_router(admin.app)
app.include_router(healthcheck.app)

app.include_router(recommendation.app)
