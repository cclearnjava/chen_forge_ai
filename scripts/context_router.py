#!/usr/bin/env python3
"""Context Router — 文件路径 → 上下文片段路由表。

ADR-030 机制 A（主动投影）的核心。根据被编辑文件的路径，
确定性地返回该文件相关的上下文片段名列表。

Usage:
    from scripts.context_router import match, load_fragment, FALLBACK_FRAGMENTS

    fragments = match("bridge_agent/agent.py")
    # → ["bridge-constitution"]
"""
from __future__ import annotations

from pathlib import Path

FRAGMENTS_DIR = Path(__file__).resolve().parent / "context-fragments"

# ── 路由表：文件路径前缀 → 上下文片段名列表 ──
# 完全按 ADR-030 Section 3.4.1 定义
CONTEXT_MAP: dict[str, list[str]] = {
    # Bridge
    "bridge_agent/":                        ["bridge-constitution"],
    "backend/product/bridge/":              ["bridge-constitution"],

    # MCP 双端
    "mcp-server/":                          ["mcp-parity"],
    "mcp-server-node/":                     ["mcp-parity"],

    # 协议 API（多消费方契约）
    "backend/product/routes/protocol.py":   ["protocol-consumers", "contract-consumers"],
    "backend/product/protocol/":            ["protocol-consumers"],

    # API 路由层（契约定义点）
    "backend/product/routes/":              ["contract-consumers"],

    # run_events（6 个消费方的共享结构）
    "backend/product/db/crud_events.py":    ["run-events-consumers"],

    # 认证（消费方安全约定 + SecondMe OAuth）
    "backend/product/auth/":                ["auth-consumers"],

    # DB 层（共享数据结构约定）
    "backend/product/db/":                  ["db-shared-structures"],

    # 分布式协商核心
    "backend/product/catalyst/":            ["catalyst-distributed"],

    # Issue / 修复
    "docs/issues/":                         ["fixed-three-layers", "closure-checklist"],

    # 场景
    "scenes/":                              ["scene-fidelity", "two-language"],
    "website/app/[scene]/":                 ["scene-fidelity", "two-language"],
    "website/components/scene/":            ["scene-fidelity", "two-language"],

    # 真相源文件
    "CLAUDE.md":                            ["truth-source-hierarchy"],
    "MEMORY.md":                            ["truth-source-hierarchy"],
    "docs/INDEX.md":                        ["truth-source-hierarchy"],

    # 版本号
    "mcp-server/pyproject.toml":            ["version-sources"],
    "mcp-server-node/package.json":         ["version-sources"],

    # 前端通用
    "website/":                             ["two-language"],

    # 文档
    "docs/decisions/":                      ["artifact-linkage"],

    # Issue-first 工作流 — 编辑业务代码时提醒先建 issue
    "backend/product/":                     ["issue-first"],
    "backend/server.py":                    ["issue-first"],
    "mcp-server/towow_mcp/":               ["issue-first"],
    "mcp-server-node/src/":                ["issue-first"],
    "website/app/":                         ["issue-first"],
}

# 未匹配任何路由的文件，由 guard-feedback.py 注入此 fallback
FALLBACK_FRAGMENTS = ["general-dev-principles"]


def match(file_path: str) -> list[str]:
    """返回匹配的上下文片段名列表。最长前缀优先，去重保序。"""
    matched: list[str] = []
    for pattern, fragments in sorted(
        CONTEXT_MAP.items(), key=lambda x: -len(x[0])
    ):
        if file_path.startswith(pattern) or file_path.endswith(pattern):
            matched.extend(fragments)
    # 去重保序
    return list(dict.fromkeys(matched))


def load_fragment(name: str) -> str:
    """加载片段文件内容。返回空字符串如果文件不存在。"""
    path = FRAGMENTS_DIR / f"{name}.md"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""
