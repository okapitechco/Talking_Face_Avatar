from botocore.client import Config
import boto3


class s3utils:
    def __init__(self, args):
        self.aws_access_key_id = args["aws_access_key_id"]
        self.aws_secret_access_key = args["aws_secret_access_key"]
        self.aws_endpoint_url = args["aws_endpoint_url"]
        self.aws_bucket_name = args["aws_bucket_name"]
        self.aws_bucket_location = args["aws_bucket_location"]
        self.connect_timeout = args["connect_timeout"]
        self.connect_attempts = args["connect_attempts"]
        self.config = Config(
            connect_timeout=self.connect_timeout,
            retries=dict(max_attempts=self.connect_attempts),
            signature_version="v4",
        )
        self.session = boto3.session.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    def get_client(self):
        return self.session.client(
            service_name="s3", endpoint_url=self.aws_endpoint_url, config=self.config
        )

    def file_upload(self, filepath, key):
        client = self.get_client()
        try:
            client.upload_file(filepath, self.aws_bucket_name, key)

            url = "https://%s.s3.amazonaws.com/%s/%s" % (
                self.aws_bucket_name,
                self.aws_bucket_name,
                key,
            )

        except Exception as e:
            print(e)
            return ""

        return url

    # def file_download(self, s3_file_path, local_file_path):
    #     client = self.get_client()

    #     try:
    #         with open(local_file_path, "wb") as f:
    #             client.download_file(self.aws_bucket_name, s3_file_path, f)
    #     except Exception as e:
    #         print("Error occured while downloading the file ", e)
