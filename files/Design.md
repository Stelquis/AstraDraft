# AstraDraft — AI智能体大赛完整设计方案

## 1. 背景与目标

### 1.1 赛题简介
基于海信企业真实生产流程，以 CAD 图纸为核心数据载体，构建一个智能 Agent 系统，支持用户通过自然语言提问，自动检索并准确反馈图纸中的关键技术参数。

### 1.2 核心任务
1. **搭建智能 Agent 系统** — 构建具备自然语言理解能力的智能体，深度解析 CAD 图纸
2. **精准参数提取** — 用户通过自然语言提问（如"过滤网的高度是多少？"），系统自动检索并反馈图纸中的技术参数

### 1.3 可用数据
- **CAD 图纸**：`过滤网modify.dwg`（AutoCAD 2018 格式 DWG 文件，约 410KB）
- **Agent 训练问题集 & 验证答案集**：竞赛期间从平台下载（当前暂未获取）
- 后续考核还将发布**侧板图、印刷图**两张新图纸

---

## 2. 总体架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                   用户界面层 (CLI/Web)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ 自然语言问题
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Agent 核心调度层                           │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────────────┐   │
│  │ 意图识别  │  │ 上下文管理│  │ 答案生成 & 格式化        │   │
│  └─────┬────┘  └──────────┘  └─────────────────────────┘   │
│        │                                                   │
│  ┌─────▼────┐                                              │
│  │ 参数映射  │                                              │
│  └─────┬────┘                                              │
└────────┼────────────────────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────────────────────┐
│                   CAD 理解引擎                               │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ CAD 解析模块     │  │  语义理解模块    │                   │
│  │ (解析 DXF/DWG)  │──▶  (结构化表示)    │                   │
│  └─────────────────┘  └────────┬────────┘                   │
│                                │                            │
│  ┌─────────────────────────────▼──────────┐                 │
│  │     知识图谱 / 结构化索引               │                 │
│  │     (部件、参数、尺寸、标注关系)         │                 │
│  └─────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### 分层说明

| 层次 | 职责 | 技术选型 |
|------|------|----------|
| **用户界面层** | 接收自然语言输入，展示回答 | CLI（初期）/ Web 或 API（可扩展） |
| **Agent 核心调度层** | 理解意图、管理对话上下文、调用 CAD 引擎、生成答案 | Python + LLM API |
| **CAD 理解引擎** | 解析图纸文件，提取参数，构建结构化表示 | ezdxf + 规则引擎 |
| **数据层** | CAD 文件存储、缓存、索引 | JSON / SQLite / 文件系统 |

---

## 3. 模块详细设计

### 3.1 CAD 解析模块 (`cad_parser/`)

#### 3.1.1 功能
- 读取 DXF/DWG 格式的 CAD 图纸文件
- 提取所有实体（直线、圆弧、圆、多段线等）
- 提取所有标注（尺寸标注、注释文本）
- 提取图层信息

#### 3.1.2 核心文件结构

```
cad_parser/
├── __init__.py              # 模块入口
├── reader.py                # 文件读取器（支持 DXF 直读 + DWG 转换）
├── entities.py              # 实体类型定义与提取
├── dimensions.py            # 尺寸标注提取与解析
├── text_extractor.py        # 文本与注释提取
├── layer_manager.py         # 图层管理
└── models.py                # 数据结构定义（dataclass）
```

#### 3.1.3 关键技术点

**DWG 格式处理**（两种方案）：

| 方案 | 说明 | 推荐度 |
|------|------|--------|
| **方案 A：ODA File Converter** | 使用 ODA 的免费工具将 DWG → DXF，再用 ezdxf 读取 | ⭐ 推荐（完整） |
| **方案 B：二进制解析** | 直接解析 DWG 二进制格式提取关键实体信息 | ⚠️ 备选（有限） |
| **方案 C：ezdxf 内核** | 部分新版 ezdxf 通过集成 ODA SDK 支持 DWG | 🔄 视环境而定 |

**推荐方案**：将 DWG 文件预先转换为 DXF（用 ODA File Converter 或 AutoCAD 导出），系统内部统一处理 DXF 格式。

#### 3.1.4 核心数据结构

```python
@dataclass
class CADDocument:
    """CAD 图纸文档的完整结构化表示"""
    file_path: str
    file_format: str       # "dxf" | "dwg"
    entities: List[Entity]
    dimensions: List[Dimension]
    text_annotations: List[TextAnnotation]
    layers: List[LayerInfo]
    blocks: List[BlockDef]
    metadata: Dict
    bounding_box: BoundingBox

@dataclass
class Dimension:
    """尺寸标注"""
    id: str
    layer: str
    dim_type: str           # "linear" | "aligned" | "diameter" | "radius" | "angular"
    measurement: float      # 实际测量值（图纸单位）
    text: str               # 标注文本（可能包含公差等）
    points: Dict            # 定义点（起点、终点、文本位置等）
    precision: int          # 精度

@dataclass
class Entity:
    """通用实体（用于后续语义分析）"""
    id: str
    layer: str
    type: str               # "LINE" | "ARC" | "CIRCLE" | "LWPOLYLINE" | etc.
    geometry: Dict          # 几何参数
    bounding_box: BoundingBox
```

### 3.2 CAD 语义理解模块 (`cad_understanding/`)

#### 3.2.1 功能
- 将原始 CAD 实体/标注转化为结构化参数索引
- 识别图纸中的部件、特征及其属性
- 建立"自然语言参数名 ↔ CAD 标注"的映射关系

#### 3.2.2 核心文件结构

```
cad_understanding/
├── __init__.py
├── parameter_index.py      # 参数索引构建
├── component_recognizer.py # 部件/特征识别
├── semantic_mapper.py      # 语义映射（NL 术语 → CAD 参数）
├── scale_inferencer.py     # 比例推断
└── models.py               # 语义模型定义
```

#### 3.2.3 工作流

```
原始 DXF/DWG
     │
     ▼
[CAD 解析模块] 提取所有实体、尺寸、文本
     │
     ▼
[语义理解模块]
     1. 尺寸关联：将尺寸标注与其描述的实体关联
     2. 层次聚类：识别部件边界框和部件结构
     3. 文本语义：从注释文本中提取参数含义（如 "H=100"、"宽度"）
     4. 参数索引：构建 {参数名 → 参数值} 的键值索引
     │
     ▼
参数索引 JSON（结构化查询入口）
```

#### 3.2.4 参数索引设计

```json
{
  "document": "过滤网modify.dwg",
  "parameters": [
    {
      "name": "过滤网高度",
      "value": 245.0,
      "unit": "mm",
      "source_dim_id": "dim_001",
      "aliases": ["高度", "高", "H", "height"],
      "layer": "尺寸标注层"
    },
    {
      "name": "过滤网宽度",
      "value": 180.0,
      "unit": "mm",
      "source_dim_id": "dim_002",
      "aliases": ["宽度", "宽", "W", "width"],
      "layer": "尺寸标注层"
    },
    {
      "name": "滤网孔径",
      "value": 2.5,
      "unit": "mm",
      "source_dim_id": "dim_010",
      "aliases": ["孔径", "孔直径", "mesh size"],
      "layer": "标注层"
    }
  ],
  "components": [
    {
      "name": "过滤网主体",
      "bounding_box": {"xmin": 0, "ymin": 0, "xmax": 180, "ymax": 245},
      "parameters": ["过滤网高度", "过滤网宽度"],
      "layer": "主体层"
    }
  ]
}
```

### 3.3 NLP 交互模块 (`nlp_interface/`)

#### 3.3.1 功能
- 解析用户自然语言问题
- 识别查询意图和目标参数
- 支持多轮对话上下文

#### 3.3.2 核心文件结构

```
nlp_interface/
├── __init__.py
├── intent_classifier.py     # 意图分类器
├── parameter_parser.py      # 参数解析（从自然语言中提取参数名）
├── query_processor.py       # 查询处理与分发
├── response_formatter.py    # 回答格式化
└── prompt_templates.py      # LLM 提示词模板
```

#### 3.3.3 意图分类体系

| 意图类型 | 示例 | 处理方式 |
|----------|------|----------|
| `query_parameter` | "过滤网的高度是多少？" | 查参数索引 → 返回值 |
| `query_multi` | "这个图纸上有哪些参数？" | 列出所有参数 |
| `query_compare` | "过滤网外框和滤网哪个更宽？" | 多参数查询 + 比较 |
| `query_info` | "这个零件是做什么的？" | 返回图纸元信息 |
| `clarify` | "我说的'高度'指的是外框高度" | 多轮对话澄清 |

#### 3.3.4 LLM 使用策略

有两种设计思路：

**方案 A：纯规则 + 关键词（推荐，稳定）**
- 不使用 LLM API，通过构建专业词典 + 相似度匹配实现
- 优点：完全离线、可预测、零成本
- 流程：问题预处理 → 分词 → 关键词匹配 → 参数索引查询

**方案 B：LLM 增强（灵活）**
- 使用 LLM API（Claude / GPT）进行意图识别和参数映射
- 将参数索引作为上下文提供给 LLM，由 LLM 推理回答
- 优点：能处理复杂模糊查询，支持多轮对话

**推荐：方案 A + B 混合**
- 基础方案用规则匹配（快速、稳定）
- 可选启用 LLM 增强以处理复杂查询

```python
# 混合策略伪代码
def answer_question(question: str, cad_context: dict) -> str:
    # 步骤1：规则尝试
    param_name = match_keyword(question, cad_context["parameters"])
    if param_name:
        return format_answer(param_name, cad_context["parameters"][param_name])
    
    # 步骤2：LLM 增强（如果配置了 API）
    if llm_available():
        return llm_answer(question, cad_context)
    
    # 步骤3：兜底
    return suggest_available_parameters(cad_context["parameters"])
```

### 3.4 Agent 核心调度层 (`agent/`)

#### 3.4.1 功能
- 协调各模块工作
- 管理对话上下文和状态
- 处理错误和异常情况

#### 3.4.2 核心文件结构

```
agent/
├── __init__.py
├── core.py                 # Agent 主循环
├── session.py              # 对话会话管理
├── config.py               # 配置管理
├── exceptions.py           # 自定义异常
└── cli.py                  # CLI 入口
```

#### 3.4.3 会话流程

```
[用户输入] → [预处理] → [意图识别]
                           │
                    ┌──────┴──────┐
                    │              │
              [参数查询]      [澄清/未知]
                    │              │
                    ▼              ▼
              [CAD 索引]    [LLM 推理]
                    │              │
                    └──────┬──────┘
                           ▼
                    [答案格式化]
                           │
                           ▼
                    [输出给用户]
```

---

## 4. 项目结构总览

```
AstraDraft/
├── README.md                          # 项目说明
├── requirements.txt                   # Python 依赖
│
├── cad_parser/                        # CAD 解析模块
│   ├── __init__.py
│   ├── reader.py                      # DXF/DWG 文件读取
│   ├── entities.py                    # 实体提取
│   ├── dimensions.py                  # 尺寸标注提取
│   ├── text_extractor.py             # 文本提取
│   ├── layer_manager.py              # 图层管理
│   └── models.py                     # 数据模型
│
├── cad_understanding/                 # CAD 语义理解模块
│   ├── __init__.py
│   ├── parameter_index.py            # 参数索引
│   ├── component_recognizer.py       # 部件识别
│   ├── semantic_mapper.py            # 语义映射
│   └── models.py                     # 语义模型
│
├── nlp_interface/                     # NLP 交互模块
│   ├── __init__.py
│   ├── intent_classifier.py          # 意图分类
│   ├── parameter_parser.py           # 参数提取
│   ├── query_processor.py            # 查询处理
│   ├── response_formatter.py         # 回答格式化
│   └── prompt_templates.py           # 提示词模板
│
├── agent/                             # Agent 核心调度
│   ├── __init__.py
│   ├── core.py                       # 主循环
│   ├── session.py                    # 会话管理
│   ├── config.py                     # 配置
│   └── cli.py                        # CLI 入口
│
├── data/                              # 数据文件
│   ├── cad/                          # CAD 图纸
│   └── index/                        # 生成的参数索引缓存
│
├── tests/                             # 测试
│   ├── test_parser.py
│   ├── test_understanding.py
│   ├── test_nlp.py
│   └── test_agent.py
│
├── tools/                             # 工具脚本
│   ├── dwg_to_dxf.py                 # DWG → DXF 转换
│   ├── build_index.py                # 构建参数索引
│   └── evaluate.py                   # 评估脚本
│
├── examples/                          # 示例与使用说明
│   ├── sample_questions.txt
│   └── expected_outputs.txt
│
└── docs/                              # 文档
    └── architecture.md
```

---

## 5. 关键技术决策

### 5.1 关于视觉/多模态模型

**核心分析**：CAD 图纸参数提取**不需要**视觉模型。

| 维度 | 说明 |
|------|------|
| CAD 文件本质 | 图纸本质是结构化数据（矢量图形 + 标注），不是光栅图片 |
| 参数位置 | 尺寸标注（Dimension）以结构化形式存储在 DXF/DWG 中，可直接程序化读取 |
| ezdxf 能力 | 可提取尺寸标注的 measurement 值（直接数值）、关联几何体、文本注释 |
| 视觉模型角色 | 仅在图纸过于复杂或标注不规范时作为辅助 **（非必需）** |

**结论**：主要方案使用结构化解析（ezdxf），LLM 仅用于自然语言理解层。无需多模态/视觉模型。

### 5.2 LLM 选型建议

| 模型 | 适用场景 | 备注 |
|------|----------|------|
| **Claude API** | NLU + 推理 | 擅长工具调用、结构化输出、复杂推理 |
| **GPT-4o** | NLU + 推理 | 类似能力，视 API 可用性 |
| **纯规则方案** | 基础版本 | 完全离线，零成本，适合竞赛基础分 |

> **建议**：先实现纯规则方案保证基础功能，再通过 LLM API（如有可用密钥）做增强。

### 5.3 主要技术依赖

```txt
# requirements.txt
ezdxf>=1.4.0         # DXF 文件读写（核心依赖）
anthropic>=0.49.0    # Claude API（可选，用于 LLM 增强）
openai>=1.0.0        # OpenAI API（可选）
numpy>=1.24.0        # 数值计算（几何处理）
```

---

## 6. 实施路线图

### Phase 1：基础框架（1-2天）
- [x] 项目结构搭建
- [ ] `cad_parser.reader` — DXF 读取功能
- [ ] `cad_parser.models` — 数据模型定义
- [ ] 命令行入口（`python main.py --file xxx.dxf`）

### Phase 2：CAD 解析与索引（2-3天）
- [ ] `cad_parser.dimensions` — 尺寸标注提取
- [ ] `cad_parser.entities` — 实体提取
- [ ] `cad_understanding.parameter_index` — 参数索引生成
- [ ] 处理 DWG → DXF 转换流程

### Phase 3：自然语言查询（2-3天）
- [ ] `nlp_interface.intent_classifier` — 意图分类
- [ ] `nlp_interface.parameter_parser` — 参数提取
- [ ] `nlp_interface.query_processor` — 查询处理
- [ ] `agent.core` — Agent 主循环

### Phase 4：LLM 增强与优化（2天）
- [ ] LLM API 集成
- [ ] 复杂查询处理
- [ ] 错误处理与兜底策略

### Phase 5：测试与交付（2天）
- [ ] 训练数据测试
- [ ] 准确率评估
- [ ] 文档编写
- [ ] 提交材料准备

---

## 7. 评估方案

### 7.1 测试方法

```python
# 评估脚本示例
test_set = [
    {"question": "过滤网的高度是多少？", "expected": "245 mm"},
    {"question": "过滤网的宽度是多少？", "expected": "180 mm"},
    {"question": "滤网孔径多大？", "expected": "2.5 mm"},
    # ... 更多测试用例
]

accuracy = sum(1 for t in test_set if answer(t.question) == t.expected) / len(test_set)
```

### 7.2 关键指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| 参数查询准确率 | 精确匹配的参数值正确率 | ≥ 90% |
| 参数查询召回率 | 图纸中可查参数被正确回复的比例 | ≥ 85% |
| 响应时间 | 从提问到回答的时间 | < 5s |

---

## 8. 提交材料准备

### 8.1 需要提交的3份材料

| 材料 | 内容 | 命名 |
|------|------|------|
| **技术方案报告** | 本文档中的设计思路、架构图、模块说明、使用方法 | `AI智能体大赛.[队伍名].技术方案报告.pdf` |
| **系统代码文件** | 完整可运行代码（建议删除冗余注释） | `AI智能体大赛.[队伍名].系统代码文件.pdf` |
| **系统输出答案** | 样例问题识别准确率 | `AI智能体大赛.[队伍名].系统输出答案.pdf` |

### 8.2 打包规范
- 压缩包命名：`Qoder.AI智能体大赛.[队伍名]`
- 需附 Qoder 账号用于奖励发放
- 需包含身份校验信息（姓名、组织机构、电子邮箱）
- 学生需提供在读证明

---

## 9. 风险和应对

| 风险 | 影响 | 应对方案 |
|------|------|----------|
| DWG 格式无法在环境直接转换 | 无法解析图纸 | 1. 请求主办方提供 DXF 版本；2. 使用纯 Python 二进制解析关键信息 |
| LLM API 不可用 | 无法使用 LLM 增强 | 纯规则方案兜底，不影响基础功能 |
| 新图纸结构差异大 | 参数索引不准确 | 设计通用解析策略，面向 DXF 标准格式而非特定图纸 |
| Qoder 环境限制 | ezdxf 等库不可用 | 提前确认环境，准备纯 Python 方案做备选 |

---

## 10. 开始实施

### 第一步：环境准备
```bash
pip install ezdxf numpy
# 可选
pip install anthropic openai
```

### 第二步：DWG → DXF 转换
安装 ODA File Converter 后将 `过滤网modify.dwg` 转换为 DXF。

### 第三步：构建参数索引
```bash
python tools/build_index.py --input data/cad/过滤网modify.dxf --output data/index/
```

### 第四步：运行 Agent
```bash
python -m agent.cli --file data/cad/过滤网modify.dxf
# 进入交互模式，输入问题即可查询
```

---

> **📋 文档版本**：v1.0  
> **最后更新**：2026-06-03  
> **适用赛题**：海信 × 阿里云 AI智能体大赛
