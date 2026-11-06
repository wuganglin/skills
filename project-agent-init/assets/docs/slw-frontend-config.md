# SLW 低代码前端配置速查

> 📌 **本项目适用性注记（{{项目名}}，{{YYYY-MM-DD}} 由 project-agent-init 安装，安装后须按实际改写）**：SLW 前端运行时平台通用。本项目前端为 `slw {{版本}}`（预发布 rc 版注意文中「预发布版方法/已移除」标注正是 rc 轨道），装载点在 {{前端工程的 main.js}}，窗口页 {{windowIndex.vue 路径}}；构建 base 为 {{'/' 或自定义上下文}}。
>
> 来源：官方文档站 [slwdoc](http://slwdoc.js.sforcecon.com:5900/)（ANYHAI 窗口配置插件开发指引，VitePress），经项目实测核对。
> 定位：写低代码**事件脚本 / 占位符 / 运行时 API** 时的速查表。表结构与后端执行语义见 [lowcode-config.md](lowcode-config.md)。

***

## 1. 平台定位与版本

- SLW = **动态页面生成组件库**：后端配置(JSON) → 前端动态渲染 → 表格/表单/图表完整页面，无需硬编码

- 技术栈：Vue 3 + VXE-PC-UI + Element Plus；npm 包 `slw`（PC 端）、`yh-mobile-renderer`（APP 端）

- **版本双轨**：旧版 0.10.x 与预发布版 1.0.0-rc.x 的 API 有差异（文档多处标注"预发布版方法/已移除"）——**项目中途禁止切换版本**

- 本项目用法：`web/src/main.js` 的 `app.use(SLW, {...})` 装载运行时（web/ 为前端 Vue3 工程，Vite + pnpm）；窗口页 `web/src/layout/window/windowIndex.vue`

## 2. 配置化操作闭环（管理后台操作视角）

在窗口管理页面新增一个完整窗口的流程（与 [lowcode-config.md 第 5.2 节](lowcode-config.md) 的表关系对应）：

1. **新增窗口**：窗口名称（= 菜单显示名）、布局（垂直/水平/页签）、所属模块、访问级别
2. **新增布局**：名称、布局方式、排序
3. **新增区域**：编码、名称、访问级别（标准/只读/只写）、**类型**（表单/表格/树形结构/外部链接）、**数据源**（须先在数据源管理配置）、所属布局
4. **生成字段**：勾选区域 → 系统按数据源字段自动生成
5. **修改字段名称**：改中文显示名（支持自动保存 + 左右切换批量改）
6. **新增字段三步闭环**：**库表加字段 → 数据源管理加字段 → 窗口里"引用字段"**（引用字段是数据源字段的映射）
7. **新增查询条件**：名称、数据源字段、数据类型、查询方式
8. **新增按钮**：类型、编码（如 EDIT\_DESIGNER）、名称、排序、显示到表格
9. **预览**

树形场景：数据源勾选"树形结构配置" + 设置树形父 ID 字段。

> 自动化插库已固化为 skill：`.trae/skills/lowcode-page-gen/SKILL.md`（新建/变更模式，见 ADR 0003）。

## 3. 事件配置与脚本签名

脚本写在\*\*区域（数据初始化前 / 数据初始化 / 页面初始化）\*\*及字段/按钮/查询条件各自的事件配置框内。

### 3.1 基础事件签名

| 事件            | 参数                                                            |
| ------------- | ------------------------------------------------------------- |
| 数据初始化 / 页面初始化 | `()`                                                          |
| 提交前触发         | `(formData)`                                                  |
| 提交后触发         | `(formData, responseData)`                                    |
| 表格行点击         | `(row)`                                                       |
| 按钮点击（表格）      | `(data, btn)` — data 为高亮/多选行                                  |
| 按钮点击（表单）      | `(formData, btn)`                                             |
| 字段值更改         | 表格 `(value, optionData, field, row)`；表单 `(value, optionData)` |
| 字段回车          | 表格 `(value, field, row)`；表单 `(value)`                         |
| 字段点击 / 字段图标点击 | `(value, field)`                                              |

### 3.2 特殊事件（在"数据初始化前"用 add\*Fun 注册）

| 注册函数                                                 | 时机 / 能力                                                            |
| ---------------------------------------------------- | ------------------------------------------------------------------ |
| `addOnActivatedFun`                                  | 缓存页重新激活                                                            |
| `addEditGridDataChangeFun`                           | 可编辑表格数据变化（收 visibleData/insertRecords/removeRecords/updateRecords） |
| `addProxyQueryBeforeFun`                             | 查询前，**返回 false 阻止查询**                                              |
| `addProxyQueryAfterFun`                              | 查询后，返回 false 不显示                                                   |
| `addAllCheckboxFun` / `addCheckboxFun(row, checked)` | 全选/行勾选                                                             |
| `addRowDragEndFun`                                   | 行拖拽结束，返回 false 禁止拖拽                                                |
| `setBeforeEditMethod`                                | 行编辑前，返回 false 禁止编辑                                                 |

## 4. 脚本可用上下文

| 变量                                                                      | 说明                                                                                          |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `gridData.value`                                                        | 区域元数据：type=GRID/EDIT\_GRID/FORM/TREE、openType=new/edit、params.code、noSearchData、queryParams |
| `formConfig.value`                                                      | 表单配置：columns、itemRender.props                                                               |
| `$externalFun`                                                          | main.js externalFun 注入的全局方法（calc/lodash/prompt…）                                            |
| `axios`                                                                 | HTTP 客户端（含 download/export）                                                                 |
| `router` / `route`                                                      | 路由                                                                                          |
| `ElMessageBox` / `ElMessage` / `$Modal` / `$vxeMessage` / `$vxeConfirm` | 消息与确认框                                                                                      |
| `nextTick` / `ref` / `inject`                                           | Vue 能力                                                                                      |
| `formLoading` / `toggleModalLoading`                                    | 加载状态                                                                                        |
| `evalEvent`                                                             | 事件求值                                                                                        |
| `localStorage`                                                          | 本地存储（userName）                                                                              |
| `window.pda.scan()`                                                     | PDA 扫码                                                                                      |

## 5. 运行时 API

### 5.1 通用（14 个）

| 方法                                      | 用途                                |
| --------------------------------------- | --------------------------------- |
| `getRegion(编码)`                         | **跨区域取对象（最常用）**；返回 undefined 时先判空 |
| `getParentRegion`                       | 取父区域                              |
| `showPreView(windowId, name, 查询参数, 配置)` | 打开配置窗口弹窗                          |
| `showModal` / `openDrawer`              | 打开自定义 vue 页面弹窗/抽屉                 |
| `closeModal`                            | 关闭弹窗                              |
| `toggleLayoutDisplay(布局ID, 'none')`     | 切换布局显隐                            |
| `isActivatedFun`                        | 页面激活判断                            |

### 5.2 表单方法（26 个，常用子集）

| 方法                                                                                                   | 用途           |
| ---------------------------------------------------------------------------------------------------- | ------------ |
| `getData` / `setValue` / `setData` / `getValue`                                                      | 表单数据读写       |
| `submitData` / `checkSubmitData`                                                                     | 提交 / 校验      |
| `resetForm` / `clearData`                                                                            | 重置 / 清空      |
| `setFormItemProperty(field, 'disabled'\|'readonly'\|'notNull'\|'suffixIconfont'\|'iconClickFun', v)` | 动态改字段属性      |
| `displayFormItem(field, 'none')`                                                                     | 字段显隐         |
| `setFormSelectOption`                                                                                | 设置下拉选项       |
| `getTableFieldSelectData`                                                                            | 取表/列表型字段下拉数据 |
| `setFieldElement`                                                                                    | 更换渲染组件       |
| `setFormGroup` / `addExtraFormItem`                                                                  | 分组 / 追加字段    |
| `setFormSlotsVuePath(vuePath, 'form_bottom'\|'form_item_title')`                                     | 插槽挂自定义 vue   |

### 5.3 表格方法（58 个，常用子集）

| 类别   | 方法                                                                                                                                      |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 数据   | `getData` / `getSelectRecord` / `getCheckedData` / `insert` / `removeRow` / `setRow` / `setChecked` / `reload` / `resetGrid` / `search` |
| 查询条件 | `setFormValue` / `getQueryForm` / `setQueryFormItemDisplay` / `setQueryEvent` / `setQueryFieldChangeFun`                                |
| 导入导出 | `exportData` / `exportCurrentData` / `setImportUrl` / `setDownTemplateUrl` / `footerSum`                                                |
| 样式   | `setCellStyle` / `setRowCellColor` / `setSpanMethod`                                                                                    |
| 扩展   | `setGridSlotsVuePath`（插槽挂自定义 vue）/ `setColumnElement` / `setGridBasicConfig` / `setButtonDisplay`                                       |

### 5.4 图表方法（6 个）

`loadEchart` / `refreshEchart` / `setEchartOption` / `getEchartOption` / `resize` / `clear` —— **勿在初始化方法中调用**（实例尚未创建）。

## 6. 占位符语法（default\_value / display\_logic / notnull\_logic）

| 占位符                      | 含义                  |
| ------------------------ | ------------------- |
| `@field@`                | 本表字段 / url 传参       |
| `@params.x@`             | url 传参              |
| `@parent.field@`         | 父表（主表）字段 —— 主子表联动查询 |
| `@userId@`               | 当前用户                |
| `now()-1D` \| `now()`    | 日期（支持 ±D/M/H/MI 偏移） |
| `@_CHILDS@=='undefined'` | 树根节点判断（根节点按钮显示逻辑）   |

后端解析的更强语法（`@CODE@` 自动编码、`@SQL=select ...`、`@orgId@` 等）见 [lowcode-config.md 6.2 节](lowcode-config.md)——注意区分前端占位符与后端默认值语法。

## 7. 字段/按钮配置项要点

- **字段**：名称、引用字段、排序、宽度（24 栅格，默认 12）、默认值、非空逻辑、事件（值更改/回车/点击/图标点击）、支持扫码

- **按钮**：显示逻辑（占位符同上）、样式（直接写 css）、图标网址

- **DOM id 约定**（脚本操作 DOM 时）：字段 = 引用字段大写（如 `NAME`）、查询条件 = `query-name`、插槽 = `插槽名_区域编码`、编辑弹窗区域 = `Edit-区域编码-WindowId`

## 8. 设计器（可视化拖拽）

- 三区布局：左组件库 / 中画布（撤销、恢复、预览、保存、清空）/ 右配置面板（窗口信息/组件设置/列属性三标签）

- 层级：**容器（垂直/水平/页签）⊃ 高级组件（表格/表单/树形表格/可编辑表格/树形结构）⊃ 基础字段**；基础字段只能拖进高级组件

- 列属性可"新增"列或"**生成字段**"（按组件选中的数据源生成，生成后需手动编辑字段配置才展示）

- 表格加查询条件自动带"查询/重置"按钮；删光查询条件自动删按钮；操作按钮只能放标题旁

- 启用方式：窗口配置中加 类型=事件、编码=`EDIT_DESIGNER` 的按钮

- 部分配置项带自动补全的代码编辑器

## 9. 集成方式

```js
// main.js
app.use(SLW, { axios, httpHeaders, VXETableConfig, externalFun, otherComponents })
```

```vue
<!-- 自定义页面内嵌窗口 -->
<slw-window-index :window-id="id" :query-params="params" :execute-fun="fn" />
```

APP 端：菜单 `menuType=='APP'` 动态路由 + `yh-renderer-index` 渲染（本项目 PDA 未使用，全手写）。

## 10. FAQ 速记

- `getRegion` 返回 undefined：编码错 / 区域未初始化 / 对 FORM 区域调表格方法 → 调用须加空值判断，且在页面初始化/按钮点击/行点击等安全时机调用

- 预发布版与旧版 API 混用报错 → 确认项目 slw 版本后只查对应版本文档段落

- 生成字段后表格不显示 → 需手动编辑字段配置（display\_grid）后才展示

## 11. 平台补充（2026-09-04 文档站核对增补）

- **APP 端**（yh-mobile-renderer，Vue3 + Vant 4）：菜单 `menuType=='APP'`、路由 `/appView/:id`、26+ 个 Ymr 组件（list/table/form/button/calendar/cascader/checkbox/datePicker/fileUploader/navBar/radio/rate/stepper/switch/tabbar/tabs/textarea/timePicker/treeSelect…），APP 事件同 PC 基础 11 + 特殊 4 个，通用方法 6 个；WEB 端窗口管理可导入"PDA页面配置"XML。示例库 sys\_app\_design 未启用、菜单无 APP 型记录——PDA 需求示例环境走手写页（menu\_type=LINK）。

- **页面设计器**（designer 章节）：拖拽式可视化配置窗口，组件层级 **容器（垂直/水平/页签）> 高级组件（表格/表单/树形表格/可编辑表格/树形结构）> 基础字段**（基础字段只能拖进高级组件）；右侧三面板：窗口信息/组件设置/列属性（新增、生成字段）；通过窗口配"设计"按钮启用（按钮 type=EVENT、code=`EDIT_DESIGNER`）；编辑弹窗区域命名规则 `Edit-区域编码-WindowId`。

- **后端接口约定**：导出 `POST /window/export?data=base64({_button_id, _region_id, parentRowId})`；文件 `POST /dataFile/upload|inline|list|delete`（MinIO，sys\_data\_file 记录）；Excel 导入 URL 可自定义。

- **特殊事件注册**（`addXxxFun`，部分返回 false 可拦截）：`addOnActivatedFun`（页面缓存重激活）、`addEditGridDataChangeFun`（可编辑表格数据更改）、`addProxyQueryBeforeFun/AfterFun`（表格查询前/后）、`addAllCheckboxFun/addCheckboxFun`（全选/勾选）、`addRowDragEndFun`（行拖拽结束）、`setBeforeEditMethod`（行激活编辑前）。

- **内建对象**：`gridData`（type: GRID/EDIT\_GRID/FORM/TREE/TREE\_STRUCTURE；openType: new/edit；params.code 区域编码）、`formConfig`、`$clientStore`（yh-client 库，取 userName/userId）。

