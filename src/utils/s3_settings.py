import os


def get_s3_settings():
    settings = {}
    settings["aws_access_key_id"] = os.environ.get("AWS_ACCESS_KEY_ID")
    settings["aws_secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY")
    settings["aws_endpoint_url"] = os.environ.get("AWS_ENDPOINT_URL")
    settings["aws_bucket_name"] = os.environ.get("AWS_BUCKET_NAME")
    settings["aws_bucket_location"] = os.environ.get("AWS_BUCKET_LOCATION")
    settings["connect_timeout"] = 5
    settings["connect_attempts"] = 1
    return settings
