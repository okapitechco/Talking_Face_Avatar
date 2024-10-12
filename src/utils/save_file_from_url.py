import urllib.request


def save_file_from_url(input_file_url, input_file_local_name):
    # Extract the original file extension from the URL
    original_filename = input_file_url.split("/")[-1]
    original_file_extension = original_filename.split(".")[-1]
    input_local_file_path = f"{input_file_local_name}.{original_file_extension}"
    try:
        urllib.request.urlretrieve(input_file_url, input_local_file_path)
        print(
            f"File downloaded from {input_file_url} and saved to {input_local_file_path}."
        )
    except Exception as e:
        print(f"An error occurred: {e}")
    return input_local_file_path
