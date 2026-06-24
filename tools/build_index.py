#!/usr/bin/env python3
"""构建 CAD 参数索引

用法:
    python tools/build_index.py --input data/cad/filter_modify.dxf --output data/index/parameters.json
"""
import argparse
import logging
import os

from cad_parser import CADParser
from cad_understanding.component_recognizer import ComponentRecognizer
from cad_understanding.parameter_index import ParameterIndex
from cad_understanding.scale_inferencer import ScaleInferencer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="构建 CAD 参数索引")
    parser.add_argument("--input", "-i", required=True, help="CAD 文件路径 (.dxf)")
    parser.add_argument("--output", "-o", default="data/index/parameters.json", help="输出索引文件路径")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        raise FileNotFoundError(f"文件不存在: {args.input}")

    logger.info("解析 CAD 文件: %s", args.input)
    cad_parser = CADParser(args.input)
    doc = cad_parser.parse()

    logger.info(
        "解析结果: %d 实体, %d 尺寸标注, %d 文本, %d 图层",
        len(doc.entities), len(doc.dimensions), len(doc.text_annotations), len(doc.layers),
    )

    unit = ScaleInferencer().infer(doc)
    logger.info("推断单位: %s", unit)

    components = ComponentRecognizer().recognize(doc)
    logger.info("识别部件: %d", len(components))

    idx = ParameterIndex()
    index_data = idx.build(doc)
    index_data.components = components

    idx.save(args.output)
    logger.info("索引已保存到: %s", args.output)
    logger.info("参数数量: %d", len(index_data.parameters))

    for p in index_data.parameters[:10]:
        logger.info("  %s = %s %s (aliases: %s)", p.name, p.value, p.unit, p.aliases)


if __name__ == "__main__":
    main()
