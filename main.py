import torch
from time import strftime
import os, sys, time
from argparse import ArgumentParser
from dotenv import load_dotenv
from datetime import datetime


from src.utils.preprocess import CropAndExtract
from src.test_audio2coeff import Audio2Coeff
from src.facerender.animate import AnimateFromCoeff
from src.generate_batch import get_data
from src.generate_facerender_batch import get_facerender_data
from src.utils.save_file_from_url import save_file_from_url
from src.utils.s3_settings import get_s3_settings
from src.utils.s3_utils import s3utils

# Load environment variables from .env file
load_dotenv()


def main(
    driven_audio_url="./examples/driven_audio/bus_chinese.wav",  # path to driven audio
    source_image_url="./examples/source_image/full_body_2.png",  # path to source image
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
    enhancer=None,  # Face enhancer, [gfpgan, RestoreFormer]
    background_enhancer=None,  # background enhancer, [realesrgan]
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
    device=None,  # device to use (cpu or cuda)
):
    # torch.backends.cudnn.enabled = False
    s3utils_instance = s3utils(get_s3_settings())

    input_audio_file_path = save_file_from_url(
        **{
            "input_file_url": driven_audio_url,
            "input_file_local_name": "input_audio_file",
        }
    )
    input_image_file_path = save_file_from_url(
        **{
            "input_file_url": source_image_url,
            "input_file_local_name": "input_image_file",
        }
    )

    pic_path = input_image_file_path
    audio_path = input_audio_file_path
    save_dir = os.path.join(result_dir, strftime("%Y_%m_%d_%H.%M.%S"))
    os.makedirs(save_dir, exist_ok=True)
    pose_style = pose_style
    device = device
    batch_size = batch_size
    input_yaw_list = input_yaw
    input_pitch_list = input_pitch
    input_roll_list = input_roll
    ref_eyeblink = ref_eyeblink
    ref_pose = ref_pose

    current_code_path = sys.argv[0]
    current_root_path = os.path.split(current_code_path)[0]

    os.environ["TORCH_HOME"] = os.path.join(current_root_path, checkpoint_dir)

    path_of_lm_croper = os.path.join(
        current_root_path, checkpoint_dir, "shape_predictor_68_face_landmarks.dat"
    )
    path_of_net_recon_model = os.path.join(
        current_root_path, checkpoint_dir, "epoch_20.pth"
    )
    dir_of_BFM_fitting = os.path.join(current_root_path, checkpoint_dir, "BFM_Fitting")
    wav2lip_checkpoint = os.path.join(current_root_path, checkpoint_dir, "wav2lip.pth")

    audio2pose_checkpoint = os.path.join(
        current_root_path, checkpoint_dir, "auido2pose_00140-model.pth"
    )
    audio2pose_yaml_path = os.path.join(
        current_root_path, "src", "config", "auido2pose.yaml"
    )

    audio2exp_checkpoint = os.path.join(
        current_root_path, checkpoint_dir, "auido2exp_00300-model.pth"
    )
    audio2exp_yaml_path = os.path.join(
        current_root_path, "src", "config", "auido2exp.yaml"
    )

    free_view_checkpoint = os.path.join(
        current_root_path, checkpoint_dir, "facevid2vid_00189-model.pth.tar"
    )

    if preprocess == "full":
        mapping_checkpoint = os.path.join(
            current_root_path, checkpoint_dir, "mapping_00109-model.pth.tar"
        )
        facerender_yaml_path = os.path.join(
            current_root_path, "src", "config", "facerender_still.yaml"
        )
    else:
        mapping_checkpoint = os.path.join(
            current_root_path, checkpoint_dir, "mapping_00229-model.pth.tar"
        )
        facerender_yaml_path = os.path.join(
            current_root_path, "src", "config", "facerender.yaml"
        )

    # init model
    print(path_of_net_recon_model)
    preprocess_model = CropAndExtract(
        path_of_lm_croper, path_of_net_recon_model, dir_of_BFM_fitting, device
    )

    print(audio2pose_checkpoint)
    print(audio2exp_checkpoint)
    audio_to_coeff = Audio2Coeff(
        audio2pose_checkpoint,
        audio2pose_yaml_path,
        audio2exp_checkpoint,
        audio2exp_yaml_path,
        wav2lip_checkpoint,
        device,
    )

    print(free_view_checkpoint)
    print(mapping_checkpoint)
    animate_from_coeff = AnimateFromCoeff(
        free_view_checkpoint, mapping_checkpoint, facerender_yaml_path, device
    )

    # crop image and extract 3dmm from image
    first_frame_dir = os.path.join(save_dir, "first_frame_dir")
    os.makedirs(first_frame_dir, exist_ok=True)
    print("3DMM Extraction for source image")
    first_coeff_path, crop_pic_path, crop_info = preprocess_model.generate(
        pic_path, first_frame_dir, preprocess, source_image_flag=True
    )
    if first_coeff_path is None:
        print("Can't get the coeffs of the input")
        return

    if ref_eyeblink is not None:
        ref_eyeblink_videoname = os.path.splitext(os.path.split(ref_eyeblink)[-1])[0]
        ref_eyeblink_frame_dir = os.path.join(save_dir, ref_eyeblink_videoname)
        os.makedirs(ref_eyeblink_frame_dir, exist_ok=True)
        print("3DMM Extraction for the reference video providing eye blinking")
        ref_eyeblink_coeff_path, _, _ = preprocess_model.generate(
            ref_eyeblink, ref_eyeblink_frame_dir
        )
    else:
        ref_eyeblink_coeff_path = None

    if ref_pose is not None:
        if ref_pose == ref_eyeblink:
            ref_pose_coeff_path = ref_eyeblink_coeff_path
        else:
            ref_pose_videoname = os.path.splitext(os.path.split(ref_pose)[-1])[0]
            ref_pose_frame_dir = os.path.join(save_dir, ref_pose_videoname)
            os.makedirs(ref_pose_frame_dir, exist_ok=True)
            print("3DMM Extraction for the reference video providing pose")
            ref_pose_coeff_path, _, _ = preprocess_model.generate(
                ref_pose, ref_pose_frame_dir
            )
    else:
        ref_pose_coeff_path = None

    # audio2ceoff
    batch = get_data(
        first_coeff_path, audio_path, device, ref_eyeblink_coeff_path, still=still
    )
    coeff_path = audio_to_coeff.generate(
        batch, save_dir, pose_style, ref_pose_coeff_path
    )

    """
    # 3dface render
    if face3dvis:
        from src.face3d.visualize import gen_composed_video

        gen_composed_video(
            args,
            device,
            first_coeff_path,
            coeff_path,
            audio_path,
            os.path.join(save_dir, "3dface.mp4"),
        )
    """

    # coeff2video
    data = get_facerender_data(
        coeff_path,
        crop_pic_path,
        first_coeff_path,
        audio_path,
        batch_size,
        input_yaw_list,
        input_pitch_list,
        input_roll_list,
        expression_scale=expression_scale,
        still_mode=still,
        preprocess=preprocess,
    )

    return_path = animate_from_coeff.generate(
        data,
        save_dir,
        pic_path,
        crop_info,
        enhancer=enhancer,
        background_enhancer=background_enhancer,
        preprocess=preprocess,
    )

    absolute_path = os.path.abspath(return_path)

    # Get the current date and time
    current_time = datetime.now()

    # Format the date to be human-readable (e.g., YYYY_MM_DD_HH_MM_SS)
    formatted_time = current_time.strftime("%Y_%m_%d_%H_%M_%S")

    # Use it in the filename
    filename = f"ai_talking_avatars/{formatted_time}.mp4"

    public_video_url = s3utils_instance.file_upload(
        absolute_path,
        filename,
    )

    return f"https://saas-blogs-bucket.s3.amazonaws.com/{filename}"


# Update device based on cpu argument if device is not provided
device = "cuda" if torch.cuda.is_available() else "cpu"

main(
    driven_audio_url="./examples/driven_audio/bus_chinese.wav",  # path to driven audio
    source_image_url="./examples/source_image/full_body_2.png",  # path to source image
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
