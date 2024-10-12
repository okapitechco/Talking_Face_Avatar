import runpod
import os
from dotenv import load_dotenv
import torch
from main import main

# Load environment variables from .env file
load_dotenv()

# If your handler runs inference on a model, load the model here.
# You will want models to be loaded into memory before starting serverless.


def handler(job):
    """Handler function that will be used to process jobs."""
    job_input = job["input"]

    name = job_input.get("name", "World")
    job_type = job_input.get("job_type", None)

    if job_type == None:
        return {"error": "You need to specify job_type"}

    # generate pre-signed URL
    if job_type == "generate-video-with-image-and-audio":
        image_file_url = job_input.get("image_file_url", None)
        audio_file_url = job_input.get("audio_file_url", None)

        # Update device based on cpu argument if device is not provided
        device = "cuda" if torch.cuda.is_available() else "cpu"

        main(
            driven_audio_url=audio_file_url,  # path to driven audio
            source_image_url=image_file_url,  # path to source image
            ref_eyeblink=None,  # path to reference video providing eye blinking
            ref_pose=None,  # path to reference video providing pose
            checkpoint_dir="./checkpoints",  # path to output
            result_dir="./results",  # path to output
            pose_style=0,  # input pose style from [0, 46)
            batch_size=2,  # the batch size of facerender
            expression_scale=1.0,  # scale factor for facial expressions
            input_yaw=None,  # the input yaw degree of the user
            input_pitch=None,  # the input pitch degree of the user
            input_roll=None,  # the input roll degree of the user
            enhancer="gfpgan",  # Face enhancer, [gfpgan, RestoreFormer]
            background_enhancer="realesrgan",  # background enhancer, [realesrgan]
            cpu=False,  # use CPU instead of GPU
            face3dvis=False,  # generate 3d face and 3d landmarks
            still=False,  # can crop back to the original videos for the full body animation
            preprocess="crop",  # how to preprocess the images: crop, resize, or full
            net_recon="resnet50",  # net structure for reconstruction (useless)
            init_path=None,  # initialization path (useless)
            use_last_fc=False,  # zero initialize the last fc
            bfm_folder="./checkpoints/BFM_Fitting/",  # path to BFM fitting folder
            bfm_model="BFM_model_front.mat",  # bfm model filename
            focal=1015.0,  # focal length for renderer
            center=112.0,  # center point for renderer
            camera_d=10.0,  # camera distance for renderer
            z_near=5.0,  # near clipping plane for renderer
            z_far=15.0,  # far clipping plane for renderer
            device=device,  # device to use (cpu or cuda)
        )

    elif job_type == "test_job":
        return {"status": "handler is fine!"}
    else:
        return {
            "error": "job_type should be one of 'generate-video-with-image-and-audio' , 'test_jo'"
        }


runpod.serverless.start({"handler": handler})
