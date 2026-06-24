# ===================================================================
# Dockerfile 镜像构建
# ===================================================================

# -----------------------------------------------------------------------------
# 第一部分: 基础镜像与环境变量
# -----------------------------------------------------------------------------

# 使用 Ubuntu 24.04 LTS 作为基础镜像
# 选择理由: 长期支持版本(LTS)，稳定性好，软件包丰富
FROM ubuntu:24.04

# 环境变量配置
#   DEBIAN_FRONTEND=noninteractive: 禁用交互式提示，避免安装时卡住
#   LANG/LANGUAGE=C.UTF-8:          设置 UTF-8 编码，支持中文显示和输入
#   DOCKER_HOST:                   Docker 守护进程地址
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LANGUAGE=C.UTF-8 \
    DOCKER_HOST=unix:///var/run/docker.sock

# -----------------------------------------------------------------------------
# 第二部分: 系统源配置
# -----------------------------------------------------------------------------

# 配置阿里云 APT 镜像源（使用 HTTPS，后续会先安装证书）
RUN rm -rf /var/lib/apt/lists/* && \
    echo "deb https://mirrors.aliyun.com/ubuntu/ noble main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/ubuntu/ noble-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/ubuntu/ noble-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/ubuntu/ noble-security main restricted universe multiverse" >> /etc/apt/sources.list

# -----------------------------------------------------------------------------
# 第三部分: 系统工具与 Node.js 安装
# -----------------------------------------------------------------------------

# 步骤1: 先安装 ca-certificates 和 curl，更新证书
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    update-ca-certificates

# 步骤2: 使用 NodeSource 安装 Node.js 22.x（Claude Code CLI 依赖）
RUN curl -fsSL https://deb.nodesource.com/setup_22.x -o /tmp/nodesource_setup.sh && \
    bash /tmp/nodesource_setup.sh && \
    rm /tmp/nodesource_setup.sh

# 步骤3: 安装系统工具与 Python 环境
# 说明: --no-install-recommends 避免安装不必要的推荐包
#
# 分组说明:
#   基础系统工具:
#     git / curl / wget / procps              版本控制与常用命令行工具
#   Python 环境:
#     python3-full / python3-venv / python3-dev  Python 3.12 解释器与开发环境
#     python-is-python3                       将 python 命令映射到 python3
#     libssl-dev / zlib1g-dev                 Python 包编译依赖
#   网络与安全工具:
#     apt-transport-https / gpg                APT HTTPS 支持与 GPG 密钥管理
#   SSH 与网络诊断:
#     openssh-client                          SSH 客户端，用于连接远程 Linux 服务器
#     iputils-ping / net-tools / iproute2     网络连通性测试与接口查看
#   系统管理工具:
#     sudo / htop / vim / less / lsof / psmisc  系统管理工具
#     build-essential                         GCC/G++ 编译工具
RUN apt-get install -y --no-install-recommends \
        git curl wget procps \
        python3-full python3-venv python3-dev python-is-python3 \
        apt-transport-https gpg \
        openssh-client iputils-ping net-tools iproute2 \
        sudo htop vim less lsof psmisc build-essential \
        libssl-dev zlib1g-dev nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    node --version && \
    npm --version

# 配置国内 npm 镜像加速
RUN npm config set registry https://registry.npmmirror.com

# -----------------------------------------------------------------------------
# 第四部分: UV 安装与虚拟环境配置
# -----------------------------------------------------------------------------

# 安装 UV - 极速 Python 包管理器（比 pip 快 10-100 倍）
# 官网: https://github.com/astral-sh/uv
# 说明: 安装脚本将二进制文件输出到 /root/.local/bin，此处移动到 /usr/local/bin 以加入 PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx

# 设置 UV 缓存目录
ENV UV_CACHE_DIR=/opt/.uv-cache

# 使用 UV 创建虚拟环境
RUN uv venv /opt/venv --python 3.12

# 设置环境变量，容器启动后自动激活虚拟环境
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# -----------------------------------------------------------------------------
# 第五部分: Python 依赖安装
# -----------------------------------------------------------------------------
# 说明: 预装项目依赖到虚拟环境，避免每次启动时重复安装
# 依赖来源: Design.md 技术选型 + 项目实际需求
#
# 【CAD 解析】
#   ezdxf          - DXF/DWG 文件读写（核心依赖）
#
# 【开发工具】
#   ipython        - 增强型 Python 交互式解释器
#
# 【数据验证】Data Validation
#   pydantic       - 数据模型验证和序列化
#   pydantic-settings - 配置管理，支持环境变量/文件读取
#
# 【LLM 集成】大语言模型调用（可选增强，直接使用 SDK 调用）
#   openai         - OpenAI 官方 SDK
#   anthropic      - Claude API 官方 SDK
#
# 【数值计算】
#   numpy          - 数值计算（几何处理）
#
# 【NLP 语义匹配】
#   jieba          - 中文分词（自然语言参数提取与关键词匹配）
#
# 【HTTP 客户端】
#   httpx          - 现代化 HTTP 客户端（LLM API 调用等）
#
# 【工具库】Utilities
#   pyyaml         - YAML 配置文件解析
#   python-dotenv  - 从 .env 文件加载环境变量

RUN uv pip install --python /opt/venv \
    ezdxf>=1.4.0 \
    ipython \
    pydantic>=2.5.0 pydantic-settings>=2.1.0 \
    openai>=1.6.0 anthropic>=0.49.0 \
    numpy>=1.24.0 \
    jieba>=0.42.1 \
    httpx>=0.25.0 \
    pyyaml>=6.0.1 python-dotenv>=1.0.0

# -----------------------------------------------------------------------------
# 第六部分: code-server 与 VS Code 扩展
# -----------------------------------------------------------------------------

# 安装 code-server - 浏览器版 VS Code
# 说明: 官方 install.sh 自动下载最新版本并安装
#
# 扩展列表（按功能分类）:
#   语言支持:
#     ms-python.python              Python 语言支持（智能提示、调试、Linter）
#     redhat.vscode-yaml            YAML 语法高亮与校验
#   Git 工具:
#     mhutchie.git-graph            Git 提交图可视化
#   编辑器增强:
#     oderwat.indent-rainbow        缩进彩虹，代码层级可视化
#   AI 编程助手:
#     anthropic.claude-code         Claude Code AI 编程助手
#     tencent-cloud.coding-copilot  CodeBuddy AI 辅助编程，代码补全和生成
#   开发服务器:
#     CloudStudio.live-server       Live Server 本地开发服务器
#   CNB 平台扩展:
#     cnbcool.cnb-welcome           CNB 平台欢迎页（内部源，容错安装）
RUN curl -fsSL https://code-server.dev/install.sh | sh && \
    code-server --install-extension ms-python.python && \
    code-server --install-extension redhat.vscode-yaml && \
    code-server --install-extension mhutchie.git-graph && \
    code-server --install-extension oderwat.indent-rainbow && \
    code-server --install-extension anthropic.claude-code && \
    code-server --install-extension tencent-cloud.coding-copilot && \
    code-server --install-extension CloudStudio.live-server && \
    code-server --install-extension cnbcool.cnb-welcome || true

# -----------------------------------------------------------------------------
# 第七部分: AI CLI 工具配置
# -----------------------------------------------------------------------------

# 安装 Claude Code CLI (需要 Node.js 22+)
# 说明: Anthropic 官方 CLI 编程助手，支持 Claude 3.5 Sonnet/Opus 等模型
RUN npm install -g @anthropic-ai/claude-code

# 复制 Claude Code 初始化脚本
COPY scripts/init-claude.sh /usr/local/bin/init-claude.sh
RUN chmod +x /usr/local/bin/init-claude.sh

# 安装 Qoder CLI
# 说明: 终端原生 AI 编程助手，围绕真实代码协同开发，支持从开发、调试到上线全流程
# 官网: https://qoder.com
RUN curl -fsSL https://qoder.com/install | bash

# -----------------------------------------------------------------------------
# 第八部分: LaTeX 编译环境 (XeLaTeX) — 用于生成技术方案报告 PDF
# -----------------------------------------------------------------------------
# 安装 TeX Live 核心包，支持 XeLaTeX 编译 .tex 生成 PDF
# 用途: 比赛需提交技术方案报告(PDF)，可用 XeLaTeX 模板直接编译
#
# 包说明:
#   texlive-xetex             - XeTeX 引擎，支持 Unicode 和系统字体
#   texlive-latex-recommended - LaTeX 推荐宏包集 (amsmath, booktabs, geometry 等)
#   texlive-fonts-recommended - 推荐字体包 (ec, cm-super)
#   texlive-lang-chinese      - 中文字体支持 (ctex, xeCJK) — 支持中文技术报告
#   latexmk                   - 自动化编译工具 (自动处理多次编译、参考文献等)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        texlive-xetex \
        texlive-latex-recommended \
        texlive-fonts-recommended \
        texlive-lang-chinese \
        latexmk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    xelatex --version && \
    latexmk --version

# -----------------------------------------------------------------------------
# 第七部分补充: LibreDWG (DWG → DXF 转换)
# -----------------------------------------------------------------------------
# 说明: 从源码编译安装 dwg2dxf 工具，用于将 AutoCAD DWG 文件转换为 DXF 格式
RUN apt-get update && \
    apt-get install -y --no-install-recommends autoconf automake libtool texinfo pkg-config && \
    cd /tmp && \
    git clone --depth 1 https://github.com/LibreDWG/libredwg.git && \
    cd libredwg && \
    git submodule update --init && \
    autoreconf -fi && \
    ./configure --prefix=/usr/local && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd / && rm -rf /tmp/libredwg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# 第九部分: 环境变量配置
# -----------------------------------------------------------------------------

# Python 运行时环境变量
ENV PYTHONPATH=/workspace
ENV PYTHONUNBUFFERED=1

# 使用虚拟环境（由 uv 在 /opt/venv 创建）
ENV PATH=/opt/venv/bin:$PATH
ENV VIRTUAL_ENV=/opt/venv

# 字符集配置：支持中文输入、输出与文件名显示
ENV LANG=C.UTF-8
ENV LANGUAGE=C.UTF-8

# Node.js 开发环境标识
ENV NODE_ENV=development

# -----------------------------------------------------------------------------
# 第十部分: 配置文件复制
# -----------------------------------------------------------------------------

# 复制 VS Code 设置到容器
# 路径说明: code-server 的机器级（Machine）设置目录
# 作用: 预配置编辑器主题、字体、Python 解释器路径等，开箱即用
COPY .vscode/settings.json /root/.local/share/code-server/Machine/settings.json

# ---------------------------------------------------------------------------
# 第十一部分: 工作目录与启动命令
# ---------------------------------------------------------------------------

# 设置容器默认工作目录
# 说明: 与 CNB 平台代码挂载点保持一致，启动后直接进入项目根目录
WORKDIR /workspace

# 容器默认启动命令
# 说明: 启动交互式 bash shell；实际运行时由 .cnb.yml 覆盖，用于启动 code-server 等服务
#
# 端口参考（由平台自动映射，无需手动 EXPOSE）:
#   8080  code-server Web IDE
#   8000  FastAPI 应用服务
CMD ["/bin/bash"]
