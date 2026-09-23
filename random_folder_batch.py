import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".jfif"}


def _find_images(folder: str, recursive: bool):
    root = Path(folder).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(f"图片文件夹不存在：{folder}")
    iterator = root.rglob("*") if recursive else root.glob("*")
    return sorted(
        (path for path in iterator if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: str(path).lower(),
    )


def _pil_to_tensor(image: Image.Image) -> torch.Tensor:
    # ComfyUI IMAGE convention: float32, RGB, [0, 1], HWC.
    array = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(array)


class RandomFolderImageBatch:
    """Randomly select images from a folder and emit them as one IMAGE batch."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "", "multiline": False}),
                "image_count": ("INT", {"default": 10, "min": 1, "max": 1024, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0x7FFFFFFF}),
                "recursive": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "output_width": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 8}),
                "output_height": ("INT", {"default": 0, "min": 0, "max": 16384, "step": 8}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("images", "masks", "selected_files")
    FUNCTION = "sample"
    CATEGORY = "image/batch"
    DESCRIPTION = "从文件夹随机抽取多张图片，以独立 IMAGE batch 项输出。"

    def sample(self, folder_path, image_count, seed, recursive=False, output_width=0, output_height=0):
        paths = _find_images(folder_path, recursive)
        if not paths:
            raise ValueError(f"文件夹中没有可读取的图片：{folder_path}")

        count = min(int(image_count), len(paths))
        rng = random.Random(int(seed))
        selected = rng.sample(paths, count)
        loaded = []
        for path in selected:
            with Image.open(path) as source:
                loaded.append(ImageOps.exif_transpose(source).convert("RGB"))

        target_width = int(output_width or max(image.width for image in loaded))
        target_height = int(output_height or max(image.height for image in loaded))
        # Auto dimensions are rounded up for clean VAE latent dimensions. An
        # explicitly supplied size is respected exactly.
        if not output_width:
            target_width = ((target_width + 7) // 8) * 8
        if not output_height:
            target_height = ((target_height + 7) // 8) * 8
        if target_width <= 0 or target_height <= 0:
            raise ValueError("输出尺寸必须大于 0")

        # A batch requires a common H/W. Preserve each image's aspect ratio and
        # pad with black, so images are still separate batch items.
        tensors = []
        for image in loaded:
            scale = min(target_width / image.width, target_height / image.height)
            resized_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
            resized = image.resize(resized_size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (target_width, target_height), (0, 0, 0))
            offset = ((target_width - resized.width) // 2, (target_height - resized.height) // 2)
            canvas.paste(resized, offset)
            tensors.append(_pil_to_tensor(canvas))

        images = torch.stack(tensors, dim=0)
        masks = torch.zeros((len(tensors), target_height, target_width), dtype=torch.float32)
        selected_files = "\n".join(str(path.resolve()) for path in selected)
        return (images, masks, selected_files)


NODE_CLASS_MAPPINGS = {"RandomFolderImageBatch": RandomFolderImageBatch}
NODE_DISPLAY_NAME_MAPPINGS = {"RandomFolderImageBatch": "随机文件夹图片批量（独立图生图）"}
