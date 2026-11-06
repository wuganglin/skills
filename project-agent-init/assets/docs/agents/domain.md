# 领域文档（Domain Docs）

工程 skills 在探索代码库时应如何消费本仓库的领域文档。

## 探索之前，先阅读

- 仓库根目录的 **`GLOSSARY.md`**（领域术语表：低代码配置域 + 能源/设备/生产/集成域）
- **`docs/adr/`** — 阅读与你要工作的区域相关的 ADR。文件名规范：`YYYYMMDD-<中文标题>.md`

如果这些文件不存在，**静默继续**。不要标记它们的缺失；不要建议预先创建。`/domain-modeling` skill（经由 `/grill-with-docs` 和 `/improve-codebase-architecture`）会在术语或决策实际得到解决时按需创建。

## 文件结构

Single-context（本仓库采用此布局）：

```
/
├── GLOSSARY.md
├── docs/
│   ├── adr/
│   │   └── 20261027-低代码插库决策.md   ← 日期开头 + 中文标题
│   ├── CODE_WIKI.md
│   ├── business-architecture.md
│   └── lowcode-config.md
└── service/ web/
```

## 使用术语表的词汇

当你的输出命名一个领域概念（issue 标题、重构提案、假设、测试名）时，使用 `GLOSSARY.md` 中定义的术语。不要漂移到术语表明确避免的同义词。

如果你需要的概念还不在术语表里，这是一个信号：要么你在发明项目不用的语言（重新考虑），要么存在真实缺口（记下来给 `/domain-modeling`）。

## 标记 ADR 冲突

如果你的输出与既有 ADR 矛盾，显式暴露而不是静默覆盖：

> _与 20261027-低代码插库决策.md 矛盾，但值得重开，因为…_
