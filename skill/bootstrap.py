#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
播客技能自举启动器（自动化沙箱专用）

手工创建的 skill 目录**不会同步**到自动化任务的临时沙箱
（实测：任务沙箱里 /root/.codebuddy/skills/text-to-podcast 不存在）。
所以这里把真正的发布脚本 podcast.py 托管在 GitHub 仓库里，
本启动器负责：① 本地有则直接用 ② 否则从多个源依次下载 ③ 转发全部参数执行。

用法（与 podcast.py 参数完全一致）:
  python3 bootstrap.py --title "第N期 标题" --script /tmp/ep.txt
  curl -fsSL https://lenzenki.github.io/podcast/skill/bootstrap.py | python3 - --title "..." --script -
"""
import os
import subprocess
import sys
import tempfile
import urllib.request
import hashlib

SOURCES = [
    "https://lenzenki.github.io/podcast/skill/podcast.py",              # Pages，最快
    "https://cdn.jsdelivr.net/gh/lenzenki/podcast@main/skill/podcast.py",
    "https://raw.githubusercontent.com/lenzenki/podcast/main/skill/podcast.py",
]

# 自举入口自身的镜像（供 curl 拉不到 Pages 时手动降级）
BOOTSTRAP_MIRRORS = [
    "https://cdn.jsdelivr.net/gh/lenzenki/podcast@main/skill/bootstrap.py",
    "https://raw.githubusercontent.com/lenzenki/podcast/main/skill/bootstrap.py",
]

LOCAL_CANDIDATES = [
    os.path.expanduser("~/.codebuddy/skills/text-to-podcast/scripts/podcast.py"),
    "/workspace/.podcast/podcast.py",
]

MIN_SIZE = 8000      # 防止下到错误页
MAX_SIZE = 400000


def log(m):
    print(m, flush=True)


def find_local():
    for p in LOCAL_CANDIDATES:
        if os.path.exists(p) and MIN_SIZE < os.path.getsize(p) < MAX_SIZE:
            return p
    return None


def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "podcast-bootstrap"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if not (MIN_SIZE < len(data) < MAX_SIZE):
        raise ValueError("内容大小异常 %dB" % len(data))
    head = data[:60]
    if b"python" not in head and b"#!" not in head:
        raise ValueError("下载到的不是脚本")
    with open(dest, "wb") as f:
        f.write(data)
    return hashlib.sha256(data).hexdigest()[:12]


def main():
    args = sys.argv[1:]

    cache = os.path.join(tempfile.gettempdir(), "podcast_publisher.py")
    path = find_local()
    if path:
        log("[bootstrap] 使用本地脚本: %s" % path)
    else:
        if os.path.exists(cache) and MIN_SIZE < os.path.getsize(cache) < MAX_SIZE:
            path = cache
            log("[bootstrap] 使用缓存脚本")
        else:
            for src in SOURCES:
                try:
                    log("[bootstrap] 下载 %s" % src)
                    sha = fetch(src, cache)
                    path = cache
                    log("[bootstrap] ✅ 已获取脚本（sha %s）" % sha)
                    break
                except Exception as e:
                    log("[bootstrap] ❌ %s: %s" % (src, str(e)[:120]))
            if not path:
                print("❌ 所有下载源都失败，无法获取发布脚本", file=sys.stderr)
                sys.exit(4)

    sys.exit(subprocess.call([sys.executable, path] + args))


if __name__ == "__main__":
    main()
