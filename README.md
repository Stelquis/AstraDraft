# 🤖 AstraDraft — CAD 智能问答 Agent

> 🎯 基于自然语言交互的 CAD 图纸参数智能问答系统
>
> 解析 DXF/DWG 图纸 → 构建语义索引 → 精准回答技术参数问题

---

## 📖 项目简介

AstraDraft 是一个面向工业 CAD 图纸的智能问答 Agent。它能够自动解析 DXF/DWG 格式的 CAD 图纸，提取几何实体、尺寸标注、文本注释等信息，构建带有语义别名的参数索引，并通过中文自然语言回答用户关于图纸中各类技术参数的提问。

对于复杂问题（如材料说明、用途解释、性能要求等），系统还会调用 **LLM 大语言模型** 进行增强回答，提供更具上下文理解的答案。

---

## 🏗️ 系统架构

```
                        🗣️ 用户自然语言问题
                              │
                              ▼
            ┌─────────────────────────────────────┐
            │    🧠 Agent 核心调度层 (agent/)       │
            │                                     │
            │  意图识别 → 参数解析 → 语义匹配       │
            │       → LLM 增强 → 答案生成           │
            └──────┬───────────────────┬──────────┘
                   │                   │
      ┌────────────▼────────┐  ┌──────▼──────────────────┐
      │  💬 NLP 交互模块      │  │  🔍 CAD 理解引擎          │
      │  (nlp_interface/)    │  │  (cad_understanding/)    │
      │                     │  │                          │
      │  · 意图分类           │  │  · 参数索引构建           │
      │  · 参数提取           │  │  · 语义别名映射           │
      │  · 查询处理           │  │  · 部件识别              │
      │  · 回答格式化          │  │  · 单位自动推断           │
      └─────────────────────┘  └──────────┬──────────────┘
                                          │
                              ┌───────────▼──────────────┐
                              │  ⚙️ CAD 解析模块           │
                              │  (cad_parser/)            │
                              │                          │
                              │  · DXF/DWG 文件读取        │
                              │  · 几何实体提取            │
                              │  · 尺寸标注解析            │
                              │  · 文本注释提取            │
                              │  · 图层管理               │
                              └──────────────────────────┘
```

---

## 📦 模块详解

### ⚙️ CAD 解析模块 — `cad_parser/`

负责读取 CAD 文件并提取图纸中的全部结构化信息。

| 子模块 | 文件 | 功能 |
|--------|------|------|
| 📂 文件读取 | `reader.py` | 支持 DXF 直接读取和 DWG → DXF 自动转换（通过 LibreDWG `dwg2dxf`） |
| 📐 实体提取 | `entities.py` | 提取 LINE、CIRCLE、ARC、LWPOLYLINE、SPLINE、ELLIPSE、INSERT 等 14 种几何实体，包含坐标与包围盒 |
| 📏 标注解析 | `dimensions.py` | 解析线性标注、对齐标注、角度、直径、半径、坐标等 7 种尺寸类型 |
| 📝 文本提取 | `text_extractor.py` | 提取 TEXT 和 MTEXT 文本注释，记录位置、高度、旋转角度 |
| 🎨 图层管理 | `layer_manager.py` | 解析图层信息（颜色、线型、可见性） |
| 📊 数据模型 | `models.py` | 基于 Pydantic 的结构化数据模型：`CADDocument`、`Entity`、`Dimension`、`TextAnnotation`、`LayerInfo`、`BlockDef` |

### 🔍 CAD 理解引擎 — `cad_understanding/`

将底层解析结果转化为具有语义含义的参数索引。

| 子模块 | 文件 | 功能 |
|--------|------|------|
| 🗂️ 参数索引 | `parameter_index.py` | 从尺寸标注和文本注释中构建参数索引；自动推断参数名称（通过附近文本关联）；识别材质、色调、成形方法、部品信息、使用温度、性能指标等非数值参数 |
| 🧩 语义映射 | `semantic_mapper.py` | 基于 jieba 分词 + 同义词表的模糊匹配；支持中英文别名（如"高度"↔"高"↔"H"↔"height"↔"总高"）；加权评分机制实现最佳参数匹配 |
| 🔎 部件识别 | `component_recognizer.py` | 按图层分组识别部件，计算各部件的包围盒 |
| 📐 单位推断 | `scale_inferencer.py` | 根据 DXF 头部 `$INSUNITS` 和 `$MEASUREMENT` 自动推断图纸单位（mm/cm/m/inches 等） |
| 📊 数据模型 | `models.py` | `Parameter`（参数）、`Component`（部件）、`ParameterIndexData`（索引数据） |

### 💬 NLP 交互模块 — `nlp_interface/`

处理用户的自然语言输入，将问题转化为精确的参数查询。

| 子模块 | 文件 | 功能 |
|--------|------|------|
| 🎯 意图分类 | `intent_classifier.py` | 基于正则模式识别 4 类意图：单参数查询、多参数查询、参数比较、信息查询 |
| 🔧 参数解析 | `parameter_parser.py` | jieba 分词 + 关键词匹配 + TF-IDF 关键词提取，精准定位用户想查询的目标参数 |
| 🔄 查询处理 | `query_processor.py` | 查询处理流水线，按优先级依次处理：极值查询（最大/最小）、计数查询（几处）、数值搜索、多参数列表、参数比较、常规参数匹配 |
| 📋 回答格式化 | `response_formatter.py` | 统一格式化输出：单参数、多参数列表、参数比较（含差值计算）、未匹配提示（附可用参数列表） |
| 📄 提示模板 | `prompt_templates.py` | LLM 系统提示词与回答模板定义 |

### 🧠 Agent 调度层 — `agent/`

系统的核心调度中枢，串联各模块并管理交互流程。

| 子模块 | 文件 | 功能 |
|--------|------|------|
| 🎛️ 核心调度 | `core.py` | `Agent` 主类：加载 CAD → 构建索引 → 处理问答；智能判断何时调用 LLM 增强（fallback 回答或复杂问题） |
| 💾 会话管理 | `session.py` | 多轮对话历史记录管理，支持上下文回溯 |
| ⚙️ 配置管理 | `config.py` | Agent 运行配置（CAD 文件路径、LLM API 参数、日志级别等） |
| 🖥️ CLI 入口 | `cli.py` | 命令行交互界面，支持交互模式和批量查询模式 |
| ⚠️ 异常处理 | `exceptions.py` | 自定义异常定义 |

### 🛠️ 工具脚本 — `tools/`

| 工具 | 文件 | 功能 |
|------|------|------|
| 🔄 格式转换 | `dwg_to_dxf.py` | DWG → DXF 批量转换 |
| 🗂️ 索引构建 | `build_index.py` | 独立构建参数索引并保存为 JSON |
| 📊 准确率评估 | `evaluate.py` | 批量评估问答准确率（支持预期答案对比，数值容差 0.1） |

---

## 🔄 处理流程

```
1️⃣  加载图纸
    DWG 文件 ──LibreDWG──→ DXF ──ezdxf──→ CADDocument
    DXF 文件 ──ezdxf──→ CADDocument

2️⃣  信息提取
    CADDocument ──→ 3,206 个几何实体 (LINE/CIRCLE/ARC/...)
                ──→ 78 个尺寸标注 (线性/半径/直径/...)
                ──→ 299 条文本注释 (TEXT/MTEXT)
                ──→ 图层 & 图块信息

3️⃣  索引构建
    尺寸标注 + 附近文本关联 ──→ 命名参数（如"总长度"、"总宽度"）
    文本注释 K=V 模式匹配 ──→ 键值参数（如"A=50mm"）
    语义规则识别 ──→ 信息参数（材质、色调、部品、性能指标...）
    自动分配语义别名 ──→ 中英文同义词索引

4️⃣  问答交互
    用户问题 ──→ 意图分类 ──→ 参数提取 ──→ 语义匹配 ──→ 格式化回答
                                                          │
                                                回答不满意？──→ LLM 增强 🚀
```

---

## 🎯 支持的查询类型

| 类型 | 示例问题 | 说明 |
|------|----------|------|
| 📏 尺寸参数查询 | "过滤网的长度是多少？" | 支持中英文别名模糊匹配 |
| 📋 多参数列表 | "图纸中有哪些参数？" | 列出所有已索引参数 |
| ⚖️ 参数比较 | "长度和宽度哪个大？" | 自动计算差值并比较 |
| 🏆 极值查询 | "最大的圆角半径是多少？" | 支持最大/最小/最长/最短等 |
| 🔢 计数查询 | "5mm 的尺寸有几处？" | 按数值搜索并统计出现次数 |
| 🔍 数值搜索 | "125mm 代表什么？" | 反向查询某个尺寸对应的参数 |
| ℹ️ 信息查询 | "边框材料是什么？" | 材质、色调、性能指标等非数值参数 |
| 🤖 复杂问答 | "这个过滤网是做什么用的？" | 自动调用 LLM 进行增强回答 |

---

## 🛠️ 技术栈

| 领域 | 技术 | 说明 |
|------|------|------|
| 📐 CAD 解析 | **ezdxf** + **LibreDWG** | ezdxf 读取 DXF，LibreDWG 处理 DWG 格式转换 |
| 📊 数据建模 | **Pydantic** | 强类型数据模型，保障数据结构一致性 |
| 🔢 数值计算 | **NumPy** | 几何计算与数值处理 |
| 🇨🇳 中文 NLP | **jieba** 分词 | 中文分词 + TF-IDF 关键词提取 |
| 🤖 LLM 增强 | **DeepSeek API** | Anthropic 兼容接口，用于复杂问题的增强回答 |
| 🐍 运行环境 | **Python 3.12** | 现代化 Python 特性 |
| 📦 包管理 | **UV** | 高性能 Python 包管理器 |
| 🐳 容器化 | **Docker** (Ubuntu 24.04) | 一键部署，环境一致 |

---

## 🚀 快速开始

### 环境准备

```bash
# 安装依赖（使用 UV）
uv sync

# 或使用 pip
pip install ezdxf pydantic numpy jieba httpx
```

### 使用流程

```bash
# 1️⃣  DWG → DXF 转换（如输入为 DWG 文件）
python tools/dwg_to_dxf.py -i data/cad/filter_modify.dwg

# 2️⃣  构建参数索引
python tools/build_index.py -i data/cad/filter_modify.dxf -o data/index/parameters.json

# 3️⃣  启动交互式 Agent
python main.py --file data/cad/filter_modify.dxf

# 4️⃣  批量评估准确率
python tools/evaluate.py -f data/cad/filter_modify.dxf -q examples/training_questions.txt
```

> 💡 也可直接传入 DWG 文件，系统会自动完成格式转换：
> ```bash
> python main.py --file data/cad/filter_modify.dwg
> ```

### 批量查询模式

```bash
# 从文件读取问题（每行一个），自动输出答案
python main.py --file data/cad/filter_modify.dxf --batch questions.txt
```

---

## 📊 当前成果

| 指标 | 数值 | 说明 |
|------|------|------|
| 📐 提取实体数 | **3,206** | 覆盖 14 种几何类型 |
| 📏 提取尺寸标注 | **78** | 7 种标注类型 |
| 📝 提取文本注释 | **299** | TEXT + MTEXT |
| 🗂️ 参数索引总数 | **102** | 含语义别名 + 信息参数 |
| 📋 训练问题集 | **58 题** | 覆盖 12 类场景 |
| ✅ 问答准确率 | **93.1%** | 目标 ≥90% ✨ |

---

## 💬 交互示例

```
> 过滤网的长度是多少？
📏 总长度(527.0mm) = 527.0 mm

> 过滤网的宽度是多少？
📏 总宽度(517.0mm) = 517.0 mm

> 最大的圆角半径是多少？
🏆 最大的圆角半径是 5.0 mm

> 边框材料是什么？
🧱 部品_边框: 部品 1 ：PS-B

> 过滤网的使用温度是多少？
🌡️ 使用温度: -15℃～+50℃

> 5mm 的尺寸有几处？
🔢 尺寸 5mm 在图纸中共出现 4 处。

> 长度和宽度哪个大？
⚖️ 总长度(527.0mm) (527.0 mm) 大于 总宽度(517.0mm) (517.0 mm)，差值 10.00 mm

> 这个过滤网是做什么用的？
🤖 [LLM 增强回答] 这是一个空调过滤网组件的技术图纸...
```

---

## 📂 项目结构

```
AstraDraft/
├── main.py                        # 🚪 主入口
├── agent/                         # 🧠 Agent 调度层
│   ├── core.py                    #    核心调度逻辑
│   ├── cli.py                     #    命令行交互界面
│   ├── session.py                 #    会话历史管理
│   ├── config.py                  #    配置管理
│   └── exceptions.py              #    异常定义
├── cad_parser/                    # ⚙️ CAD 解析模块
│   ├── reader.py                  #    DXF/DWG 文件读取
│   ├── entities.py                #    几何实体提取
│   ├── dimensions.py              #    尺寸标注解析
│   ├── text_extractor.py          #    文本注释提取
│   ├── layer_manager.py           #    图层管理
│   └── models.py                  #    数据模型定义
├── cad_understanding/             # 🔍 CAD 理解引擎
│   ├── parameter_index.py         #    参数索引构建
│   ├── semantic_mapper.py         #    语义别名映射
│   ├── component_recognizer.py    #    部件识别
│   ├── scale_inferencer.py        #    单位推断
│   └── models.py                  #    数据模型定义
├── nlp_interface/                 # 💬 NLP 交互模块
│   ├── intent_classifier.py       #    意图分类
│   ├── parameter_parser.py        #    参数提取
│   ├── query_processor.py         #    查询处理流水线
│   ├── response_formatter.py      #    回答格式化
│   └── prompt_templates.py        #    LLM 提示模板
├── tools/                         # 🛠️ 工具脚本
│   ├── dwg_to_dxf.py              #    DWG → DXF 转换
│   ├── build_index.py             #    索引构建工具
│   └── evaluate.py                #    准确率评估
├── data/                          # 📁 数据目录
│   ├── cad/                       #    CAD 图纸文件
│   └── index/                     #    参数索引（JSON）
├── examples/                      # 📋 示例问题集
├── Dockerfile                     # 🐳 Docker 构建
└── pyproject.toml                 # 📦 项目配置
```

---

## ⚙️ 配置说明

系统支持通过环境变量或配置文件进行设置：

| 配置项 | 环境变量 | 说明 |
|--------|----------|------|
| CAD 文件路径 | `--file` 参数 | 指定 DXF/DWG 文件 |
| LLM API Key | `ANTHROPIC_AUTH_TOKEN` | DeepSeek API 密钥 |
| LLM API 地址 | `ANTHROPIC_BASE_URL` | 默认 `https://api.deepseek.com/anthropic` |
| LLM 模型 | `ANTHROPIC_MODEL` | 默认 `deepseek-v4-pro[1m]` |
| 日志级别 | `--log-level` | DEBUG / INFO / WARNING |

> 💡 当 LLM API Key 未配置时，系统将自动降级为纯规则问答模式，仍可正常使用基础查询功能。

---

## 🐳 Docker 部署

```bash
# 构建镜像
docker build -t astra-draft .

# 运行交互模式
docker run -it -v $(pwd)/data:/app/data astra-draft --file data/cad/filter_modify.dxf
```
