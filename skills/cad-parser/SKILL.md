---
name: cad-parser
description: >
  解析 DWG/DXF CAD 图纸文件，提取几何实体、尺寸标注、文本注释、
  图层信息，输出结构化的 CADDocument。
tools:
  - parse_cad_file
---

# CAD 图纸解析

## 能力
解析工业 CAD 图纸（DWG/DXF 格式），提取所有可查询的技术信息。

## 输入
- 文件路径（.dwg 或 .dxf）

## 输出
- CADDocument：包含 dimensions、text_annotations、entities、layers

## 处理流程
1. DWG 文件 → LibreDWG dwg2dxf 转换为 DXF
2. DXF 文件 → ezdxf 解析为 CADDocument
3. 提取 14 种几何实体 + 7 种标注类型
4. 提取 TEXT/MTEXT 文本注释（GBK 编码）
5. 记录图层归属信息

## 支持的实体类型
- LINE, CIRCLE, ARC, LWPOLYLINE, POLYLINE, SPLINE, ELLIPSE
- TEXT, MTEXT, INSERT, DIMENSION, HATCH, POINT, LEADER

## 支持的标注类型
- 线性标注 (linear)、对齐标注 (aligned)、直径标注 (diameter)
- 半径标注 (radius)、角度标注 (angular)、坐标标注 (ordinate)

## 注意事项
- DWG 转换依赖外部命令 `dwg2dxf`（需预装 LibreDWG）
- DXF 内部编码为 GBK，转换时注意字符集处理
- 大文件（>10MB）可能需要 5-10 秒解析时间
