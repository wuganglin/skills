***

name: "lowcode-page-gen"
description: "从表结构示意（字段清单/DDL/Markdown表格）直插数据库生成低代码页面闭环：建PG表→数据选项→数据源→窗口(含主子表/自定义按钮)→菜单→admin授权；也支持对既有窗口/数据源做增量变更（加字段/改中文名/调显隐/加删查询与按钮，自然语言即可启动）。可选生成后端 Java 四件套骨架（默认不生成，仅用户明确要求时出 Controller/Mapper/Entity/Service 且不含方法实现）。当用户要求生成业务页面、配置化管理页面、父子表关联页面、快速建CRUD菜单，或改动现有低代码页面时调用。"
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# 低代码页面直插生成（lowcode-page-gen）

把用户的表结构示意变成 admin 可用的低代码页面，或对**既有**窗口/数据源做增量变更。**不走后台 UI**，用本 skill 自带脚本 `scripts/lowcode_seed.py`（相对 skill 目录）直插配置表（dev 库实时查库无缓存，插完即生效）。

**决策依据**：当前项目 `docs/adr/` 下的「低代码插库」ADR（若有）；表关系原理：当前项目 `docs/lowcode-config.md` 第 5 章（SLW/core-window 平台通用文档）。

**通用性说明**：本 skill 随仓库分发，是**项目共有资产**（本项目位于 `skills/lowcode-page-gen/`，AGENTS.md 有索引），适用于所有 SLW 低代码平台（core-window / slw 前端运行时）的同框架项目——其他同框架项目可整体复制本目录。数据库连接、Admin 角色 id、「是否」数据选项 id 均随项目而异：连接用 `--dsn` 或环境变量 `LOWCODE_PG_DSN` 传入（从当前项目后端 `application-dev.yml` 数据源配置换算）；Admin 角色与「是否」选项由脚本运行时按名称查库解析。

**⚠️ 数据库方言警告**：脚本生成的业务表 DDL 与配置 INSERT 是 **PostgreSQL 方言**（如 `'Y'::bpchar` 类型转换、`now()` 等），且 psycopg2 只能连 PG。**若目标库非 PostgreSQL（如信创达梦 DM8、人大金仓等）**：脚本无法直连，使用路径为 `--dry-run` 生成 SQL → **人工转译为目标库方言**（重点改 `'Y'::bpchar`→`'Y'`、核对 `now()`/`timestamp(6)` 等语法）→ 留档 `docs/sql/` 后人工执行。目标库为 PG 时可直插。**执行前先查当前项目后端 yml 确认数据库类型**。

## 路由：新建 vs 变更

- 用户给**表结构示意**要新页面 → 走下方【新建流程】

- 用户要**改既有对象**（"给 XX 窗口加个字段/查询/按钮"、"把 XX 改名"、"XX 不在表格里显示"）→ 跳转【变更流程】

## 新建流程（六步，2/4 步必须停下等用户确认）

### 第 1 步：解析输入

支持三种输入，统一解析为字段清单（字段名/中文名/类型/选项/必填/唯一）：

- **中文字段清单**（口述式）：解析成「字段名/中文名/类型/选项/必填/唯一」清单

- **DDL**：直接读 CREATE TABLE

- **Markdown 表格**：按列映射

类型映射（PG 类型 → 数据源 data\_type）：varchar/text→STRING、数值→DOUBLE/LONG、timestamp→DATETIME、date→DATE、char(1)→LIST（配「是否」）、TEXT 长文本→TEXT。
字段名一律 lower\_snake\_case。**主键由工具自动生成：`<表名>_id varchar(32) PRIMARY KEY`，值由低代码框架保存时自动生成 32 位大写 UUID（勿加 DB default，`gen_random_uuid()`** **带 36 位横线与框架格式不一致）**。审计七件套同样自动加，**不要**让用户列。

### 第 2 步：英文化确认（必须停下）

向用户展示解析结果并确认：**表名、每个字段英文名、模块归属（WMS/WCS/MES/MANU/EAM/QC/USER/REPORT/KANBAN/EMS/0=系统模块，默认值取当前项目主业务模块，本项目为 EMS）、菜单挂载父级**（必填，不指定则问；顶层分组 parent\_id='0'，按项目实际菜单分组）。用户点头才继续。

### 第 3 步：生成配置 JSON

写到 `.scratch/lowcode-seed/<对象名>.json`，schema：

```json
{
  "meta": {"module": "WMS", "env": "dev"},
  "tables": [
    {"name": "mes_xxx", "cn_name": "对象中文", "create": true,
     "columns": [
       {"name": "code", "cn": "编码", "pg": "varchar(50) not null", "ds_type": "STRING", "unique": true, "not_null": true},
       {"name": "status", "cn": "状态", "pg": "varchar(20)", "ds_type": "LIST",
        "selector": {"name": "对象-状态", "values": [{"value": "待处理", "name": "待处理"}]}},
       {"name": "eam_equipment_id", "cn": "机台", "pg": "varchar(32)", "ds_type": "TABLE",
        "selector": {"name": "机台(对象)", "table": "eam_equipment", "key": "eam_equipment_id", "name_col": "name"}},
       {"name": "is_valid", "cn": "是否有效", "pg": "char(1) default 'N'", "ds_type": "LIST", "selector": {"reuse": "是否"}}
     ]}
  ],
  "window": {"name": "对象管理", "regions": [
    {"code": "t1", "cn": "对象", "table": "mes_xxx", "type": "GRID", "page_size": 15,
     "orderby": "created desc", "queries": [{"col": "code", "cn": "编码", "type": "LIKE"}],
     "buttons": ["NEW", "EDIT", "DELETE"],
     "custom_buttons": [{"code": "DONE", "cn": "完成", "click_function": "..."}]},
    {"code": "t2", "cn": "明细", "table": "mes_xxx_detail", "parent": "t1", "type": "GRID",
     "buttons": ["NEW", "EDIT", "DELETE"]}
  ]},
  "menu": {"name": "对象管理", "group": {"name": "Agent生成", "create": false}, "parent_id": null, "seq": 999}
}
```

规则：

- **主子表**：子表 FK 列（指向父表主键 `父表名_id`）必须出现在 columns 里并标 `"fk": true`；数据源字段照常生成（含父表 id），区域字段也生成但**不勾选表单/表格显示**；子区域配 `"parent": "t1"` 即完成联动，**零脚本零 where\_clause**（平台惯例）

- **区域字段覆盖全部列**（与后台「生成字段」/存量惯例一致）：主键、业务列、FK 列、审计列全部生成区域字段；**业务列勾选"在表单/表格中显示"，主键与关联 id 字段及审计列不勾选**；隐藏的 isactive 区域字段 default\_value='Y'。工具自动处理，JSON 无需表达

- **数据选项命名**（Q9）：通用选项（是否/正常不正常等）不加前缀；业务独家选项用完整路径明确归属（如 `料卷退库单-退库原因`）

- **Y/N 字段**：ds\_type=LIST + `{"reuse": "是否"}`（复用系统选项，勿新建）

- **菜单**：`parent_id`（挂既有分组）或 `group.create=true`（新建分组），二者必有其一

- **click\_function**：可用 `getRegion('编码')`、`ElMessage/ElMessageBox`、`$vxeMessage/$vxeConfirm`、`axios`；表格取选中行 `getRegion('t1').getSelectRecord()`，须判空

### 第 4 步：自定义按钮与 Java 骨架（可选，默认关闭）

**后端 Java 代码默认不生成**——本 skill 的默认产物只有低代码配置闭环。仅当用户明确要求"生成后端 Java / 四件套 / 骨架代码"时才生成，且**只出骨架、不含任何方法实现**（方法体由用户自行补充，skill 不代写业务逻辑）。

**按钮需要调后台接口时**（用户提到"调后台定制化接口"而未给结构），先按下面提问（Q15 结构化格式优先，必须停下）：

```
按钮：下发生产 | 确认弹窗：是 | 成功后：刷新表格
  接口：POST /productionTask/dispatch
  传参：选中行 id 列表 + 表单字段 xxx
  返回：{result: true, msg: "..."}
```

拿到答案后：

- 按钮脚本照常写 `axios.post('/<url>', qs.stringify({...}))`（url 为后端 Controller 路径），成功后 `getRegion('t1').reload()`

- 接口结构仅作前后端契约约定；**Java 骨架仍需用户明确点头才生成**，未点头就只交付按钮脚本

**用户明确要求生成 Java 时**，按存量实体模板出四件套骨架（模块分层随项目而异，按当前项目 AGENTS.md 的分层约定落位，本项目为 `api-<域>` 模块内 controller/service/mapper/entity 分层；URL 前缀 = 表名，须在第 2 步确认时一并让用户点头）：

- **Entity**：完整字段结构——`@Data @ToString @NoArgsConstructor @AllArgsConstructor` 继承 `BaseModel<实体>`，`@TableId(value = "<表名>_id", type = IdType.ASSIGN_UUID)`，业务字段 + 中文注释（审计字段 BaseModel 已含，勿重复声明）。字段类型规范：

  - **日期/时间**一律 `java.sql.Timestamp` 或 `Date`（参照存量实体）

  - **数值优先** **`BigDecimal`**；仅当语义明确是整数（个数、数量、排序号 seq）时用 `Long` 或 `Integer`

  - **主子表关联用** **`@TableField(exist = false)`** **+** **`List<子实体>`**（框架惯例，**不用 @BindEntity**）；常量内联在实体里（如 `<实体名>.ORDER_TYPE_XXX`）

- **Mapper**：空接口 `@Mapper extends BaseMapper<实体>`

- **Service**：**interface + impl 两层**（框架惯例）：`<实体名>Service` 接口 + `impl/<实体名>ServiceImpl implements <实体名>Service`，**不写任何业务方法**

- **Controller**：类壳 `@RestController @RequestMapping("/<表名>") @AllArgsConstructor` + 注入 Service，**不写任何接口方法**

- 空方法/空类处留 `// TODO 业务实现由使用方自行补充` 注释

- 写完在项目根跑 `mvn compile -pl <主模块> -am -q -DskipTests` 验证编译（**Java 8 项目**：本地默认 JDK 过高时 Lombok 注解处理失效会产生无关文件假错误，必要时 `JAVA_HOME` 指向 JDK 8）

### 第 5 步：执行

```bash
# <skill目录> = 本 SKILL.md 所在目录（本项目即 skills/lowcode-page-gen），按实际加载路径解析为绝对路径后执行
python3 <skill目录>/scripts/lowcode_seed.py --config .scratch/lowcode-seed/<对象名>.json --dsn "host=... port=... dbname=... user=... password=..." --out docs/sql
```

- `--config`/`--out` 是**项目根**相对路径（工作目录 = 项目根）；脚本本身用 skill 目录相对路径定位

- `--dsn` 指定目标库（或环境变量 `LOWCODE_PG_DSN`）：从当前项目后端 `application-dev.yml` 数据源配置换算；事务执行 + SQL 级核验，失败自动回滚。**目标库非 PostgreSQL 时脚本无法直连**——按上方「数据库方言警告」走 dry-run + 人工转译路径

- 同名冲突默认报错；用户明说"重建"才加 `--rebuild`

- 正式产物留档 `docs/sql/YYYYMMDD-HHMMSS-<对象名>-seed.sql` + `-seed-reverse.sql`（反向清理；**回滚必须用当次生成的版本**，id 随机、重跑生成的文件不配对）

- 非 dev 环境或 `--dry-run`：只生成 SQL 文件不执行（prod 永远只出文件，人工执行）

### 第 6 步：交付报告

必须包含：

1. 表/数据源/窗口/菜单/按钮清单 + 核验结果（工具自动输出）
2. **提醒：admin 需重新登录**（窗口/按钮授权是登录时 Redis 快照，菜单授权即刷即见）
3. 反向清理 SQL 路径（回滚入口）
4. 若生成了 Java 骨架：编译结果 + 重启后端提醒（新接口需重启 mes 才生效）+ **明确告知骨架不含方法实现，由用户自行补充**
5. 页面验证待办：让用户登录点开页面确认（尤其主子表联动、自定义按钮）

## 变更流程（对既有窗口/数据源做改动，四步，第 2 步必须停下）

`lowcode_seed.py` 变更模式（JSON 顶层 `"mode": "change"`）：连库定位既有对象 ids + 记录旧值，事务执行增量 SQL + 断言核验，输出正向/反向 SQL 留档（`<时间戳>-<窗口名>-change.sql` / `-change-reverse.sql`）。

### 第 1 步：查库反解现状

用户自然语言描述变更后，先连 dev 库把目标对象现状查出来（psql，模板）：

```sql
-- 窗口 → 区域 → 数据源
SELECT w.name AS 窗口, r.code AS 区域, r.type, ds.name AS 数据源, ds.table_name AS 表名
FROM sys_window w JOIN sys_window_region r ON r.sys_window_id=w.sys_window_id
JOIN sys_datasource ds ON ds.sys_datasource_id=r.sys_datasource_id
WHERE w.name='<窗口名>';

-- 区域字段（列名/中文名/显隐/顺序）
SELECT c.column_name, f.name, f.seq, f.display_form, f.display_grid, f.not_null, f.is_unique
FROM sys_window_region_field f
JOIN sys_datasource_column c ON c.sys_datasource_column_id=f.sys_datasource_column_id
WHERE f.sys_window_region_id='<区域id>' ORDER BY f.seq NULLS LAST;

-- 区域按钮 / 查询条件
SELECT code, name, type, seq FROM sys_window_button WHERE sys_window_region_id='<区域id>' ORDER BY seq;
SELECT q.name, c.column_name, q.type, q.data_type FROM sys_window_region_query q
JOIN sys_datasource_column c ON c.sys_datasource_column_id=q.sys_datasource_column_id
WHERE q.sys_window_region_id='<区域id>' ORDER BY q.seq;
```

### 第 2 步：现状 + 变更计划确认（必须停下）

向用户展示查到的现状 + 拟执行的变更清单（op 级别），用户点头才继续。字段名/区域 code 以库内实际值为准，不要凭记忆猜。

### 第 3 步：生成变更 JSON 并执行

写到 `.scratch/lowcode-seed/<对象名>-change.json`，七种 op：

```json
{
  "meta": {"module": "WMS", "env": "dev"},
  "mode": "change",
  "target": {"window": "对象管理", "table": "mes_xxx"},
  "changes": [
    {"op": "add_column", "name": "weight", "cn": "重量", "pg": "numeric(18,4)", "ds_type": "DOUBLE",
     "not_null": false, "unique": false, "field_default": null,
     "selector": {"reuse": "是否"}, "regions": "all"},
    {"op": "modify_column", "name": "status", "cn": "单据状态", "ds_type": "LIST"},
    {"op": "field_display", "region": "t1", "col": "code", "display_grid": "N", "seq": 50},
    {"op": "add_query", "region": "t1", "col": "created", "cn": "创建时间", "type": "GE"},
    {"op": "remove_query", "region": "t1", "col": "created"},
    {"op": "add_button", "region": "t1", "code": "DONE", "cn": "完成", "click_function": "...", "seq": 40},
    {"op": "remove_button", "region": "t1", "code": "DONE"}
  ]
}
```

规则：

- `target.window`/`target.table` 是全局默认定位，单条 op 可用 `window`/`table` 覆盖

- **add\_column** 三层一次到位（业务表 ALTER + 数据源字段 + 区域字段），`regions: "all"` 给引用该数据源全部区域加，或 `[{"region": "t1", "display_form": "N"}]` 指定；selector 写法同新建

- **modify\_column** 改中文名会联动区域字段 name；`selector` 可换选项

- **field\_display** 支持 display\_form/display\_grid/seq/not\_null/is\_unique/default\_value/name

- **add\_button**：code 为 NEW/EDIT/DELETE 是标准按钮；其他为 EVENT 自定义（必填 click\_function，写法同新建），自动授权系统管理员

- 执行同新建第 5 步：`python3 <skill目录>/scripts/lowcode_seed.py --config <变更json> --out docs/sql`

### 第 4 步：交付报告

1. 变更清单（op 级）+ 断言核验结果（工具自动输出，逐条"实际 vs 期望"）
2. **回滚**：反向 SQL 路径；**必须用本次生成的版本**（id 随机，重新 dry-run 生成的文件与库内数据不配对，执行无效）
3. **涉及按钮/授权的变更：admin 需重新登录**（授权是登录时 Redis 快照）
4. 字段/查询类变更刷新页面即见；提醒用户登录验证

### 变更边界

- **不支持删业务列**（数据丢失风险），确需删除让用户在后台 UI 或手写 SQL 处理

- 改 `where_clause`/`orderby_clause`/事件脚本等区域级属性：脚本未覆盖，走后台 UI 或手写 SQL（表结构见 lowcode-config.md 第 7 章）

## 边界与已知坑

- **子表 FK 自动注入是运行时行为**，SQL 核验覆盖不到；页面首验重点看子表新增是否正确带出主表 id

- SQL 型数据源（本工具只做 TABLE 型）如手写，必须含 `[accessLevel]` 占位否则无租户过滤（**当前项目若已设置 `system.close-client-filter: true` 关闭租户过滤，则可不写**——以前端项目 AGENTS.md/后端 yml 为准）

- `ad_role_window` 授权固定给系统管理员角色；业务角色授权是上线动作，让用户自己在后台配

- 按钮行不写 sys\_window\_id（多区域同名按钮依赖 NULL 绕过唯一约束，勿"修复"）

- `sys_connection` 跨库多数项目未启用（仅 1 条模板记录），数据源 `sys_connection_id` 留空走主库（以当前项目库内实测为准）

- 单号字段：若业务表有单号列（如 xxx\_no），先查 `sys_code_rules` 是否已有 `(table_name, column_name)` 规则；无则提醒用户补配或用 default\_value=`@SQL=select ...` 兜底（机制见 lowcode-config.md 8.8）。**core-window 4.x 注意**：编码规则分段**不支持 SQL 型分段**（仅 SELF/日期/PARAM/ORG/XL 等），配规则时勿选 SQL 段；`@SQL=` 默认值兜底仍是有效语法
- **core-window 4.x 版本差异**：本 skill 所用的表/列在 4.x 全部兼容（已对照主线源码核对，脚本无需改）；过时表结构与语义差异见 lowcode-config.md 头部「4.0.0 勘误表」。首次对目标库执行前建议 `\d` 抽查 sys_window_region / sys_code_sequence / sys_selector_data 三表物理列

