# Issue 跟踪：本地 Markdown

本仓库的 issue 和 spec 以 markdown 文件形式存放在 `.scratch/` 下。

## 约定

- 每个 feature 一个目录：`.scratch/<日期-中文标题>/`（如 `.scratch/20261027-能耗报表优化/`），**目录名以日期开头、用中文**
- spec 文件为 `.scratch/<日期-中文标题>/spec.md`
- 实现 issue 一个 ticket 一个文件，位于 `.scratch/<日期-中文标题>/issues/` 下，**文件名同样日期开头 + 中文**（如 `20261027-抄表结果查询优化.md`）——不再使用 `NN-<slug>.md` 英文编号风格
- triage 状态记录在每个 issue 文件顶部附近的 `Status:` 行（角色字符串见 `triage-labels.md`）
- 评论和对话历史追加到文件底部的 `## Comments` 标题下

## 命名规范（强制）

**所有 ADR / spec / ticket 的 `.md` 文件名以日期开头（YYYYMMDD），文件名用中文**；spec 的**目录名**同样日期开头 + 中文；**SQL 归档文件**（docs/sql/ 下）同样日期开头 + 中文对象名。示例：

```
docs/adr/20261027-低代码插库决策.md
.scratch/20261027-能耗报表优化/spec.md
.scratch/20261027-能耗报表优化/issues/20261027-抄表结果查询优化.md
docs/sql/20261027-153000-对象管理-seed.sql
```

## 验收项打勾与状态同步（强制）

票面验收清单的 checkbox 和 Status 行是票据的唯一事实来源，**实施完成时必须当场同步，不攒批、不留到收官后补**：

- 某个 `- [ ]` 验收项已实现并通过票面指定验证（单测绿/编译过/代码落地）→ 当场改为 `- [x]`；Comments 追加一条实施记录（日期、改动落点、测试结果）
- 整票验收项全部勾完 → `Status:` 改为 `done`（可带括号注释：日期/留工作区未提交等）
- 实施完成但有验收项依赖用户浏览器手测/现场联调/真机验证 → 已完成的项照勾，`Status:` 改为 `ready-for-human`，括号注明待验内容
- 验收项依赖生产部署后才能做 → 该项保持未勾，`Status:` 用 `done` 并在括号里注明"XX 项留部署后补验"
- 放弃/不做某验收项 → 保持未勾并在 Comments 说明裁决，不得静默打勾

## 当 skill 说"发布到 issue tracker"时

在 `.scratch/<日期-中文标题>/` 下创建新文件（必要时先创建目录）。

## 当 skill 说"获取相关 ticket"时

读取引用路径处的文件。用户通常会直接传入路径或 issue 主题。

## Wayfinding 操作

供 `/wayfinder` 使用。**map** 是一个文件，每个 ticket 对应一个 **child** 文件。

- **Map**：`.scratch/<effort>/map.md` — 包含 Notes / Decisions-so-far / Fog 正文。
- **Child ticket**：`.scratch/<effort>/issues/` 下，文件名日期开头 + 中文，正文包含问题。`Type:` 行记录 ticket 类型（`research`/`prototype`/`grilling`/`task`）；`Status:` 行记录 `claimed`/`resolved`。
- **Blocking**：文件顶部附近的 `Blocked by: <文件名>` 行。当其列出的每个文件都 `resolved` 时，该 ticket 解除阻塞。
- **Frontier**：扫描 `.scratch/<effort>/issues/` 中 open、unblocked 且 unclaimed 的文件；日期最早者优先。
- **Claim**：在任何工作开始前，设置 `Status: claimed` 并保存。
- **Resolve**：在 `## Answer` 标题下追加答案，设置 `Status: resolved`，然后向 `map.md` 的 Decisions-so-far 追加上下文指针（要点 + 链接）。
