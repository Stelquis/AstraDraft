#!/usr/bin/env python3
"""DWG → DXF 转换工具

用法:
    python tools/dwg_to_dxf.py --input path/to/file.dwg [--output path/to/output.dxf]
"""
import argparse
import logging
import os
import shutil
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def find_dwg2dxf() -> str:
    path = shutil.which("dwg2dxf")
    if path:
        return path
    print(
        "错误: 未找到 dwg2dxf 工具。\n"
        "安装方法:\n"
        "  git clone https://github.com/LibreDWG/libredwg.git\n"
        "  cd libredwg\n"
        "  apt-get install -y autoconf automake libtool texinfo\n"
        "  autoreconf -fi && ./configure --prefix=/usr/local && make -j$(nproc) && make install\n",
        file=sys.stderr,
    )
    sys.exit(1)


def convert(input_path: str, output_path: str | None = None) -> str:
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"文件不存在: {input_path}")

    if not input_path.lower().endswith(".dwg"):
        raise ValueError(f"输入文件必须是 .dwg 格式: {input_path}")

    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".dxf"

    dwg2dxf = find_dwg2dxf()

    logger.info("转换: %s -> %s", input_path, output_path)
    result = subprocess.run(
        [dwg2dxf, "-o", output_path, input_path],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"转换失败:\n{result.stderr}")

    if not os.path.isfile(output_path):
        raise RuntimeError(f"转换失败: 输出文件未生成 ({output_path})")

    logger.info("转换完成: %s (%.1f KB)", output_path, os.path.getsize(output_path) / 1024)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="DWG → DXF 转换工具")
    parser.add_argument("--input", "-i", required=True, help="输入的 DWG 文件路径")
    parser.add_argument("--output", "-o", help="输出的 DXF 文件路径（默认: 同名 .dxf）")
    args = parser.parse_args()

    convert(args.input, args.output)


if __name__ == "__main__":
    main()
