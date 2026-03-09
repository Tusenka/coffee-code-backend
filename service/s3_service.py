import logging
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ENDPOINT = "https://storage.yandexcloud.net"
logger = logging.getLogger(__name__)


class S3Service:
    bucket_name = "coffee-and-code"

    def __init__(self):
        session = boto3.Session(
            aws_access_key_id=(os.environ["S3_KEY_ID"]),
            aws_secret_access_key=(os.environ["S3_SECRET_ID"]),
            region_name="ru-central1",
        )

        self.s3 = session.client(
            "s3", endpoint_url=ENDPOINT, config=Config(signature_version="s3v4")
        )

    def upload_file(self, file_path: str, key: str):
        self.s3.upload_file(file_path, self.bucket_name, key)

    def create_presigned_url(self, key, expiration=3600 * 24):
        try:
            response = self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logging.exception(e)
            return None

        return response
