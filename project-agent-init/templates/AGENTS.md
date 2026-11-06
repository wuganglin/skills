# AGENTS.md

<!-- ============================================================
  project-agent-init 模板：AGENTS.md
  填充规则：
  1. 替换所有 {{占位符}}（探索结果或用户答复）
  2. 删除全部 <!-- FILL --> 注释行
  3. 交付前 grep '{{' 必须零命中
  非 SLW 低代码项目：删除「低代码」相关段落与索引行
============================================================ -->

{{项目名}}（{{项目中文定位一句话}}）工作区的 AI 编码代理约定。{{业务域概述一句话}}：{{技术栈概述：语言/框架/多模块或单体/进程与端口}} + 前端 {{框架}}（{{前端目录}}，dev :{{端口}}）<!-- FILL: 概述要能让人 30 秒理解项目全貌，端口/context-path 写实测值 -->{{+ 低代码平台描述（仅 SLW 项目）}}

## 项目文档索引（按任务场景选用）

| 场景 | 文档 |
| --- | --- |
| 了解代码结构 / 模块职责 / 运行方式 | [docs/CODE_WIKI.md](docs/CODE_WIKI.md) |
| 了解业务域 / 端到端流程 / 外部集成 | [docs/business-architecture.md](docs/business-architecture.md) |
| **实施后怎么验证（TDD 流程/测试命令）/ 环境地址 / 日志排障** | [docs/dev-environment.md](docs/dev-environment.md) |
| **常见实施任务逐步手册（按项目实际任务改写章节）** | [docs/recipes.md](docs/recipes.md) |
| 领域术语（{{举例 3 个核心术语}}…） | [GLOSSARY.md](GLOSSARY.md) |
<!-- FILL: 仅 SLW 低代码项目保留以下两行 + lowcode-page-gen 索引行；并按实际改写 -->
| 低代码配置化表关系（ad_menu→sys_datasource_* 闭环） | [docs/lowcode-config.md](docs/lowcode-config.md) |
| 低代码脚本 API / 事件签名 / 占位符（写脚本时速查） | [docs/slw-frontend-config.md](docs/slw-frontend-config.md) |
| **低代码页面生成 skill（`skills/lowcode-page-gen/`，项目共有资产，随仓库分发）**——**凡提到"生成/修改低代码页面、配置化管理页面、主子表 CRUD、给窗口加字段/按钮"等低代码配置化工作，优先调用此 skill** | [skills/lowcode-page-gen/SKILL.md](skills/lowcode-page-gen/SKILL.md) |

## 文档与工单命名规范（强制）

**所有 ADR、spec、ticket 的 `.md` 文件，文件名以日期开头（YYYYMMDD）+ 中文标题**；**spec 的目录名也用中文（同样日期开头）**；**生成的 SQL 归档文件（docs/sql/）同样日期开头 + 中文对象名**：

```
docs/adr/YYYYMMDD-<中文标题>.md
.scratch/YYYYMMDD-<中文标题>/spec.md
.scratch/YYYYMMDD-<中文标题>/issues/YYYYMMDD-<中文标题>.md
docs/sql/YYYYMMDD-HHMMSS-<中文对象名>-seed.sql
```

细则见 [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md)「命名规范」。

## 快速指引

<!-- FILL: 按项目实际写 3~6 个小节，常见：数据库 / 后端调试重启 / 前端 dev server / 前端页面编写规范；以下是骨架示例 -->

### 数据库（{{数据库类型}}）

dev 库（{{配置文件路径}}）：{{类型}} `{{host:port}}/{{库名}}`（{{内网/本地}}，密码见 yml）。{{中间件清单：Redis/对象存储/MQ 及地址}}。

### 后端调试重启

改 {{后端语言}} 代码后的标准重启循环（{{进程清单}}按需重启）：**明示后 kill 旧进程 → `{{编译命令}}` → 重启对应进程**。进程管理优先用户 IDE Run 窗口；启动顺序：{{实际依赖顺序}}。

### 前端 dev server（{{前端目录}}，{{构建工具}}）

- dev `{{host:port}}`，proxy `{{前缀}}` → {{代理目标及含义}}。
- 改前端代码**不动服务**：HMR 自动生效。包管理器是 {{npm/pnpm}}。装新包/改构建配置的重启规则见全局约定。

<!-- FILL: 前端为 Vue 时保留本节（按实际装了的 skill 调整表格）；非 Vue 项目删除 -->
### 前端 Vue 页面编写（优先参照 skill）

写或改前端 Vue 页面时，**若当前环境已安装 Vue 相关 skill，先加载对应 skill 并按其规范实现**：通用写法 `vue-best-practices`、工具函数 `vueuse-functions`、路由 `vue-router-best-practices`、状态 `vue-pinia-best-practices`、**改老页面（选项式）** `vue-options-api-best-practices`、JSX `vue-jsx-best-practices`、单测 `vue-testing-best-practices`、排障 `vue-debug-guides`。规则：①先确认目标页面既有风格（选项式 vs `<script setup>`），不强行政造老页面；②skill 与本项目约定冲突时**项目约定优先**（如 {{本项目特有约定举例}}）；③skill 未安装则按既有代码风格实现，不为此新装依赖。

## 代码约定速记

<!-- FILL: 按项目实际写 6~12 条；以下为常见维度清单，每条必须有代码证据（文件路径），探索阶段收集 -->
- **新需求一律 TDD**：先写失败单测 → 实现 → 测试绿 → 重构。{{存量测试现状：已有测试则写怎么跑；无测试则注明首个 TDD 任务先补测试依赖}}；验证与跑测见 [dev-environment.md](docs/dev-environment.md)
- **{{语言/编译约束}}**：{{如 JDK 8 强制、Node 版本、编译必带 -am 等}}
- **{{数据库方言约束（如有）}}**：{{如信创达梦——禁止 PG 专属语法}}
- **{{分层约定}}**：{{Service interface+impl / 包结构 / Mapper XML 位置}}
- **{{实体约定}}**：{{基类 / 主键策略 / 返回包装}}
- **{{已知技术债}}**：{{如分页双栈、重复实体等——标注"不要混用/先确认目标份"}}
- **{{租户/权限过滤约定}}**
- **{{前端两代风格并存（如有）}}**
<!-- FILL: 仅 SLW 项目保留 -->
- 低代码页面生成走项目内置 skill `lowcode-page-gen`（`skills/lowcode-page-gen/`，见上），SQL 留档文件名已是日期+中文格式
- 详见 [CODE_WIKI 第 8 章](docs/CODE_WIKI.md#8-开发约定与规范)

## Agent skills

### Issue tracker

Issue 以本地 markdown 文件形式跟踪，存放在 `.scratch/` 下。见 `docs/agents/issue-tracker.md`。

**验收项打勾强制**：票面验收项实现完成的当场把 `- [ ]` 改 `- [x]`、整票完成改 `Status: done`（留手测的改 `ready-for-human`），不攒批。细则见 issue-tracker.md「验收项打勾与状态同步」。

**命名规范强制**：ADR/spec/ticket 的 .md 文件名**日期开头 + 中文**，spec 目录名同；SQL 归档文件同（见上文「文档与工单命名规范」）。

### Triage labels

使用五个默认 triage 标签（needs-triage、needs-info、ready-for-agent、ready-for-human、wontfix）。见 `docs/agents/triage-labels.md`。

### Domain docs

Single-context 布局：仓库根目录一个 `GLOSSARY.md` + `docs/adr/`（ADR 文件名日期开头 + 中文）。见 `docs/agents/domain.md`。
