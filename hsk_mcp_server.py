# W10 自定义 MCP 服务器：查 HSK 词汇等级
# 依赖：python -m pip install "mcp[cli]"
# 运行：python hsk_mcp_server.py
#
# 说明：本服务器使用 stdio 传输。运行时"挂起、不退出"就是启动成功，
# 表示它正在等待客户端通过标准输入/输出连接；按 Ctrl+C 结束。
"""hsk-tools：一个只读本地 CSV、完全离线的 MCP 服务器。

暴露两个工具：
    hsk_level(word)       查某个词的 HSK 等级
    list_by_level(level)  列出某个等级的全部词汇

安全边界（与第 10 讲"服务端不等于可信端"对应）：
    * 只读 data/生词表.csv，不写文件、不发网络请求、不读环境变量；
    * 所有入参先校验（非空、长度上限、等级为 1-9 的整数），再查表；
    * stdout 留给 JSON-RPC，诊断信息一律写 stderr，避免破坏协议。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_NAME = "生词表.csv"
MAX_INPUT_LEN = 20
HSK_MIN, HSK_MAX = 1, 9


# --------------------------------------------------------------------------
# 数据定位：整包运行时走 weekpath；单独上传 week10_MCP/ 时走本目录 data/
# --------------------------------------------------------------------------
def _csv_candidates() -> list[Path]:
    candidates: list[Path] = []
    if str(HERE.parent) not in sys.path:
        sys.path.insert(0, str(HERE.parent))
    try:
        import weekpath  # type: ignore  # 作品集根目录的公共模块

        candidates.append(Path(weekpath.data_path(CSV_NAME)))
    except Exception:
        pass
    candidates.append(HERE / "data" / CSV_NAME)
    candidates.append(HERE.parent / "data" / CSV_NAME)
    return candidates


def _locate_csv() -> Path:
    candidates = _csv_candidates()
    for path in candidates:
        if path.is_file():
            return path
    tried = "\n".join("  - %s" % p for p in candidates)
    raise SystemExit(
        "找不到数据文件 %s。已尝试：\n%s\n"
        "请确认 data/%s 与本文件（或 weekpath.py）的相对位置没有改变。"
        % (CSV_NAME, tried, CSV_NAME)
    )


def _load_rows() -> list[dict[str, str]]:
    with VOCAB.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"词汇", "HSK等级"}
        fields = set(reader.fieldnames or [])
        if not required.issubset(fields):
            raise SystemExit(
                "数据表 %s 缺少必需列：%s" % (VOCAB, "、".join(sorted(required - fields)))
            )
        rows = []
        for raw in reader:
            row = {k: (v or "").strip() for k, v in raw.items()}
            if row.get("词汇") and row.get("HSK等级"):
                rows.append(row)
        return rows


VOCAB = _locate_csv()
ROWS = _load_rows()


# --------------------------------------------------------------------------
# MCP 服务端库：1.x 叫 FastMCP，2.x 改名 MCPServer，这里做版本自适应
# --------------------------------------------------------------------------
try:
    from mcp.server.fastmcp import FastMCP  # mcp 1.x
except ImportError:
    try:
        from mcp.server import MCPServer as FastMCP  # mcp 2.x
    except ImportError:
        raise SystemExit(
            "未找到 MCP 服务端库。请先安装：python -m pip install \"mcp[cli]\"\n"
            "（若使用 mcp 2.x，本文件会自动改用 MCPServer，无需改代码。）"
        )

mcp = FastMCP("hsk-tools")


# --------------------------------------------------------------------------
# 输入校验：工具函数的输入边界永远写在我们手里
# --------------------------------------------------------------------------
def _clean(value: object, label: str, max_len: int = MAX_INPUT_LEN) -> str:
    if not isinstance(value, str):
        raise ValueError("%s必须是字符串。" % label)
    text = value.strip()
    if not text:
        raise ValueError("%s不能为空。" % label)
    if len(text) > max_len:
        raise ValueError("%s过长（最多 %d 个字符）。" % (label, max_len))
    if any(ch in text for ch in "\r\n\t"):
        raise ValueError("%s不能包含换行或制表符。" % label)
    return text


def _normalize_level(value: object) -> str:
    text = _clean(value, "等级", max_len=8).lower()
    text = text.replace("hsk", "").replace("级", "").strip()
    if not text.isdigit() or not (HSK_MIN <= int(text) <= HSK_MAX):
        raise ValueError("等级应为 %d-%d 的整数，收到：%s" % (HSK_MIN, HSK_MAX, value))
    return str(int(text))


# --------------------------------------------------------------------------
# 工具：类型注解不能省（MCP 用它生成 inputSchema）
# --------------------------------------------------------------------------
@mcp.tool()
def hsk_level(word: str) -> str:
    """查询某个词属于 HSK 几级。

    参数 word：要查询的词语，例如「把」。
    返回：形如「把 -> 3 级」；查不到时返回「未找到 xxx」。
    """
    try:
        target = _clean(word, "词语")
    except ValueError as exc:
        return "输入不合法：%s" % exc

    for row in ROWS:
        if row["词汇"] == target:
            return "%s -> %s 级" % (target, row["HSK等级"])
    return "未找到 %s" % target


@mcp.tool()
def list_by_level(level: str) -> str:
    """列出某一 HSK 等级的全部词汇。

    参数 level：等级数字（1-9），例如「3」；也接受「HSK3」「3级」。
    返回：用顿号分隔的词汇；该等级没有词时返回「x 级暂无词汇」。
    """
    try:
        lv = _normalize_level(level)
    except ValueError as exc:
        return "输入不合法：%s" % exc

    words = [row["词汇"] for row in ROWS if row["HSK等级"] == lv]
    return "、".join(words) if words else "%s 级暂无词汇" % lv


if __name__ == "__main__":
    # stdout 是 JSON-RPC 通道，启动日志必须走 stderr
    print("[hsk-tools] 数据文件：%s" % VOCAB, file=sys.stderr)
    print(
        "[hsk-tools] 已加载 %d 条词汇；stdio 服务已启动，等待客户端连接……"
        % len(ROWS),
        file=sys.stderr,
    )
    mcp.run()
