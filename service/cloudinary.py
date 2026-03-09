import os
from http import HTTPStatus

import cloudinary
from cloudinary.uploader import upload
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile

import logging

logger = logging.getLogger(__name__)


class CloudinaryService:
    def __init__(self):
        load_dotenv()
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        )

    @staticmethod
    def upload_image(image: UploadFile):
        logger.debug("Выгрузка изображения %s на сервер Cloudinary...", image.filename)
        try:
            upload_result = upload(image.file)
            file_url: str = upload_result["secure_url"]
            logger.info(
                "Изображение %s выгружено на сервер Cloudinary.", image.filename
            )
            return file_url
        except Exception as e:
            logger.exception(
                "Не удалось выгрузить изображение %s на сервер Cloudinary.\n%s",
                image.filename,
                e,
            )
            raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
