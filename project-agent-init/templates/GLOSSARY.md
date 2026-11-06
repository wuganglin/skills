# {{项目名}}（{{项目中文全称}}）

{{项目一句话定位：业务域 + 技术形态（低代码底座承载 X，手写 Y）}}。

## Language

<!-- FILL: GLOSSARY 是"领域语言"的唯一权威。格式：**中文术语（English / 代码名/表名）**: 定义一段 + _Avoid_: 易混淆说法。每个术语必须有代码证据（实体/表/接口名）。业务域术语 15~30 个为宜，来自探索阶段提炼。以下为格式示例，替换为项目实际术语。 -->

### {{业务域 A（示例）}}

**{{核心术语 1（EmsXxx / 表名）}}**:
{{一段定义：它是什么、关键字段/属性、在系统中的角色。}}
_Avoid_: {{易混说法 1}}、{{易混说法 2}}

**{{核心术语 2}}**:
{{定义。}}
_Avoid_: {{...}}

### {{业务域 B（示例）}}

<!-- FILL: 按业务域分组，每组一个 ### 标题 -->

### 集成与部署域（示例）

**{{外部系统/中间件术语}}**:
{{定义与交互方式。}}
_Avoid_: {{...}}

<!-- ============================================================
  以下「低代码配置域」整节仅 SLW 低代码项目保留（已是成品，直接可用；
  非 SLW 项目删除本节）。按项目实际确认：租户过滤开关、菜单路由生成方式。
============================================================ -->

### 低代码配置域（SLW 低代码平台通用）

**窗口（Window / sys_window）**:
一个低代码页面的顶层容器，名称即菜单显示名。一个窗口 = 一个页面。
_Avoid_: 页面、表单页

**区域（Region / sys_window_region）**:
窗口内绑定数据源的渲染区块（GRID/FORM/TREE/EDIT_GRID/LINK），编码是脚本 `getRegion(code)` 的 key。主子表通过 `parent_region_id` 建区域层级。
_Avoid_: 子页面、面板

**数据源（Datasource / sys_datasource）**:
驱动区域 CRUD 的元数据：TABLE 型绑物理表、SQL 型绑手写 SQL。`url` 是 `/window/data/{url}` 的路由（等于表名）。
_Avoid_: 数据连接（那是 sys_connection）

**数据源字段（Datasource Column / sys_datasource_column）**:
数据源返回列的定义（物理列名/中文名/data_type/下拉选项/子查询）。区域字段与查询条件都通过 id 引用它。
_Avoid_: 区域字段（那是 sys_window_region_field，是字段在区域上的展示配置）

**数据选项（Selector / sys_selector）**:
下拉选项来源。LIST 型配 sys_selector_data 静态枚举；TABLE 型从业务表取值。「是否」为全局复用选项（按名称查库解析，id 随库而异）。
_Avoid_: 字典、枚举表

**菜单（Menu / ad_menu）**:
侧边栏入口（注意是 ad_ 前缀不是 sys_menu）。WINDOW 型挂 sys_window_id，点击即开窗口；GROUP 分组、LINK 外链/手写页。
_Avoid_: sys_menu（表名不存在）、路由（路由 url 由登录拉菜单时后端拼出）

**编码规则（Code Rules / sys_code_rules）**:
单号自动生成配置：按 `(table_name, column_name)` 定位，分段组合（日期/序列/自定义/参数），字段 default_value 配 `@CODE@` 触发。
_Avoid_: 序列（单指序列段）

**租户（Client / ad_client）**:
多租户隔离单位，SQL 层由框架拦截器自动注入过滤。**按项目实际改写：本项目租户过滤为 {{已关闭（close-client-filter: true）/ 启用}}**。
_Avoid_: 公司、客户

**组织（Org / ad_org）**:
树形数据范围，决定数据可见范围。
_Avoid_: 部门（组织是数据权限维度，不等于行政组织树）
