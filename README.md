# 公司 Agent Skills

团队共享的 agent skill 仓库。目前包含 **`project-agent-init`**——对新项目一键初始化完整的 agent 文档体系（探索代码 → 生成 AGENTS.md / CODE_WIKI / 业务架构 / GLOSSARY / 环境手册 / 实施手册 / docs/agents 三件套 / .gitignore，SLW 低代码平台项目额外安装平台文档与插库 skill，并自动安装整套 mattpocock 工程 skills）。

**完全自包含、离线可用**（676K）：低代码平台文档、插库脚本、30 个 mattpocock skills（含 `setup-matt-pocock-skills` 及三种 tracker 种子模板）全部内置，不依赖任何已存在项目。

---

## 🚀 快速开始（复制下面这句话发给你的 agent）

```text
从 https://github.com/wuganglin/skills.git 克隆 project-agent-init skill（git clone --depth 1 到临时目录即可），把它安装到 ~/.agents/skills/ 下并软链到我当前 agent 的 skills 目录，然后在当前项目里执行这个 skill 完成项目初始化
```

agent 会自动完成：安装 → 软链 → 按流程执行（探索项目 → 生成全套文档 → 安装低代码资产与 mattpocock skills → 校验交付）。

不想说话的话，等价的一行命令（`AGENT_DIR` 按你的工具替换，见下表）：

```bash
git clone --depth 1 https://github.com/wuganglin/skills.git /tmp/company-skills \
  && cp -R /tmp/company-skills/project-agent-init ~/.agents/skills/ \
  && ln -sfn ~/.agents/skills/project-agent-init ~/.zcode/skills/project-agent-init \
  && rm -rf /tmp/company-skills
```

| Agent 工具 | 软链目标目录（AGENT_DIR） |
| --- | --- |
| ZCode | `~/.zcode/skills` |
| Claude Code | `~/.claude/skills` |
| Trae | `~/.trae/skills` |
| 其他 | 该工具读取 skill 的用户级目录 |

> 软链完成后**新开会话**即可用 `/project-agent-init` 命令触发；当前会话内 agent 也可直接读 `~/.agents/skills/project-agent-init/SKILL.md` 按其内容执行，效果等同。

---

## 它产出什么

在**已有代码**的项目根一次性生成：

```
项目根/
├── AGENTS.md                     # agent 入口约定（文档索引/命名规范/快速指引/代码约定/Agent skills）
├── GLOSSARY.md                   # 领域术语表（业务域 + 低代码配置域[仅 SLW 项目]）
├── .gitignore                    # 隐藏目录通配忽略 + .scratch 白名单
├── docs/
│   ├── CODE_WIKI.md              # 代码结构 8 章（模块/架构图/运行方式/开发约定）
│   ├── business-architecture.md  # 业务架构 7 章（业务域/端到端流程/集成/部署拓扑）
│   ├── dev-environment.md        # 环境矩阵 + TDD 验证手段 + 日志排障
│   ├── recipes.md                # 高频实施任务 cookbook
│   └── agents/                   # issue-tracker / domain / triage-labels
└── skills/lowcode-page-gen/      # [仅 SLW 项目] 低代码页面插库 skill（含 lowcode_seed.py）
```

同时把**整套 mattpocock 工程 skills**（30 个：to-spec / to-tickets / triage / tdd / grill-with-docs / domain-modeling / setup-matt-pocock-skills 等）从内置资产安装到 `~/.agents/skills/` 并软链到当前 agent——装齐「需求 → spec → tickets → TDD 实施」的完整工作流。

## 工作流程（skill 内置六步）

| 步骤 | 内容 |
| --- | --- |
| 第 0 步 | 前置检查（已初始化则询问增量/重建；空项目停止） |
| 第 0.5 步 | 从内置资产安装 mattpocock skills 生态（检测→安装→软链→刷新，离线可用） |
| 第 1 步 | 快速摸底（技术栈/SLW 低代码判定/数据库类型/中间件） |
| 第 2 步 | 深度探索（后端+前端两份必答清单，优先派 subagent 并行） |
| 第 3 步 | 关键决策确认（是否装低代码资产/命名规范/占位信息——必须停下问） |
| 第 4-5 步 | 安装静态资产 + 按模板填充文档（每份有质量验收标准） |
| 第 6 步 | 校验（占位符零命中/链接可达）与交付报告（含推测项与待补信息清单） |

**质量红线**：文档独立自洽（不含任何其他项目痕迹）、推测必标注、密码永不落文档、不改动项目既有代码。

## 前置要求

- 一个**已有代码**的仓库（纯空项目先搭代码）
- agent 工具能执行 shell 命令（git clone / cp / ln）
- 无网络要求（全套资产内置；仅"更新到 mattpocock 上游最新"为可选联网操作）

## 目录结构

```
skills/                                ← 本仓库
├── README.md
└── project-agent-init/                ← skill 本体
    ├── SKILL.md                       # 六步流程（给 agent 读）
    ├── assets/                        # 原样安装的静态资产
    │   ├── docs/agents/               #   issue-tracker / domain / triage-labels 标准件
    │   ├── docs/lowcode-config.md     #   [SLW] 低代码表关系闭环（含 4.x 勘误表）
    │   ├── docs/slw-frontend-config.md#   [SLW] 前端脚本 API 速查
    │   ├── gitignore                  #   .gitignore 模板
    │   ├── skills/lowcode-page-gen/   #   [SLW] 插库 skill（SKILL.md + scripts/lowcode_seed.py）
    │   └── mattpocock-skills/         #   mattpocock skills 全套 30 个（离线安装源）
    └── templates/                     # 六份文档骨架（{{占位符}} + FILL 指引）
        ├── AGENTS.md / GLOSSARY.md
        └── docs/CODE_WIKI.md / business-architecture.md / dev-environment.md / recipes.md
```

## 维护

- 改 skill：编辑本仓库 `project-agent-init/` 后提交推送即可；各机器用上面的一行命令重装（同名覆盖前先删旧目录）
- 更新 mattpocock skills 快照：在上游 [mattpocock/skills](https://github.com/mattpocock/skills) 有新版时，替换 `assets/mattpocock-skills/` 下的对应目录
- 以后新增团队 skill：在本仓库加兄弟目录（如 `xxx-skill/`），README 的快速开始按新 skill 改一句话
