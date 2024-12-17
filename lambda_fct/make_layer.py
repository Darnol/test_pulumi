import os
import subprocess
from pathlib import Path
import shutil


def make_layer(output_name: str):
    """
    From the requirements.txt file crate a .zip layer that will be passed
    to the lambda function.
    """

    parent_directory: Path = Path(__file__).resolve().parent
    print(f"Using directory: {parent_directory}")
    os.chdir(parent_directory)

    # Create a temporary directory for the layer
    layer_dir = "tmp_layer_build"
    os.makedirs(layer_dir, exist_ok=True)

    # Install dependencies into the layer's tmp folder
    try:
        subprocess.run(
            ["pip", "install", "-r", "requirements.txt", "-t", f"{layer_dir}"],
            check=True,
        )
        # Zip the folder
        subprocess.run(["zip", "-r", output_name, f"{layer_dir}/"], check=True)
    except subprocess.CalledProcessError as e:
        print(e)
    finally:
        shutil.rmtree(layer_dir)
