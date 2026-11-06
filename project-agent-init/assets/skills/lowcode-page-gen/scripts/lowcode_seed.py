#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
低代码页面配置直插工具（SLW 平台 / core-window，同框架项目通用）

【新建模式】（默认）吃一份配置 JSON，生成并（dev 环境下）执行：
  PG 业务表 DDL → sys_selector(+data) → sys_datasource(+column)
  → sys_window(+layout+region+field+query+button)
  → ad_menu(GROUP/WINDOW) → ad_role_menu/window/window_button 授权
同时输出正向 .sql 与反向清理 .sql 留档。冲突默认报错；--rebuild 才级联删除重建。

【变更模式】（JSON 顶层 mode="change"）对既有窗口/数据源做增量调整：
  add_column / modify_column / field_display / add_query / remove_query
  / add_button / remove_button
  连库定位 ids + 记录旧值，输出增量 .sql 与反向回滚 .sql；事务执行 + 断言核验。
  不支持"删业务列"（数据丢失风险）。

用法（项目根执行；脚本路径 = 本 skill 目录下的 scripts/lowcode_seed.py，按实际加载路径解析）：
  python3 <skill目录>/scripts/lowcode_seed.py --config xx.json [--dsn "<PG DSN>"] [--dry-run] [--rebuild] [--out docs/sql]

数据库连接（按项目而异，不再内置默认值）：
  --dsn "host=... port=... dbname=... user=... password=..." 或环境变量 LOWCODE_PG_DSN；
  DSN 从当前项目后端 application-dev.yml 的数据源配置换算。

决策依据：各项目 docs/adr/ 下「低代码插库」相关 ADR（若有）
"""
import argparse
import datetime
import json
import os
import re
import sys
import uuid

try:
    import psycopg2
except ImportError:
    print("需要 psycopg2: pip3 install psycopg2-binary")
    sys.exit(1)

# ---- 平台常量 ----
# DEV_DSN：不内置连接，由 --dsn 或环境变量 LOWCODE_PG_DSN 提供
DEV_DSN = None
DEFAULT_CLIENT = "0"                                           # ad_client_id 惯例（参照存量配置行，'0' 占绝对主流）
CREATED_BY = "0"                                              # createdby/updatedby 惯例（参照存量配置行）
ADMIN_ROLE = None                                             # 系统管理员 Admin 角色 id：连接后按名称查库解析，失败则要求 meta.role_id 显式传入
ORG_ID = "0"                                                  # 配置行 ad_org_id 惯例
ROOT_MENU = "0"                                               # 根菜单 id

AUDIT_COLS = [  # (列名, 中文名, ds data_type)
    ("ad_org_id", "组织机构", "TABLE"),   # selector 由工具补组织机构选项（留空亦可）
    ("ad_client_id", "租户", "STRING"),
    ("isactive", "有效", "BOOL"),
    ("created", "创建时间", "DATETIME"),
    ("createdby", "创建人", "STRING"),
    ("updated", "更新时间", "DATETIME"),
    ("updatedby", "更新人", "STRING"),
]

STD_BUTTONS = [("NEW", "新增", 10), ("EDIT", "编辑", 20), ("DELETE", "删除", 30)]


def uid():
    return uuid.uuid4().hex.upper()


_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def check_ident(name, what="标识符"):
    """校验表名/列名（用于 SQL interpolate 前的防注入把关，只放行合法标识符）"""
    if not name or not _IDENT_RE.match(str(name)):
        raise SystemExit("[非法 %s] %r（仅允许字母/数字/下划线，且不以数字开头）" % (what, name))
    return name


def safe_slug(slug):
    """清洗留档文件名片段：去掉路径分隔符与特殊字符（窗口名可能含 / 等）"""
    return re.sub(r'[\\/:*?"<>|\s]+', '_', str(slug)).strip('_') or "change"


def check_out_dir(out):
    """校验 SQL 留档目录：禁止路径穿越（.. 段）"""
    parts = str(out).replace("\\", "/").split("/")
    if ".." in parts:
        raise SystemExit("[非法留档目录] %r（不允许包含 ..）" % out)
    return out


def resolve_dsn(cli_dsn):
    """确定数据库连接：命令行 --dsn > 环境变量 LOWCODE_PG_DSN；都没有则报错退出"""
    global DEV_DSN
    DEV_DSN = cli_dsn or os.environ.get("LOWCODE_PG_DSN")
    if not DEV_DSN:
        print("[缺 DSN] 请用 --dsn \"host=... port=... dbname=... user=... password=...\" "
              "或设环境变量 LOWCODE_PG_DSN（从当前项目后端 application-dev.yml 数据源配置换算）")
        sys.exit(1)


def try_resolve_admin_role():
    """连库按名称解析系统管理员角色 id（随库而异，不内置）；失败静默，由 build 阶段兜底报错"""
    global ADMIN_ROLE
    if ADMIN_ROLE or not DEV_DSN:
        return
    try:
        conn = psycopg2.connect(DEV_DSN)
        cur = conn.cursor()
        cur.execute("SELECT ad_role_id FROM ad_role "
                    "WHERE name IN ('Admin', '系统管理员') OR name ILIKE 'admin%%' "
                    "ORDER BY (name = 'Admin') DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row:
            ADMIN_ROLE = row[0]
    except Exception:
        pass


def sql_lit(v):
    """渲染 SQL 字面量（用于 .sql 留档文件）"""
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, datetime.datetime):
        v = v.strftime("%Y-%m-%d %H:%M:%S")
    return "'" + str(v).replace("'", "''") + "'"


class Plan:
    """收集正向 inserts / DDL / 反向 deletes"""

    def __init__(self):
        self.ddl = []        # [(sql, params)]
        self.ins = []        # [(sql, params_dict)]
        self.rev = []        # [sql]（倒序删除）
        self.drop = []       # [drop table sql]

    def add(self, sql, **params):
        self.ins.append((sql, params))

    def rev_delete(self, table, where):
        self.rev.append("DELETE FROM %s WHERE %s;" % (table, where))


def audit_cols(extra=None):
    cols = ["ad_client_id", "ad_org_id", "isactive", "created", "createdby", "updated", "updatedby"]
    vals = ["%(client)s", "%(org)s", "'Y'", "now()", "%(created_by)s", "now()", "%(created_by)s"]
    if extra:
        for k, v in extra.items():
            cols.append(k)
            vals.append(v)
    return ", ".join(cols), ", ".join(vals)


def _meta_of(cfg):
    meta = cfg.get("meta", {})
    return {
        "module": meta.get("module", "WMS"),
        "env": meta.get("env", "dev"),
        "client": meta.get("client_id", DEFAULT_CLIENT),
        "org": meta.get("org_id", ORG_ID),
        "created_by": meta.get("created_by", CREATED_BY),
        "role": meta.get("role_id", ADMIN_ROLE),
    }


def ensure_selector(plan, m, col):
    """列配置里声明了 selector 的：reuse 复用 / list 新建 / table 新建（新建与变更模式共用）"""
    p = plan
    sel = col.get("selector")
    if not sel:
        return None
    if sel.get("reuse"):
        sid = sel.get("id") or _lookup_selector_id(sel["reuse"])
        if not sid:
            raise SystemExit("[冲突] 数据选项「%s」不存在，无法复用" % sel["reuse"])
        return sid
    sid = uid()
    name = sel["name"]
    ac, av = audit_cols()
    if sel.get("table"):  # TABLE 型
        p.add(
            "INSERT INTO sys_selector (sys_selector_id, sys_module_id, %s, name, type, table_name, key_column, name_column, access_level) "
            "VALUES (%%(sid)s, %%(module)s, %s, %%(name)s, 'TABLE', %%(table)s, %%(key)s, %%(name_col)s, 'CLIENT')" % (ac, av),
            sid=sid, name=name, table=sel["table"], key=sel["key"], name_col=sel["name_col"],
            module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
        )
        p.rev_delete("sys_selector", "sys_selector_id = %s" % sql_lit(sid))
    else:  # LIST 型
        p.add(
            "INSERT INTO sys_selector (sys_selector_id, sys_module_id, %s, name, type, access_level) "
            "VALUES (%%(sid)s, %%(module)s, %s, %%(name)s, 'LIST', 'CLIENT')" % (ac, av),
            sid=sid, name=name, module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
        )
        p.rev_delete("sys_selector", "sys_selector_id = %s" % sql_lit(sid))
        for i, v in enumerate(sel.get("values", []), start=1):
            p.add(
                "INSERT INTO sys_selector_data (sys_selector_data_id, sys_selector_id, %s, name, value, seq) "
                "VALUES (%%(did)s, %%(sid)s, %s, %%(name)s, %%(value)s, %%(seq)s)" % (ac, av),
                did=uid(), sid=sid, name=v["name"], value=v["value"], seq=i * 10,
                module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
            )
        p.rev_delete("sys_selector_data", "sys_selector_id = %s" % sql_lit(sid))
    return sid


def build(cfg):
    m = _meta_of(cfg)
    if not m["role"]:
        raise SystemExit("[缺角色] 未能解析系统管理员角色 id（库内无 name='Admin'/'系统管理员' 的 ad_role 行），"
                         "请在配置 meta.role_id 显式传入")
    plan = Plan()
    p = plan

    # ---------- 1. 数据选项 selector ----------
    selector_ids = {}   # key: selector name -> id

    def ensure_selector_build(col):
        sid = ensure_selector(p, m, col)
        if sid and col.get("selector", {}).get("name"):
            selector_ids[col["selector"]["name"]] = sid
        return sid

    # ---------- 2. 业务表 DDL ----------
    for t in cfg.get("tables", []):
        check_ident(t["name"], "表名")
        for c in t["columns"]:
            check_ident(c["name"], "列名")
        if not t.get("create", True):
            continue
        cols = ['    %s_id varchar(32) PRIMARY KEY' % t["name"]]
        for c in t["columns"]:
            cols.append("    %s %s" % (c["name"], c.get("pg", "varchar(200)")))
        cols.append("    ad_client_id varchar(32)")
        cols.append("    ad_org_id varchar(32)")
        cols.append("    isactive char(1) DEFAULT 'Y'::bpchar NOT NULL")
        cols.append("    created timestamp(6) DEFAULT now() NOT NULL")
        cols.append("    createdby varchar(32)")
        cols.append("    updated timestamp(6) DEFAULT now() NOT NULL")
        cols.append("    updatedby varchar(32)")
        ddl = "CREATE TABLE %s (\n%s\n);" % (t["name"], ",\n".join(cols))
        p.ddl.append((ddl, None))
        p.drop.append("DROP TABLE IF EXISTS %s;" % t["name"])

    # ---------- 3. 数据源 + 字段 ----------
    ds_by_table = {}      # table -> ds_id
    col_id_by_key = {}    # (table, column) -> datasource_column_id
    for t in cfg.get("tables", []):
        ds_id = uid()
        ds_by_table[t["name"]] = ds_id
        ds_name = t.get("ds_name", t["cn_name"])
        ac, av = audit_cols()
        p.add(
            "INSERT INTO sys_datasource (sys_datasource_id, sys_module_id, %s, name, url, type, table_name, access_level) "
            "VALUES (%%(ds)s, %%(module)s, %s, %%(name)s, %%(url)s, 'TABLE', %%(table)s, 'CLIENT')" % (ac, av),
            ds=ds_id, name=ds_name, url=t["name"], table=t["name"],
            module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
        )
        p.rev_delete("sys_datasource", "sys_datasource_id = %s" % sql_lit(ds_id))

        all_cols = [(t["name"] + "_id", t["cn_name"] + "ID", "ID", None)] + \
                   [(c["name"], c.get("cn", c["name"]), c.get("ds_type", "STRING"), c) for c in t["columns"]] + \
                   [(a, b, dt, None) for a, b, dt in AUDIT_COLS]
        seq = 10
        for cname, cn, dtype, cconf in all_cols:
            cid = uid()
            col_id_by_key[(t["name"], cname)] = cid
            sel_id = ensure_selector_build(cconf) if cconf else None
            p.add(
                "INSERT INTO sys_datasource_column (sys_datasource_column_id, sys_module_id, sys_datasource_id, %s, column_name, name, data_type, seq, sys_selector_id) "
                "VALUES (%%(cid)s, %%(module)s, %%(ds)s, %s, %%(cname)s, %%(cn)s, %%(dtype)s, %%(seq)s, %%(sel)s)" % (ac, av),
                cid=cid, ds=ds_id, cname=cname, cn=cn, dtype=dtype, seq=seq, sel=sel_id,
                module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
            )
            seq += 10
        p.rev_delete("sys_datasource_column", "sys_datasource_id = %s" % sql_lit(ds_id))

    # ---------- 4. 窗口 + 布局 + 区域 + 字段 + 查询 + 按钮 ----------
    win = cfg["window"]
    win_id = uid()
    ac, av = audit_cols()
    p.add(
        "INSERT INTO sys_window (sys_window_id, sys_module_id, %s, name, access_type, layout, layout_draggable) "
        "VALUES (%%(wid)s, %%(module)s, %s, %%(name)s, 'BZ', 'V', 'Y')" % (ac, av),
        wid=win_id, name=win["name"], module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
    )
    # 反向清理按「倒序执行」append（render 时整体 reversed）：后 append 的先执行
    p.rev_delete("sys_window", "sys_window_id = %s" % sql_lit(win_id))
    p.rev_delete("sys_window_layout", "sys_window_id = %s" % sql_lit(win_id))
    p.rev_delete("sys_window_region", "sys_window_id = %s" % sql_lit(win_id))
    p.rev_delete("sys_window_button", "sys_window_region_id IN (SELECT sys_window_region_id FROM sys_window_region WHERE sys_window_id = %s)" % sql_lit(win_id))
    p.rev_delete("sys_window_region_query", "sys_window_region_id IN (SELECT sys_window_region_id FROM sys_window_region WHERE sys_window_id = %s)" % sql_lit(win_id))
    p.rev_delete("sys_window_region_field", "sys_window_region_id IN (SELECT sys_window_region_id FROM sys_window_region WHERE sys_window_id = %s)" % sql_lit(win_id))
    p.rev_delete("ad_role_window", "sys_window_id = %s" % sql_lit(win_id))
    p.rev_delete("ad_role_window_button", "sys_window_id = %s" % sql_lit(win_id))

    region_id_by_code = {}
    button_rows = []      # (button_id, code, name) 供授权
    tables_by_name = {t["name"]: t for t in cfg.get("tables", [])}
    for i, r in enumerate(win.get("regions", []), start=1):
        rid = uid()
        region_id_by_code[r["code"]] = rid
        parent_rid = region_id_by_code.get(r.get("parent")) if r.get("parent") else None
        # 每区域独立 layout：SLW 渲染遍历 layout、每个 layout 只渲一个
        # 区域——主子表共用同一 layout 会使主表不渲染只剩子表（实测踩坑）；
        # 平台惯例（主子表窗口）= 每区域一 layout，name 用序号、seq=区域排列序。
        # 单区域窗口产物与旧版逐字段一致（name '1'、seq 10），单表行为不变
        layout_id = uid()
        p.add(
            "INSERT INTO sys_window_layout (sys_window_layout_id, sys_window_id, %s, name, position, seq, show_title) "
            "VALUES (%%(lid)s, %%(wid)s, %s, %%(lname)s, 'V', %%(lseq)s, 'N')" % (ac, av),
            lid=layout_id, wid=win_id, lname=str(i), lseq=i * 10,
            module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
        )
        p.add(
            "INSERT INTO sys_window_region (sys_window_region_id, sys_window_id, %s, code, name, type, access_type, sys_datasource_id, sys_window_layout_id, parent_region_id, page_size, seq, orderby_clause, show_title) "
            "VALUES (%%(rid)s, %%(wid)s, %s, %%(code)s, %%(name)s, %%(type)s, 'BZ', %%(ds)s, %%(lid)s, %%(parent)s, %%(ps)s, %%(seq)s, %%(ob)s, 'Y')" % (ac, av),
            rid=rid, wid=win_id, code=r["code"], name=r.get("cn", r["code"]), type=r.get("type", "GRID"),
            ds=ds_by_table[r["table"]], lid=layout_id, parent=parent_rid,
            ps=r.get("page_size", 15), seq=i * 10, ob=r.get("orderby", "created desc"),
            module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
        )

        # 区域字段：覆盖全部列（pk + 业务列 + fk + 审计列），与后台「生成字段」/存量惯例一致；
        # 业务列勾选表单/表格显示；pk、外键列、审计列不勾选（display_form/display_grid/seq 均为 NULL）
        t = tables_by_name[r["table"]]
        pk_name = t["name"] + "_id"
        region_cols = [(pk_name, t["cn_name"] + "ID", None)] + \
                      [(c["name"], c.get("cn", c["name"]), c) for c in t["columns"]] + \
                      [(a, b, None) for a, b, _ in AUDIT_COLS]
        fseq = 1
        for cname, cn, cconf in region_cols:
            cid = col_id_by_key[(t["name"], cname)]
            visible = cconf is not None and not cconf.get("fk")
            dv = cconf.get("field_default") if cconf else None
            if cname == "isactive" and not dv:
                dv = "Y"  # 参照存量：isactive 隐藏字段默认 Y
            p.add(
                "INSERT INTO sys_window_region_field (sys_window_region_field_id, sys_window_region_id, %s, name, sys_datasource_column_id, seq, not_null, is_unique, display_form, display_grid, default_value) "
                "VALUES (%%(fid)s, %%(rid)s, %s, %%(name)s, %%(cid)s, %%(seq)s, %%(nn)s, %%(uq)s, %%(df)s, %%(dg)s, %%(dv)s)" % (ac, av),
                fid=uid(), rid=rid, name=cn, cid=cid, seq=(fseq if visible else None),
                nn="Y" if (cconf and cconf.get("not_null")) else None,
                uq="Y" if (cconf and cconf.get("unique")) else None,
                df=("Y" if visible else None), dg=("Y" if visible else None), dv=dv,
                module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
            )
            if visible:
                fseq += 10 if fseq > 1 else 9  # 1,10,20,30...（存量惯例）

        # 查询条件
        qseq = 10
        for q in r.get("queries", []):
            cid = col_id_by_key[(t["name"], q["col"])]
            qdtype = next((c.get("ds_type", "STRING") for c in t["columns"] if c["name"] == q["col"]), "STRING")
            p.add(
                "INSERT INTO sys_window_region_query (sys_window_region_query_id, sys_window_region_id, %s, name, sys_datasource_column_id, type, data_type, seq) "
                "VALUES (%%(qid)s, %%(rid)s, %s, %%(name)s, %%(cid)s, %%(type)s, %%(dtype)s, %%(seq)s)" % (ac, av),
                qid=uid(), rid=rid, name=q.get("cn", q["col"]), cid=cid, type=q.get("type", "LIKE"), dtype=qdtype, seq=qseq,
                module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
            )
            qseq += 10

        # 按钮：sys_window_id 不写（NULL 不触发唯一约束，多区域可各有 NEW/EDIT/DELETE）
        for code, name, seq in STD_BUTTONS:
            if code not in r.get("buttons", ["NEW", "EDIT", "DELETE"]):
                continue
            bid = uid()
            button_rows.append((bid, code, name))
            p.add(
                "INSERT INTO sys_window_button (sys_window_button_id, sys_window_region_id, %s, code, name, type, seq) "
                "VALUES (%%(bid)s, %%(rid)s, %s, %%(code)s, %%(name)s, %%(type)s, %%(seq)s)" % (ac, av),
                bid=bid, rid=rid, code=code, name=name, type=code, seq=seq,
                module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
            )
        bseq = 40
        for cb in r.get("custom_buttons", []):
            bid = uid()
            button_rows.append((bid, cb["code"], cb["cn"]))
            p.add(
                "INSERT INTO sys_window_button (sys_window_button_id, sys_window_region_id, %s, code, name, type, seq, click_function) "
                "VALUES (%%(bid)s, %%(rid)s, %s, %%(code)s, %%(name)s, 'EVENT', %%(seq)s, %%(fn)s)" % (ac, av),
                bid=bid, rid=rid, code=cb["code"], name=cb["cn"], seq=bseq, fn=cb.get("click_function"),
                module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
            )
            bseq += 10

    # ---------- 5. 菜单（GROUP 可选新建 + WINDOW）----------
    menu = cfg["menu"]
    parent_id = menu.get("parent_id")
    group_cfg = menu.get("group")
    if group_cfg and group_cfg.get("create", True):
        gid = uid()
        p.add(
            "INSERT INTO ad_menu (ad_menu_id, %s, name, menu_type, parent_id, seq, is_show, show_mode, sys_module_id) "
            "VALUES (%%(mid)s, %s, %%(name)s, 'GROUP', '%s', %%(seq)s, 'Y', 'P', %%(module)s)" % (audit_cols()[0], audit_cols()[1], ROOT_MENU),
            mid=gid, name=group_cfg["name"], seq=group_cfg.get("seq", 999),
            module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
        )
        p.rev_delete("ad_menu", "ad_menu_id = %s" % sql_lit(gid))
        p.rev_delete("ad_role_menu", "ad_menu_id = %s" % sql_lit(gid))
        parent_id = gid
    if not parent_id:
        raise SystemExit("[配置缺失] menu.parent_id 或 menu.group.name 必须提供其一（父菜单须用户指定）")
    mid = uid()
    p.add(
        "INSERT INTO ad_menu (ad_menu_id, %s, name, menu_type, sys_window_id, parent_id, seq, show_mode, sys_module_id) "
        "VALUES (%%(mid)s, %s, %%(name)s, 'WINDOW', %%(wid)s, %%(pid)s, %%(seq)s, 'P', %%(module)s)" % (audit_cols()[0], audit_cols()[1]),
        mid=mid, name=menu["name"], wid=win_id, pid=parent_id, seq=menu.get("seq", 999),
        module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
    )
    p.rev_delete("ad_menu", "ad_menu_id = %s" % sql_lit(mid))
    p.rev_delete("ad_role_menu", "ad_menu_id = %s" % sql_lit(mid))

    # ---------- 6. 授权（系统管理员：菜单 + 窗口 + 全部按钮）----------
    for xid in [parent_id, mid]:
        if xid:
            p.add(
                "INSERT INTO ad_role_menu (ad_role_menu_id, ad_role_id, ad_menu_id) VALUES (%(id)s, %(role)s, %(mid)s) "
                "ON CONFLICT (ad_role_id, ad_menu_id) DO NOTHING",
                id=uid(), role=m["role"], mid=xid,
            )
    p.add(
        "INSERT INTO ad_role_window (ad_role_id, sys_window_id) VALUES (%(role)s, %(wid)s)",
        role=m["role"], wid=win_id,
    )
    for bid, _, _ in button_rows:
        p.add(
            "INSERT INTO ad_role_window_button (ad_role_id, sys_window_id, sys_window_button_id) VALUES (%(role)s, %(wid)s, %(bid)s)",
            role=m["role"], wid=win_id, bid=bid,
        )

    return plan, m, {"win_id": win_id, "menu_id": mid, "group_id": parent_id if group_cfg else None,
                     "buttons": button_rows, "ds_ids": list(ds_by_table.values())}


_LOOKUP_CACHE = {}


def _lookup_selector_id(name):
    """运行时查库定位既有 selector（如「是否」，按名称查找、id 随库而异）；无连接时返回缓存/None"""
    if name in _LOOKUP_CACHE:
        return _LOOKUP_CACHE[name]
    try:
        conn = psycopg2.connect(DEV_DSN)
        cur = conn.cursor()
        cur.execute("SELECT sys_selector_id FROM sys_selector WHERE name = %s", (name,))
        row = cur.fetchone()
        conn.close()
        _LOOKUP_CACHE[name] = row[0] if row else None
        return _LOOKUP_CACHE[name]
    except Exception:
        return None


def render_sql_file(plan, header):
    lines = ["-- %s" % header, "-- 生成时间: %s" % datetime.datetime.now(), ""]
    for sql, params in plan.ddl:
        lines.append(sql + "\n")
    for sql, params in plan.ins:
        rendered = sql
        for k, v in (params or {}).items():
            rendered = rendered.replace("%(" + k + ")s", sql_lit(v))
        lines.append(rendered + ";")
    return "\n".join(lines)


def render_reverse_file(plan, header):
    lines = ["-- %s（反向回滚，按依赖倒序执行）" % header, ""]
    lines.extend(reversed(plan.rev))
    lines += [""] + plan.drop
    return "\n".join(lines)


def check_conflicts(cfg, conn, rebuild):
    """同名冲突检测；rebuild=True 时按反向顺序级联删除既有同名对象"""
    cur = conn.cursor()
    win_name = cfg["window"]["name"]
    cur.execute("SELECT sys_window_id FROM sys_window WHERE name = %s", (win_name,))
    if cur.fetchone():
        if not rebuild:
            raise SystemExit("[冲突] 窗口「%s」已存在（--rebuild 可级联删除重建）" % win_name)
        _cascade_delete_window(cur, win_name)
    for t in cfg.get("tables", []):
        ds_name = t.get("ds_name", t["cn_name"])
        cur.execute("SELECT sys_datasource_id FROM sys_datasource WHERE name = %s", (ds_name,))
        if cur.fetchone():
            if not rebuild:
                raise SystemExit("[冲突] 数据源「%s」已存在（--rebuild 可级联删除重建）" % ds_name)
            cur.execute("DELETE FROM sys_datasource_column WHERE sys_datasource_id IN (SELECT sys_datasource_id FROM sys_datasource WHERE name=%s)", (ds_name,))
            cur.execute("DELETE FROM sys_datasource WHERE name = %s", (ds_name,))
        if t.get("create", True):
            cur.execute("SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s", (t["name"],))
            if cur.fetchone():
                if not rebuild:
                    raise SystemExit("[冲突] 表 %s 已存在（--rebuild 可 DROP 重建）" % t["name"])
                cur.execute("DROP TABLE IF EXISTS %s CASCADE" % t["name"])
    # selector 冲突（仅新建名单里的）
    for t in cfg.get("tables", []):
        for c in t["columns"]:
            sel = c.get("selector")
            if sel and not sel.get("reuse") and sel.get("name"):
                cur.execute("SELECT 1 FROM sys_selector WHERE name = %s", (sel["name"],))
                if cur.fetchone():
                    if not rebuild:
                        raise SystemExit("[冲突] 数据选项「%s」已存在（--rebuild 可删除重建）" % sel["name"])
                    cur.execute("DELETE FROM sys_selector_data WHERE sys_selector_id IN (SELECT sys_selector_id FROM sys_selector WHERE name=%s)", (sel["name"],))
                    cur.execute("DELETE FROM sys_selector WHERE name = %s", (sel["name"],))
    # 菜单冲突（同父同名）
    menu = cfg["menu"]
    cur.execute("SELECT ad_menu_id FROM ad_menu WHERE name = %s AND menu_type='WINDOW'", (menu["name"],))
    if cur.fetchone():
        if not rebuild:
            raise SystemExit("[冲突] 菜单「%s」已存在（--rebuild 可删除重建）" % menu["name"])
        cur.execute("DELETE FROM ad_role_menu WHERE ad_menu_id IN (SELECT ad_menu_id FROM ad_menu WHERE name=%s AND menu_type='WINDOW')", (menu["name"],))
        cur.execute("DELETE FROM ad_menu WHERE name = %s AND menu_type='WINDOW'", (menu["name"],))
    g = menu.get("group")
    if g and g.get("create", True):
        cur.execute("SELECT ad_menu_id FROM ad_menu WHERE name = %s AND parent_id = %s", (g["name"], ROOT_MENU))
        rows = cur.fetchall()
        if rows:
            if not rebuild:
                raise SystemExit("[冲突] 分组菜单「%s」已存在（--rebuild 可删除重建）" % g["name"])
            for (gid,) in rows:  # 清理全部同名残留（含历史副本）+ 授权
                cur.execute("DELETE FROM ad_role_menu WHERE ad_menu_id = %s", (gid,))
                cur.execute("DELETE FROM ad_menu WHERE ad_menu_id = %s", (gid,))
    conn.commit()


def _cascade_delete_window(cur, win_name):
    """按 WindowEvent 级联顺序删除既有窗口"""
    cur.execute("SELECT sys_window_id FROM sys_window WHERE name = %s", (win_name,))
    wid = cur.fetchone()[0]
    cur.execute("DELETE FROM ad_role_menu WHERE ad_menu_id IN (SELECT ad_menu_id FROM ad_menu WHERE sys_window_id=%s)", (wid,))
    cur.execute("DELETE FROM ad_menu WHERE sys_window_id = %s", (wid,))
    cur.execute("DELETE FROM ad_role_window_button WHERE sys_window_id = %s", (wid,))
    cur.execute("DELETE FROM ad_role_window WHERE sys_window_id = %s", (wid,))
    cur.execute("DELETE FROM sys_window_region_field WHERE sys_window_region_id IN (SELECT sys_window_region_id FROM sys_window_region WHERE sys_window_id=%s)", (wid,))
    cur.execute("DELETE FROM sys_window_region_query WHERE sys_window_region_id IN (SELECT sys_window_region_id FROM sys_window_region WHERE sys_window_id=%s)", (wid,))
    cur.execute("DELETE FROM sys_window_button WHERE sys_window_region_id IN (SELECT sys_window_region_id FROM sys_window_region WHERE sys_window_id=%s)", (wid,))
    cur.execute("DELETE FROM sys_window_region WHERE sys_window_id = %s", (wid,))
    cur.execute("DELETE FROM sys_window_layout WHERE sys_window_id = %s", (wid,))
    cur.execute("DELETE FROM sys_window WHERE sys_window_id = %s", (wid,))


def verify(conn, info, cfg):
    """SQL 级核验：FK 完整性 + 计数"""
    cur = conn.cursor()
    wid = info["win_id"]
    checks = [
        ("窗口存在", "SELECT name FROM sys_window WHERE sys_window_id=%s", (wid,)),
        ("区域数", "SELECT count(*) FROM sys_window_region WHERE sys_window_id=%s", (wid,)),
        ("区域-布局独立（应为t）",
         "SELECT count(*) = count(DISTINCT sys_window_layout_id) FROM sys_window_region WHERE sys_window_id=%s", (wid,)),
        ("区域字段数",
         "SELECT count(*) FROM sys_window_region_field f JOIN sys_window_region r ON r.sys_window_region_id=f.sys_window_region_id "
         "WHERE r.sys_window_id=%s", (wid,)),
        ("字段引用悬空数（应为0）",
         "SELECT count(*) FROM sys_window_region_field f JOIN sys_window_region r ON r.sys_window_region_id=f.sys_window_region_id "
         "LEFT JOIN sys_datasource_column c ON c.sys_datasource_column_id=f.sys_datasource_column_id "
         "WHERE r.sys_window_id=%s AND f.sys_datasource_column_id IS NOT NULL AND c.sys_datasource_column_id IS NULL", (wid,)),
        ("按钮数", "SELECT count(*) FROM sys_window_button b JOIN sys_window_region r ON r.sys_window_region_id=b.sys_window_region_id WHERE r.sys_window_id=%s", (wid,)),
        ("菜单授权", "SELECT count(*) FROM ad_role_menu WHERE ad_menu_id=%s", (info["menu_id"],)),
        ("窗口授权", "SELECT count(*) FROM ad_role_window WHERE sys_window_id=%s", (wid,)),
        ("按钮授权数", "SELECT count(*) FROM ad_role_window_button WHERE sys_window_id=%s", (wid,)),
    ]
    report = []
    ok = True
    zero_means_fail = {"窗口存在", "区域数", "区域-布局独立（应为t）", "区域字段数", "按钮数", "菜单授权", "窗口授权", "按钮授权数"}
    for label, sql, args in checks:
        cur.execute(sql, args)
        val = cur.fetchone()[0]
        report.append("  %-22s %s" % (label, val))
        if val in (0, None) and label in zero_means_fail:
            ok = False
    # 数据源字段/selector FK 抽查
    for ds_id in info["ds_ids"]:
        cur.execute("SELECT count(*) FROM sys_datasource_column WHERE sys_datasource_id=%s", (ds_id,))
        report.append("  %-22s %s" % ("数据源字段数", cur.fetchone()[0]))
    return "\n".join(report), ok


# ============ 变更模式（mode="change"）：对既有窗口/数据源做增量调整 ============
# 支持 op：add_column / modify_column / field_display / add_query / remove_query
#          / add_button / remove_button
# 与新建模式共用 Plan / 留档 / 事务；UPDATE/DELETE 前记录旧值生成反向回滚 SQL。
# 注意：不做"删业务列"（数据丢失风险），需要时人工处理。

CHANGE_OPS = ("add_column", "modify_column", "field_display", "add_query",
              "remove_query", "add_button", "remove_button")


def _must(cond, msg):
    if not cond:
        raise SystemExit("[变更失败] " + msg)


def _find_window_id(cur, name):
    cur.execute("SELECT sys_window_id FROM sys_window WHERE name = %s", (name,))
    row = cur.fetchone()
    return row[0] if row else None


def _find_ds_id_by_table(cur, table):
    cur.execute("SELECT sys_datasource_id FROM sys_datasource WHERE table_name = %s AND type = 'TABLE' "
                "ORDER BY created LIMIT 1", (table,))
    row = cur.fetchone()
    return row[0] if row else None


def _find_region(cur, wid, code):
    cur.execute("SELECT sys_window_region_id, sys_datasource_id FROM sys_window_region "
                "WHERE sys_window_id = %s AND code = %s", (wid, code))
    row = cur.fetchone()
    return row if row else None


def _regions_of_ds(cur, ds_id):
    cur.execute("SELECT sys_window_region_id, code FROM sys_window_region "
                "WHERE sys_datasource_id = %s ORDER BY seq", (ds_id,))
    return cur.fetchall()


def _find_ds_col(cur, ds_id, column_name):
    cur.execute("SELECT sys_datasource_column_id, name, data_type, sys_selector_id "
                "FROM sys_datasource_column WHERE sys_datasource_id = %s AND column_name = %s",
                (ds_id, column_name))
    row = cur.fetchone()
    return row if row else None


def _find_region_field(cur, rid, cid):
    cur.execute("SELECT sys_window_region_field_id, name, seq, display_form, display_grid, "
                "not_null, is_unique, default_value FROM sys_window_region_field "
                "WHERE sys_window_region_id = %s AND sys_datasource_column_id = %s", (rid, cid))
    row = cur.fetchone()
    return row if row else None


def _find_query_by_col(cur, rid, cid):
    cur.execute("SELECT sys_window_region_query_id, name, type, seq, data_type "
                "FROM sys_window_region_query WHERE sys_window_region_id = %s AND sys_datasource_column_id = %s",
                (rid, cid))
    row = cur.fetchone()
    return row if row else None


def _find_button(cur, rid, code):
    cur.execute("SELECT sys_window_button_id, code, name, type, seq, click_function "
                "FROM sys_window_button WHERE sys_window_region_id = %s AND code = %s", (rid, code))
    row = cur.fetchone()
    return row if row else None


def build_change(cfg, conn):
    """变更模式构建：连库定位既有对象 ids，收集增量 SQL 与反向回滚 SQL"""
    m = _meta_of(cfg)
    if not m["role"]:
        raise SystemExit("[缺角色] 未能解析系统管理员角色 id（库内无 name='Admin'/'系统管理员' 的 ad_role 行），"
                         "请在配置 meta.role_id 显式传入")
    plan = Plan()
    cur = conn.cursor()
    target = cfg.get("target", {})
    checks = []   # (label, sql, args, expect) 核验断言
    seq_cache = {}  # key -> max seq（同批次多次取号不重复）

    def take_seq(key, table, where, params):
        if key not in seq_cache:
            cur.execute("SELECT coalesce(max(seq), 0) FROM %s WHERE %s" % (table, where), params)
            seq_cache[key] = cur.fetchone()[0]
        seq_cache[key] += 10
        return seq_cache[key]

    def op_window(op):
        name = op.get("window") or target.get("window")
        _must(name, "op「%s」缺 window（或顶层 target.window）" % op.get("op"))
        wid = _find_window_id(cur, name)
        _must(wid, "窗口「%s」不存在（核对 sys_window.name）" % name)
        return wid

    def op_table_ds(op):
        t = op.get("table") or target.get("table")
        _must(t, "op「%s」缺 table（或顶层 target.table）" % op.get("op"))
        ds = _find_ds_id_by_table(cur, t)
        _must(ds, "表 %s 未找到 TABLE 型数据源（核对 sys_datasource.table_name）" % t)
        return t, ds

    def op_region(op):
        """返回 (rid, ds_id)"""
        wid = op_window(op)
        r = _find_region(cur, wid, op.get("region"))
        _must(r, "窗口「%s」无区域 code=%s" % (op.get("window") or target.get("window"), op.get("region")))
        return r[0], r[1]

    def op_col(cur_ds, op):
        col = _find_ds_col(cur, cur_ds, op.get("col") or op.get("name"))
        _must(col, "数据源字段「%s」不存在" % (op.get("col") or op.get("name")))
        return col

    ac, av = audit_cols()
    for idx, op in enumerate(cfg.get("changes", []), start=1):
        kind = op.get("op")
        _must(kind in CHANGE_OPS, "第%d条 op「%s」不认识（支持: %s）" % (idx, kind, ", ".join(CHANGE_OPS)))

        if kind == "add_column":
            t, ds = op_table_ds(op)
            name = op.get("name")
            _must(name, "add_column 缺 name")
            check_ident(name, "列名")
            check_ident(t, "表名")
            cur.execute("SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
                        "AND table_name=%s AND column_name=%s", (t, name))
            col_exists = cur.fetchone()
            _must(not _find_ds_col(cur, ds, name), "数据源字段 %s 已存在" % name)
            if not col_exists:
                plan.ddl.append(("ALTER TABLE %s ADD COLUMN %s %s;" % (t, name, op.get("pg", "varchar(200)")), None))
                plan.drop.append("ALTER TABLE %s DROP COLUMN IF EXISTS %s;" % (t, name))
            # 表列已存在（DDL 先行场景，如分期实施）：跳过 ALTER，仅补数据源字段+区域字段；
            # 反向回滚也不 DROP 业务列（列数据归属前置 DDL，不归本次变更）
            cid = uid()
            sel_id = ensure_selector(plan, m, op)
            plan.add(
                "INSERT INTO sys_datasource_column (sys_datasource_column_id, sys_module_id, sys_datasource_id, %s, column_name, name, data_type, seq, sys_selector_id) "
                "VALUES (%%(cid)s, %%(module)s, %%(ds)s, %s, %%(cname)s, %%(cn)s, %%(dtype)s, %%(seq)s, %%(sel)s)" % (ac, av),
                cid=cid, ds=ds, cname=name, cn=op.get("cn", name), dtype=op.get("ds_type", "STRING"),
                seq=take_seq(("dsc", ds), "sys_datasource_column", "sys_datasource_id = %s", (ds,)), sel=sel_id,
                module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
            )
            # 反向：先删区域字段（引用 cid），后删数据源字段（rev 倒序执行）
            plan.rev.append("DELETE FROM sys_datasource_column WHERE sys_datasource_column_id = %s;" % sql_lit(cid))
            plan.rev.append("DELETE FROM sys_window_region_field WHERE sys_datasource_column_id = %s;" % sql_lit(cid))
            # 区域字段：默认给引用该数据源的全部区域加（regions: "all"）；也可指定 [{"region":"t1","display_form":"N"...}]
            regions_cfg = op.get("regions", "all")
            if regions_cfg == "all":
                targets = [(rid, code, {}) for rid, code in _regions_of_ds(cur, ds)]
            else:
                targets = []
                for rc in regions_cfg:
                    wid = op_window({"window": rc.get("window", op.get("window"))})
                    r = _find_region(cur, wid, rc.get("region", target.get("region")))
                    _must(r, "指定区域 %s 不存在" % rc.get("region"))
                    targets.append((r[0], rc.get("region"), rc))
            for rid, rcode, rc in targets:
                fseq = take_seq(("rf", rid), "sys_window_region_field",
                                "sys_window_region_id = %s AND seq IS NOT NULL", (rid,))
                fid = uid()
                plan.add(
                    "INSERT INTO sys_window_region_field (sys_window_region_field_id, sys_window_region_id, %s, name, sys_datasource_column_id, seq, not_null, is_unique, display_form, display_grid, default_value) "
                    "VALUES (%%(fid)s, %%(rid)s, %s, %%(name)s, %%(cid)s, %%(seq)s, %%(nn)s, %%(uq)s, %%(df)s, %%(dg)s, %%(dv)s)" % (ac, av),
                    fid=fid, rid=rid, name=op.get("cn", name), cid=cid, seq=fseq,
                    nn="Y" if op.get("not_null") else None, uq="Y" if op.get("unique") else None,
                    df=rc.get("display_form", "Y"), dg=rc.get("display_grid", "Y"),
                    dv=op.get("field_default"),
                    module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
                )
                plan.rev.append("DELETE FROM sys_window_region_field WHERE sys_window_region_field_id = %s;" % sql_lit(fid))
                checks.append(("加列-区域%s字段" % rcode,
                               "SELECT count(*) FROM sys_window_region_field WHERE sys_window_region_field_id=%s",
                               (fid,), 1))
            checks.append(("加列-数据源字段", "SELECT count(*) FROM sys_datasource_column WHERE sys_datasource_column_id=%s",
                           (cid,), 1))

        elif kind == "modify_column":
            t, ds = op_table_ds(op)
            col = op_col(ds, op)
            cid, old_cn, old_dtype, old_sel = col
            sets, params = [], {"cid": cid, "by": m["created_by"]}
            rev_sets = ["updated=now()", "updatedby=%s" % sql_lit(m["created_by"])]
            if "cn" in op:
                sets.append("name=%(cn)s"); params["cn"] = op["cn"]
                rev_sets.append("name=%s" % sql_lit(old_cn))
            if "ds_type" in op:
                sets.append("data_type=%(dt)s"); params["dt"] = op["ds_type"]
                rev_sets.append("data_type=%s" % sql_lit(old_dtype))
            if "selector" in op:
                sel_id = ensure_selector(plan, m, op)
                sets.append("sys_selector_id=%(sel)s"); params["sel"] = sel_id
                rev_sets.append("sys_selector_id=%s" % sql_lit(old_sel))
            _must(sets, "modify_column 无可变更属性（支持 cn / ds_type / selector）")
            plan.add("UPDATE sys_datasource_column SET " + ", ".join(sets) +
                     ", updated=now(), updatedby=%(by)s WHERE sys_datasource_column_id=%(cid)s", **params)
            plan.rev.append("UPDATE sys_datasource_column SET %s WHERE sys_datasource_column_id = %s;"
                            % (", ".join(rev_sets), sql_lit(cid)))
            # 联动：区域字段 name 冗余存储，同步更新并记录旧值
            if "cn" in op:
                for rid, rcode in _regions_of_ds(cur, ds):
                    f = _find_region_field(cur, rid, cid)
                    if not f:
                        continue
                    plan.add("UPDATE sys_window_region_field SET name=%(cn)s, updated=now(), "
                             "updatedby=%(by)s WHERE sys_window_region_field_id=%(fid)s",
                             cn=op["cn"], by=m["created_by"], fid=f[0])
                    plan.rev.append("UPDATE sys_window_region_field SET name=%s WHERE sys_window_region_field_id = %s;"
                                    % (sql_lit(f[1]), sql_lit(f[0])))
            checks.append(("改列-新中文名", "SELECT name FROM sys_datasource_column WHERE sys_datasource_column_id=%s",
                           (cid,), op.get("cn", old_cn)))

        elif kind == "field_display":
            rid, ds = op_region(op)
            col = op_col(ds, op)
            f = _find_region_field(cur, rid, col[0])
            _must(f, "区域 %s 尚无字段「%s」的区域字段行（若为新列先 add_column）" % (op.get("region"), op.get("col")))
            fid, old_name, old_seq, old_df, old_dg, old_nn, old_uq, old_dv = f
            editable = {"name": "name", "display_form": "display_form", "display_grid": "display_grid",
                        "seq": "seq", "not_null": "not_null", "is_unique": "is_unique",
                        "default_value": "default_value"}
            sets, params = [], {"fid": fid, "by": m["created_by"]}
            rev_sets = ["updated=now()", "updatedby=%s" % sql_lit(m["created_by"])]
            oldmap = {"name": old_name, "display_form": old_df, "display_grid": old_dg, "seq": old_seq,
                      "not_null": old_nn, "is_unique": old_uq, "default_value": old_dv}
            for k, v in op.items():
                if k in editable and k != "op":
                    sets.append("%s=%%(%s)s" % (editable[k], k)); params[k] = v
                    rev_sets.append("%s=%s" % (editable[k], sql_lit(oldmap[k])))
            _must(sets, "field_display 无可变更属性（支持 %s）" % ", ".join(sorted(editable)))
            plan.add("UPDATE sys_window_region_field SET " + ", ".join(sets) +
                     ", updated=now(), updatedby=%(by)s WHERE sys_window_region_field_id=%(fid)s", **params)
            plan.rev.append("UPDATE sys_window_region_field SET %s WHERE sys_window_region_field_id = %s;"
                            % (", ".join(rev_sets), sql_lit(fid)))
            conds = " AND ".join(
                ("%s IS NULL" % editable[k]) if v is None else ("%s=%s" % (editable[k], sql_lit(v)))
                for k, v in op.items() if k in editable)
            checks.append(("调字段-生效",
                           "SELECT count(*) FROM sys_window_region_field WHERE sys_window_region_field_id=%s AND %s"
                           % (sql_lit(fid), conds), (), 1))

        elif kind in ("add_query", "remove_query"):
            rid, ds = op_region(op)
            col = op_col(ds, op)
            cid, cn, dtype, _ = col
            if kind == "add_query":
                _must(not _find_query_by_col(cur, rid, cid), "区域 %s 已有字段「%s」的查询条件" % (op.get("region"), op.get("col")))
                qid = uid()
                plan.add(
                    "INSERT INTO sys_window_region_query (sys_window_region_query_id, sys_window_region_id, %s, name, sys_datasource_column_id, type, data_type, seq) "
                    "VALUES (%%(qid)s, %%(rid)s, %s, %%(name)s, %%(cid)s, %%(type)s, %%(dtype)s, %%(seq)s)" % (ac, av),
                    qid=qid, rid=rid, name=op.get("cn", cn), cid=cid,
                    type=op.get("type", "LIKE"), dtype=op.get("ds_type", dtype),
                    seq=take_seq(("q", rid), "sys_window_region_query", "sys_window_region_id = %s", (rid,)),
                    module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
                )
                plan.rev.append("DELETE FROM sys_window_region_query WHERE sys_window_region_query_id = %s;" % sql_lit(qid))
                checks.append(("加查询", "SELECT count(*) FROM sys_window_region_query WHERE sys_window_region_query_id=%s",
                               (qid,), 1))
            else:
                q = _find_query_by_col(cur, rid, cid)
                _must(q, "区域 %s 无字段「%s」的查询条件" % (op.get("region"), op.get("col")))
                qid, qname, qtype, qseq, qdtype = q
                plan.add("DELETE FROM sys_window_region_query WHERE sys_window_region_query_id=%(qid)s", qid=qid)
                plan.rev.append(
                    "INSERT INTO sys_window_region_query (sys_window_region_query_id, sys_window_region_id, "
                    "ad_client_id, ad_org_id, isactive, created, createdby, updated, updatedby, name, "
                    "sys_datasource_column_id, type, data_type, seq) VALUES (%s, %s, '%s', '%s', 'Y', now(), '%s', now(), '%s', %s, %s, %s, %s, %s);"
                    % (sql_lit(qid), sql_lit(rid), m["client"], m["org"], m["created_by"], m["created_by"],
                       sql_lit(qname), sql_lit(cid), sql_lit(qtype), sql_lit(qdtype), sql_lit(qseq)))
                checks.append(("删查询", "SELECT count(*) FROM sys_window_region_query WHERE sys_window_region_query_id=%s",
                               (qid,), 0))

        elif kind in ("add_button", "remove_button"):
            rid, ds = op_region(op)
            code = op.get("code")
            _must(code, "op「%s」缺 code" % kind)
            b = _find_button(cur, rid, code)
            if kind == "add_button":
                _must(not b, "区域 %s 已有按钮 code=%s" % (op.get("region"), code))
                std = code in ("NEW", "EDIT", "DELETE")
                bid = uid()
                bseq = op.get("seq") or take_seq(("btn", rid), "sys_window_button",
                                                 "sys_window_region_id = %s", (rid,))
                if std:
                    plan.add(
                        "INSERT INTO sys_window_button (sys_window_button_id, sys_window_region_id, %s, code, name, type, seq) "
                        "VALUES (%%(bid)s, %%(rid)s, %s, %%(code)s, %%(name)s, %%(type)s, %%(seq)s)" % (ac, av),
                        bid=bid, rid=rid, code=code, name=op.get("cn", code), type=code, seq=bseq,
                        module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
                    )
                else:
                    _must(op.get("click_function"), "自定义按钮缺 click_function（前端 eval 脚本）")
                    plan.add(
                        "INSERT INTO sys_window_button (sys_window_button_id, sys_window_region_id, %s, code, name, type, seq, click_function) "
                        "VALUES (%%(bid)s, %%(rid)s, %s, %%(code)s, %%(name)s, 'EVENT', %%(seq)s, %%(fn)s)" % (ac, av),
                        bid=bid, rid=rid, code=code, name=op.get("cn", code), seq=bseq, fn=op.get("click_function"),
                        module=m["module"], client=m["client"], org=m["org"], created_by=m["created_by"],
                    )
                # 反向（倒序执行 → 先删授权再删按钮，规避 FK）
                plan.rev.append("DELETE FROM sys_window_button WHERE sys_window_button_id = %s;" % sql_lit(bid))
                plan.rev.append("DELETE FROM ad_role_window_button WHERE sys_window_button_id = %s;" % sql_lit(bid))
                # 授权系统管理员（授权是登录快照，执行后需重新登录）
                plan.add("INSERT INTO ad_role_window_button (ad_role_id, sys_window_id, sys_window_button_id) "
                         "VALUES (%(role)s, %(wid)s, %(bid)s)",
                         role=m["role"], wid=op_window(op), bid=bid)
                checks.append(("加按钮", "SELECT count(*) FROM sys_window_button WHERE sys_window_button_id=%s",
                               (bid,), 1))
                checks.append(("加按钮-授权", "SELECT count(*) FROM ad_role_window_button WHERE sys_window_button_id=%s",
                               (bid,), 1))
            else:
                _must(b, "区域 %s 无按钮 code=%s" % (op.get("region"), code))
                bid, bcode, bname, btype, bseq, bfn = b
                plan.add("DELETE FROM ad_role_window_button WHERE sys_window_button_id=%(bid)s", bid=bid)
                plan.add("DELETE FROM sys_window_button WHERE sys_window_button_id=%(bid)s", bid=bid)
                cols_rev = ("INSERT INTO sys_window_button (sys_window_button_id, sys_window_region_id, "
                            "ad_client_id, ad_org_id, isactive, created, createdby, updated, updatedby, "
                            "code, name, type, seq%s) VALUES (%s, %s, '%s', '%s', 'Y', now(), '%s', now(), '%s', %s, %s, %s, %s%s);"
                            % (", click_function" if bfn else "",
                               sql_lit(bid), sql_lit(rid), m["client"], m["org"], m["created_by"], m["created_by"],
                               sql_lit(bcode), sql_lit(bname), sql_lit(btype), sql_lit(bseq),
                               (", " + sql_lit(bfn)) if bfn else ""))
                plan.rev.append("INSERT INTO ad_role_window_button (ad_role_id, sys_window_id, sys_window_button_id) "
                                "VALUES ('%s', (SELECT sys_window_id FROM sys_window_region WHERE sys_window_region_id=%s), %s);"
                                % (m["role"], sql_lit(rid), sql_lit(bid)))
                plan.rev.append(cols_rev)
                checks.append(("删按钮", "SELECT count(*) FROM sys_window_button WHERE sys_window_button_id=%s",
                               (bid,), 0))

    _must(cfg.get("changes"), "changes 为空，无可执行变更")
    slug = target.get("window") or (cfg["changes"][0].get("window") or cfg["changes"][0].get("table") or "change")
    return plan, m, {"slug": slug, "checks": checks}


def verify_change(conn, info):
    """变更后核验：逐断言执行，全部通过才提交"""
    report, ok = [], True
    for label, sql, args, expect in info["checks"]:
        cur = conn.cursor()
        cur.execute(sql, args)
        val = cur.fetchone()[0]
        report.append("  %-22s %s（期望 %s）%s" % (label, val, expect, "" if val == expect else " ← 不符!"))
        if val != expect:
            ok = False
    return "\n".join(report), ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="配置 JSON 路径")
    ap.add_argument("--dsn", help="目标库 DSN：host=... port=... dbname=... user=... password=...（或环境变量 LOWCODE_PG_DSN）")
    ap.add_argument("--dry-run", action="store_true", help="只生成 SQL 文件，不执行")
    ap.add_argument("--rebuild", action="store_true", help="同名冲突时级联删除重建")
    ap.add_argument("--out", default="docs/sql", help="SQL 留档目录")
    args = ap.parse_args()

    cfg = json.load(open(args.config, encoding="utf-8"))
    resolve_dsn(args.dsn)
    check_out_dir(args.out)
    try_resolve_admin_role()

    # ---------- 变更模式分支 ----------
    if cfg.get("mode") == "change":
        # 变更必须连库（定位 ids / 读旧值），dry-run 也只读不写
        conn = psycopg2.connect(DEV_DSN)
        conn.autocommit = False
        try:
            plan, m, info = build_change(cfg, conn)
            slug = safe_slug(info["slug"])
            if args.dry_run or m["env"] != "dev":
                print("[dry-run] 仅生成变更 SQL 文件（env=%s）" % m["env"])
            else:
                cur = conn.cursor()
                try:
                    for sql, _ in plan.ddl:
                        cur.execute(sql)
                    for sql, params in plan.ins:
                        cur.execute(sql, params)
                    report, ok = verify_change(conn, info)
                    if not ok:
                        conn.rollback()
                        print("[核验失败，已回滚]\n" + report)
                        sys.exit(1)
                    conn.commit()
                    print("[已提交 dev 库] 变更目标「%s」，共 %d 条操作" % (slug, len(cfg["changes"])))
                    print(report)
                    print("\n!! 若涉及按钮/授权：admin 需【重新登录】后生效 !!")
                except Exception as e:
                    conn.rollback()
                    print("[执行失败，已回滚] %s" % e)
                    sys.exit(1)
        finally:
            conn.close()
        os.makedirs(args.out, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        f1 = os.path.join(args.out, "%s-%s-change.sql" % (stamp, slug))
        f2 = os.path.join(args.out, "%s-%s-change-reverse.sql" % (stamp, slug))
        open(f1, "w", encoding="utf-8").write(render_sql_file(plan, "低代码配置增量变更: %s" % slug))
        open(f2, "w", encoding="utf-8").write(render_reverse_file(plan, "低代码配置变更回滚: %s" % slug))
        print("[留档] %s\n[留档] %s" % (f1, f2))
        return

    # ---------- 新建模式（原流程）----------
    slug = safe_slug(cfg["window"]["name"])
    plan, m, info = build(cfg)

    if args.dry_run or m["env"] != "dev":
        print("[dry-run] 仅生成 SQL 文件（env=%s）" % m["env"])
    else:
        conn = psycopg2.connect(DEV_DSN)
        conn.autocommit = False
        check_conflicts(cfg, conn, args.rebuild)
        cur = conn.cursor()
        try:
            for sql, _ in plan.ddl:
                cur.execute(sql)
            for sql, params in plan.ins:
                cur.execute(sql, params)
            report, ok = verify(conn, info, cfg)
            if not ok:
                conn.rollback()
                print("[核验失败，已回滚]\n" + report)
                sys.exit(1)
            conn.commit()
            print("[已提交 dev 库] 窗口「%s」" % slug)
            print(report)
            print("\n!! 重要：admin 的窗口/按钮授权是登录时快照，需【重新登录】后生效 !!")
        except Exception as e:
            conn.rollback()
            print("[执行失败，已回滚] %s" % e)
            sys.exit(1)

    os.makedirs(args.out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    f1 = os.path.join(args.out, "%s-%s-seed.sql" % (stamp, slug))
    f2 = os.path.join(args.out, "%s-%s-seed-reverse.sql" % (stamp, slug))
    open(f1, "w", encoding="utf-8").write(render_sql_file(plan, "低代码配置正向插入: %s" % slug))
    open(f2, "w", encoding="utf-8").write(render_reverse_file(plan, "低代码配置反向清理: %s" % slug))
    print("[留档] %s\n[留档] %s" % (f1, f2))


if __name__ == "__main__":
    main()
