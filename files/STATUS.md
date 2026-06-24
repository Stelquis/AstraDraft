# AstraDraft 项目状态总结

> 最后更新: 2026-06-04
> 分支: main | 最新提交: `1310cef` docs: 丰富 README 内容并分离竞赛指南
>
> **本文档是每次启动开发环境后的必读文档**，帮助快速恢复上下文。

---

## 0. AI 编程模式与 AstraDraft 开发指南

以下 6 种 AI 编程模式对本项目有不同程度的参考价值，按优先级排列：

### 核心模式（日常开发中应自觉运用）

**Harness Engineering 驾驭工程** — 适用度：很高

围绕 AI 搭建约束机制，确保 AI 可靠地工作。包含三大支柱：

| 支柱 | 在 AstraDraft 中的实践 |
|------|----------------------|
| 上下文工程 | `parameter_index.py` 构建参数索引、`semantic_mapper.py` 语义别名映射 — 确保问答时获得正确上下文 |
| 架构约束 | Pydantic 数据模型强制类型约束、意图分类器的 4 类意图边界、LLM fallback 策略 |
| 熵管理 | 处理新图纸时定期清理硬编码规则、不一致别名、过时文档；通过 `evaluate.py` 回归测试防止退化 |

**Agentic Engineering 智能体工程** — 适用度：高

"先想清楚、写好方案、拆好任务，再交给 AI 执行"。在赛事冲刺阶段用于：规划每个模块的优化任务、设定验收标准（准确率目标）、迭代式地让 AI 辅助完成代码修改并验证。

**Ralph Wiggum Loop** — 适用度：中高

用评估脚本驱动的短循环快速迭代：修改匹配策略 → 跑 `tools/evaluate.py` → Git 提交 → 检查结果。拿到官方训练集后，用同样的循环快速适配新问题。

### 辅助模式（特定场景参考）

**SDD 规范驱动开发** — 适用度：中高

`Design.md` 已是非正式规范。赛事冲刺时可升级为正式接口定义，处理新图纸前先写规范再实现，提交技术方案报告时规范文档可直接转化为报告素材。

### 低适用度模式

- **Vibe Coding**：项目已过原型阶段，当前需要精确调优而非跟着感觉走。
- **BMAD 角色化开发**：核心架构已定型，单人/小团队竞赛项目不需要完整的角色化流程。

### 推荐组合

```
Harness Engineering (稳定环境)
  + Agentic Engineering (规划任务)
    + Ralph Wiggum Loop (快速迭代)
```

---

## 1. 项目概览

**AstraDraft** 是参加 **海信 × 阿里云 AI智能体大赛** 的参赛作品。系统基于 CAD 图纸（DWG/DXF），通过自然语言问答方式，自动提取并反馈图纸中的关键技术参数。

### 赛题核心要求
1. 搭建智能 Agent 系统 — 深度解析 CAD 图纸
2. 精准参数提取 — 用户用自然语言提问，系统自动检索并反馈技术参数

### 赛事时间线

| 阶段 | 时间 (UTC+8) | 状态 |
|------|-------------|------|
| 注册与实名验证 | 5月28日 - 6月4日 | **进行中** |
| 赛事阶段（下载数据+开发） | 6月5日 - 6月22日 | 待开始 |
| 代码&技术方案提交 | 6月5日 - 6月22日 | 待开始 |
| 赛事结果评估 | 6月23日 - 6月25日 | 待开始 |
| 赛事结果公布 | 6月26日 | 待开始 |

---

## 2. 当前进度

### 已完成

| 模块 | 状态 | 说明 |
|------|------|------|
| DWG→DXF 转换 | 完成 | LibreDWG 源码编译，`dwg2dxf` 工具可用 |
| CAD 解析器 | 完成 | 3206 实体、299 文本标注、尺寸标注全部解析 |
| 参数索引 | 完成 | 102 个参数，含语义别名 |
| NLP 交互层 | 完成 | jieba 分词 + 规则匹配 + 意图分类 |
| LLM 增强 | 完成 | DeepSeek API 集成（复杂问题 fallback） |
| Agent 核心 | 完成 | CLI 入口 + 会话管理 + 混合策略 |
| 训练问题集 | 完成 | 58 题（12 类），准确率 93.1% |

### 关键指标

- **参数总数**: 102 个（含线性尺寸、对齐尺寸、材质、色调、性能指标等）
- **训练问答准确率**: 93.1%（从初始 43.1% 优化而来）
- **支持的查询类型**: 尺寸查询、计数查询、最大值/最小值、材质/性能信息、比较查询

---

## 3. 技术架构

```
用户提问 (自然语言)
    ↓
[nlp_interface] → 意图分类 + 参数解析
    ↓
[cad_understanding] → 语义映射 + 参数索引
    ↓
[cad_parser] → DXF/DWG 文件解析
    ↓
[agent/core.py] → 规则匹配 + LLM fallback (DeepSeek)
    ↓
格式化回答
```

### 核心依赖

| 库 | 版本 | 用途 |
|----|------|------|
| ezdxf | ≥1.4.0 | DXF 文件读取 |
| pydantic | ≥2.5.0 | 数据模型 |
| pydantic-settings | ≥2.1.0 | 配置管理 |
| jieba | ≥0.42.1 | 中文分词 |
| httpx | ≥0.25.0 | HTTP 客户端（LLM API） |
| anthropic | ≥0.49.0 | DeepSeek Anthropic API 兼容层 |
| numpy | ≥1.24.0 | 数值计算 |

---

## 4. 项目结构

```
/workspace/
├── cad_parser/              # CAD 文件解析层
│   ├── models.py            # Pydantic v2 数据模型
│   ├── reader.py            # DXF/DWG 文件读取
│   ├── entities.py          # 几何实体提取
│   ├── dimensions.py        # 尺寸标注解析
│   ├── text_extractor.py    # 文本标注提取
│   └── layer_manager.py     # 图层管理
├── cad_understanding/       # 语义理解层
│   ├── parameter_index.py   # 参数索引（核心）
│   ├── semantic_mapper.py   # 语义映射（jieba + 同义词）
│   └── scale_inferencer.py  # 单位推断
├── nlp_interface/           # NLP 交互层
│   ├── intent_classifier.py # 意图分类
│   ├── parameter_parser.py  # 参数名提取
│   ├── query_processor.py   # 查询处理主流程
│   └── response_formatter.py# 回答格式化
├── agent/                   # Agent 核心层
│   ├── config.py            # 配置管理（pydantic-settings）
│   ├── exceptions.py        # 自定义异常
│   ├── session.py           # 会话管理
│   ├── core.py              # Agent 主循环（规则+LLM混合）
│   └── cli.py               # CLI 入口
├── tools/
│   ├── dwg_to_dxf.py        # DWG 转换工具
│   ├── build_index.py       # 索引构建 CLI
│   └── evaluate.py          # 评估脚本
├── examples/
│   └── training_questions.txt # 58 题训练集
├── data/
│   ├── cad/                 # CAD 源文件
│   └── index/               # 参数索引缓存
├── files/
│   ├── Design.md            # 完整设计方案
│   ├── STATUS.md            # 本文档（启动后必读）
│   └── 竞赛指南.md           # 海信×阿里云赛事规则与赛程
├── Dockerfile               # 开发环境（Ubuntu 24.04 + Python 3.12）
├── .cnb.yml                 # CNB CI/CD 配置
├── requirements.txt         # Python 依赖
├── .env                     # 环境变量（API Key 等，gitignored）
├── .gitignore
└── main.py                  # 顶层入口
```

---

## 5. 环境配置

### 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 转换 DWG → DXF（如果只有 DWG 文件）
python tools/dwg_to_dxf.py --input data/cad/filter_modify.dwg

# 构建参数索引
python tools/build_index.py --input data/cad/filter_modify.dxf --output data/index/

# 启动交互式问答
python main.py --file data/cad/filter_modify.dxf

# 运行评估
python tools/evaluate.py --questions examples/training_questions.txt
```

### API 密钥配置

`.env` 文件（已 gitignore）：

```env
ASTRADRAFT_LLM_ENABLED=true
ASTRADRAFT_LLM_API_KEY=sk-353805dc3a7d4a97a21519398d9f818e
ASTRADRAFT_LLM_BASE_URL=https://api.deepseek.com/anthropic
ASTRADRAFT_LLM_MODEL=deepseek-v4-pro[1m]
```

> **注意**: `.env` 文件不纳入 Git，每次新环境需手动创建或从安全存储恢复。

### Docker 开发环境

镜像: `docker.cnb.cool/oriondawn/astradraft`

主要组件:
- Ubuntu 24.04 + Python 3.12 (via UV)
- Node.js 22
- code-server（VS Code 网页版）
- LibreDWG（DWG→DXF 编译安装）
- ezdxf + jieba + DeepSeek SDK

---

## 6. 已知问题与注意事项

1. **DWG AC1032 格式**: `filter_modify.dwg` 是 AutoCAD 2018 格式，ezdxf 无法直接读取，必须先通过 `dwg2dxf` 转换
2. **dimtype 位标志**: ezdxf 返回的 dimtype 使用复合位标志，需用 `& 0x0F` 提取真实类型
3. **insunits=0 处理**: 中国工业 CAD 中 insunits=0（无单位）默认按毫米处理
4. **Pydantic v2 PrivateAttr**: `CADDocument._dxf_doc` 必须实例化后赋值，不能通过构造函数传入
5. **LLM API 响应**: DeepSeek Anthropic 兼容 API 返回的 content 包含 thinking 和 text 两个 block，需过滤 `type=="text"`

---

## 7. 下一步工作

### 高优先级（赛事阶段 6月5日开始后）

1. **下载训练数据**: 从平台获取官方训练问题集、验证答案集
2. **处理新图纸**: 平台将发布 **侧板图** 和 **印刷图**（AC1032 格式）
3. **参数映射优化**: 根据实际问题集调整语义别名和匹配策略
4. **准确率验证**: 用官方答案集评估系统准确率

### 提交材料（截止 6月22日）

| 材料 | 格式 | 命名 |
|------|------|------|
| 技术方案报告 | PDF | `AI智能体大赛.参赛队伍名称.技术方案报告.pdf` |
| 系统代码文件 | PDF/ZIP | `AI智能体大赛.参赛队伍名称.系统代码文件.pdf` |
| 系统输出答案 | PDF | `AI智能体大赛.参赛队伍名称.系统输出答案.pdf` |

压缩包命名: `Qoder.AI智能体大赛.参赛队伍名称`

---

## 8. Git 历史

```
1310cef docs: 丰富 README 内容并分离竞赛指南
248ed9e docs: 添加项目状态总结文档，便于下次启动开发环境时快速恢复上下文
b12b1f7 fix: 修复计数查询和复杂问题判断的优先级冲突
5c1285e feat: 实现 AstraDraft CAD 智能问答 Agent 系统
e77e383 chore: 更新 Dockerfile 注释
89532fa feat: initialize AstraDraft project with CI, Docker, and MIT license
```

远程: `https://cnb.cool/oriondawn/astradraft`
用户: `STARS_NIU`
