# 随机文件夹图片批量（ComfyUI 自定义节点）

把本目录复制到 ComfyUI 的 `custom_nodes` 目录后重启 ComfyUI，在节点菜单中选择：

`image/batch → 随机文件夹图片批量（独立图生图）`

节点会从指定文件夹随机抽取图片（默认 10 张），输出一个 `IMAGE` batch。batch 中的每个项目仍是一张独立图片；将 `images` 接到支持 batch 的图生图流程（例如 VAE Encode → KSampler）即可同时处理十张图片。不同尺寸图片会保持比例缩放并用黑边补齐到统一尺寸。

输入说明：

- `folder_path`：图片文件夹的绝对路径。
- `image_count`：抽取数量；如果文件不足则抽取现有全部图片。
- `seed`：相同文件夹内容和 seed 会得到相同抽样结果。
- `recursive`：是否包含子文件夹。
- `output_width` / `output_height`：可选统一输出尺寸；填 0 时自动使用本次图片中的最大宽高。

第三个输出 `selected_files` 是本次抽中的文件路径列表，便于记录或调试。
