import os
import subprocess
from pathlib import Path
import shutil
import zipfile


def make_layer(output_name: str):
    """
    From the requirements.txt file crate a .zip layer that will be passed
    to the lambda function.
    Must be installed into the /python folder, aws lambda layer want it that way
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
            [
                "pip",
                "install",
                "-r",
                "requirements.txt",
                "-t",
                f"{layer_dir}/python",
                "--quiet",
            ],
            check=True,
        )

        # Zip the folder
        with zipfile.ZipFile(output_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(f"{layer_dir}/python"):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Add the file to the zip file, using a relative path
                    arcname = os.path.relpath(file_path, start=layer_dir)
                    zipf.write(file_path, arcname)

    finally:
        shutil.rmtree(layer_dir)
