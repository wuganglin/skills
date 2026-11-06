***
name: "project-agent-init"
description: "对新项目一键初始化 agent 文档体系与目录结构：探索代码库后生成 AGENTS.md、CODE_WIKI、业务架构、GLOSSARY、dev-environment、recipes、docs/agents 三件套与 .gitignore；SLW 低代码平台项目额外安装 lowcode-config/slw-frontend-config 平台文档与 lowcode-page-gen 插库 skill。当用户要求初始化新项目、搭建项目 agent 文档体系、或在新项目执行 /project-agent-init 时调用。自包含，不依赖任何已存在项目。"
------------------------------------------------------------------

# 项目 agent 文档体系初始化（project-agent-init）

把一个新项目初始化为 **agent 可直接实施需求**的完整文档工作区。一次调用产出：

```
项目根/
├── AGENTS.md                     # agent 入口约定（文档索引/命名规范/快速指引/代码约定/Agent skills）
├── GLOSSARY.md                   # 领域术语表（业务域 + 低代码配置域[仅 SLW]）
├── .gitignore                    # 隐藏目录通配忽略 + .scratch 白名单
├── docs/
│   ├── CODE_WIKI.md              # 代码结构 8 章
│   ├── business-architecture.md  # 业务架构 7 章
│   ├── dev-environment.md        # 环境矩阵 + TDD 验证手段 + 排障
│   ├── recipes.md                # 高频实施任务 cookbook
│   ├── agents/                   # issue-tracker / domain / triage-labels（agent 工作流标准件）
│   ├── lowcode-config.md         # [仅 SLW] 低代码表关系闭环（含 4.x 勘误表）
│   └── slw-frontend-config.md    # [仅 SLW] 前端脚本 API 速查
└── skills/
    └── lowcode-page-gen/         # [仅 SLW] 低代码页面插库 skill（SKILL.md + scripts/lowcode_seed.py）
```

**产物原则**：文档必须**独立自洽**——不得出现任何其他项目的名字、客户名、库名、路径；未证实的事实标注「推测/待确认」；密码永不落文档（写"见 yml"）。

**本 skill 自包含**：`assets/`（原样安装的静态资产：项目文档标准件、SLW 低代码文档与插库 skill、**mattpocock skills 全套 30 个**）与 `templates/`（骨架+填充指引）都在本 skill 目录内，**不读取任何外部项目、安装不依赖网络**（可选更新除外）。

## 第 0 步：前置检查

- 项目根已有 `AGENTS.md` → **停下问用户**：增量更新现有文档（读各文档后按流程刷新）还是推倒重建（明确同意后才覆盖）
- 目标目录为空/非代码仓库 → 停止：本 skill 面向**已有代码**的项目，纯空项目先搭代码再说

## 第 0.5 步：安装 mattpocock skills 生态（agent 工作流引擎，内置资产、离线可用）

本 skill 安装的 `docs/agents/` 三件套（issue-tracker / triage-labels / domain）是 [mattpocock/skills](https://github.com/mattpocock/skills) 工程 skills 的**配置文件**——装齐那套 skills 才能跑「需求 → spec → tickets → TDD 实施」的完整工作流。**本 skill 已把整套 mattpocock skills（30 个，含 `setup-matt-pocock-skills` 及其 GitHub/GitLab/local 三种 tracker 种子模板）内置在 `assets/mattpocock-skills/`，安装不依赖网络**。

**与 setup-matt-pocock-skills 的关系**：本 skill 已按最常用配置（本地 markdown issue tracker + 默认五标签 + GLOSSARY 单上下文）把它的配置产物直接装进项目（即 assets/docs/agents 三件套），**无需再跑 setup**。若该项目日后想换 GitHub/GitLab tracker 或改标签词表，装好后跑 `/setup-matt-pocock-skills` 交互重配即可。

1. **检测**（标志性组合：`to-spec`、`to-tickets`、`triage`、`grill-with-docs`、`domain-modeling`、`setup-matt-pocock-skills`）：

   ```bash
   ls ~/.agents/skills/ | grep -xE "to-spec|to-tickets|triage|grill-with-docs|domain-modeling|setup-matt-pocock-skills"
   ```

   全部命中 → 已安装，仅检查当前 agent skill 目录软链是否齐全（缺哪个补链哪个），跳到第 1 步；部分缺失 → 只补缺的。

2. **从内置资产安装到 `~/.agents/skills/`**（`<本skill目录>` = 本 SKILL.md 所在目录，按实际加载路径解析为绝对路径）：

   ```bash
   for d in <本skill目录>/assets/mattpocock-skills/*/; do
     name=$(basename "$d")
     if [ ! -e ~/.agents/skills/"$name" ]; then cp -R "$d" ~/.agents/skills/"$name"; fi
   done
   ```

   已存在的同名 skill **不覆盖**（用户可能改过/是更新版本）。装完抽查：`ls ~/.agents/skills/to-spec/SKILL.md` 等。

3. **软链到当前 agent 的 skill 目录**（按宿主探测：ZCode → `~/.zcode/skills`；另有 `~/.claude/skills`、`~/.trae/skills` 等，装到实际使用的那一个；仅链缺失的，不动用户既有软链）：

   ```bash
   # AGENT_SKILL_DIR 按实际宿主替换，如 ~/.zcode/skills
   for d in ~/.agents/skills/*/; do
     name=$(basename "$d")
     [ -e "$AGENT_SKILL_DIR"/"$name" ] || ln -sfn ~/.agents/skills/"$name" "$AGENT_SKILL_DIR"/"$name"
   done
   ```

4. **刷新生效**：软链落盘即文件系统就绪；agent 的 skill 列表一般在**新会话**装载——告知用户新开会话即可用 `/to-spec`、`/triage`、`/setup-matt-pocock-skills` 等命令；**当前会话兜底**：若列表尚未出现，agent 直接读 `~/.agents/skills/<名>/SKILL.md` 并按其内容执行，效果等同。

5. **（可选）更新到上游最新**：内置资产是制作时刻的快照；用户想要最新版时用官方途径更新——`npx skills@latest add mattpocock/skills -a <agent>` 或 `git clone --depth 1 https://github.com/mattpocock/skills` 后把 `skills/<类别>/<skill>/` 覆盖装到 `~/.agents/skills/`（更新动作由用户主动发起，本流程不做）。

## 第 1 步：快速摸底（5 分钟，不派 agent）

按顺序探查并记录（每项都有证据路径）：

1. `git remote -v`、`git log --oneline -10`（仓库来源与近期演进）
2. 后端形态：找 `pom.xml`/`build.gradle`/`go.mod`/`package.json`（服务端）——多模块则列模块清单与相互依赖
3. **SLW 低代码判定**：依赖里找 `core-window`/`com.anyhai`/`com.forcecon`，前端 `package.json` 找 `slw`/`yh-` 系包；二者任一命中即按「SLW 项目」走
4. 启动配置：`application*.yml`/`.env`/`config.*`——端口、context-path、数据源（**类型+地址**，密码只记"见 yml"）、中间件（Redis/MQ/对象存储）、定时任务框架
5. 前端形态：`package.json`（框架/构建工具/包管理器）、`vite.config`/`webpack.config`（dev 端口、proxy、base）、`src` 目录组织
6. 测试现状：找 `src/test`、测试依赖、CI 配置
7. 数据库类型（**关键**）：PostgreSQL / 达梦 / MySQL…——决定低代码插库 skill 的使用路径与方言警告

## 第 2 步：深度探索（agent 实施的素材来源）

**优先派 subagent 并行探索**（后端一个、前端一个）；不支持 subagent 时自己按清单查。两个探索的必答问题清单：

**后端探索**——① 每模块职责与依赖；② 技术栈精确版本（JDK/框架/ORM/数据库驱动）；③ 启动类与三件配置（port/context/数据源）；④ 业务域全景（每域核心 Controller/Service/实体表名）；⑤ 3~6 条端到端流程的调用链；⑥ 外部集成（HTTP 接口/定时任务清单/消息）；⑦ 代码分层约定（包结构/基类/主键/返回包装）；⑧ 领域术语提炼（中文业务名词+代码名+一句话解释，15~30 个）；⑨ 已知技术债。要求：结论附文件路径、推测显式标注、不贴大段代码。

**前端探索**——① 技术栈与版本；② 构建/部署配置（端口/proxy/base/deploy）；③ 目录组织与路由生成方式（**静态 or 后端菜单驱动**——决定 recipes 的"新增页面"写法）；④ 低代码运行时痕迹与页面比例；⑤ 页面清单按业务域分组；⑥ 与后端交互（baseURL/序列化/令牌）；⑦ 代码约定（选项式 vs 组合式/i18n/状态管理）。

## 第 3 步：关键决策确认（必须停下等用户）

拿探索摘要向用户确认三件事（给推荐默认值）：

1. **是否安装 SLW 低代码资产**（判定为 SLW 项目时推荐"是"——装 lowcode 两份文档 + lowcode-page-gen skill 并在 AGENTS.md 建索引；用户不想要可跳过）
2. **命名规范**：默认采用「日期开头（YYYYMMDD）+ 中文标题」强制规范（ADR/spec/ticket/SQL 归档），用户可否决
3. **占位信息**：环境账号/部署方式/生产地址等探索不到的信息——确认留占位清单（默认）还是用户现在提供

## 第 4 步：安装静态资产（assets/ → 项目）

| asset | 目标 | 说明 |
| --- | --- | --- |
| `assets/gitignore` | `.gitignore` | 已有则合并（保留用户规则，去重） |
| `assets/docs/agents/*.md` | `docs/agents/` | 原样复制（标准件，无占位符） |
| `assets/docs/lowcode-config.md` | `docs/` | **仅 SLW**；复制后**改写头部注记**：替换 `{{项目名}}/{{日期}}/core-window 版本/slw 版本/租户过滤开关/数据库类型` 四组占位（值来自第 1、2 步实测） |
| `assets/docs/slw-frontend-config.md` | `docs/` | **仅 SLW**；同上改写头部注记（slw 版本/装载点路径/构建 base） |
| `assets/skills/lowcode-page-gen/` | `skills/lowcode-page-gen/` | **仅 SLW**；整目录复制（含 scripts/lowcode_seed.py，复制后 `python3 -m py_compile` 校验） |

## 第 5 步：填充模板（templates/ → 项目）

逐份复制并填充，占位符 `{{...}}` 全部替换、`<!-- FILL -->` 指引注释**删除**：

| 模板 | 质量验收标准 |
| --- | --- |
| `AGENTS.md` | 30 秒能读懂项目全貌；索引表每行链接可达且与实际产物一致；代码约定每条有证据；非 SLW 项目删尽低代码段落 |
| `GLOSSARY.md` | 业务术语 15~30 个、每个有代码名与 Avoid 反例；低代码域（SLW）为成品节，仅改租户/路由两处按实际 |
| `docs/CODE_WIKI.md` | 8 章齐；两张 mermaid 图节点名 = 实际类名/表名/模块名；第 7 章命令可复制执行；维护脚注列全部推测项 |
| `docs/business-architecture.md` | 7 章（非 SLW 删第 6 章）；流程图含触发源→调用链→落表；每域要点落到表名/类名 |
| `docs/dev-environment.md` | 环境矩阵全实测值；TDD 段与项目测试现状一致；占位清单保留给用户 |
| `docs/recipes.md` | 章节按项目高频任务改写；每个项目特有坑（菜单挂载/三层同步/跨进程引用等）必须成节 |

## 第 6 步：校验与交付

1. `grep -rn '{{' AGENTS.md GLOSSARY.md docs/ skills/` → 必须零命中（assets 里 lowcode-config/slw-frontend-config 头部注记占位符也必须已替换）
2. 校验 AGENTS.md 索引表所有相对链接文件存在
3. `git status --short` 展示新增清单；**不提交**（用户自行决定）
4. 交付报告必须包含：①产物清单；②**推测/待确认事项列表**；③**待用户补充信息清单**（来自 dev-environment 占位）；④低代码资产使用提示（目标库非 PG 时的方言路径；AGENTS.md 已建索引，用户提到低代码时 agent 按 `skills/lowcode-page-gen/SKILL.md` 路径加载）；⑤**mattpocock skills 安装结果**（已装/从内置资产新装/补链清单；提醒新会话即可用 `/to-spec`、`/triage` 等命令；内置资产为制作时快照，要最新版走第 0.5 步第 5 点的官方更新途径）

## 质量红线

- **独立自洽**：产出文档不得含其他项目的项目名/客户名/库名/本地路径（assets 已泛化，填充时也不得引入）
- **不编造**：写不出的写「待确认」；推测必须带标记；密码/密钥永不落文档
- **可执行**：文档里的命令、路径、端口全部实测或标注来源
- **外科手术**：不改动项目既有代码；已有文档走增量更新并保留用户手写内容
