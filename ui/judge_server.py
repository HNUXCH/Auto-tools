"""Flask 判题服务器 — 本地 OJ (Online Judge) 后端。

提供题目浏览、代码编辑、自动判题功能。
前端：HTML + CodeMirror + marked.js（SPA）
后端：Flask + subprocess 执行用户代码
"""

from __future__ import annotations

import html as html_mod
import io
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

# 题目文件目录（由 code_judge Tool 在启动时设置）
_problems_dir: Path | None = None

# CSP 题目 Markdown 示例的输入/输出提取正则
_SAMPLE_RE = re.compile(
    r"```input(\d*)\s*\n(.*?)```\s*\n+```output\1\s*\n(.*?)```",
    re.DOTALL,
)

# 判题超时（秒）
_JUDGE_TIMEOUT = 5


def set_problems_dir(path: Path) -> None:
    global _problems_dir
    _problems_dir = path


def _get_problems_dir() -> Path:
    if _problems_dir is None:
        raise RuntimeError("题目目录未设置")
    return _problems_dir


# ── 题目数据 ──────────────────────────────────────


def _parse_problems() -> list[dict]:
    """扫描题目目录，解析 Markdown，返回题目列表。"""
    problems: list[dict] = []
    md_dir = _get_problems_dir()
    for md_path in sorted(md_dir.glob("*.md")):
        content = md_path.read_text(encoding="utf-8")
        title = _extract_title(content, md_path.stem)
        samples = _extract_samples(content)
        problems.append({
            "id": md_path.stem,
            "title": title,
            "content": content,
            "sample_count": len(samples) // 2,
        })
    return problems


def _extract_title(content: str, fallback: str) -> str:
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# ") and not line.startswith("## "):
            return line[2:].strip()
    return fallback


def _unescape_content(content: str) -> str:
    """将 JSON 转义序列还原为真实字符。

    Hydro OJ 的 content 字段是 JSON 字符串，\\n 等序列被储存为字面量。
    """
    import codecs
    try:
        return codecs.decode(content, "unicode_escape")
    except Exception:
        return content


def _extract_samples(content: str) -> list[str]:
    """提取样例：返回 [input1, output1, input2, output2, ...]。

    先尝试原始内容匹配，失败则 unescape 后再试。
    """
    samples: list[str] = []

    def _try_match(text: str) -> bool:
        for m in _SAMPLE_RE.finditer(text):
            samples.append(m.group(2).strip())
            samples.append(m.group(3).strip())
        return len(samples) > 0

    _try_match(content)
    if not samples:
        # Hydro OJ 的 JSON 把 \\n 存成了字面量，需要 decode
        _try_match(_unescape_content(content))

    return samples


# ── 判题引擎 ──────────────────────────────────────


def _run_judge(code: str, samples: list[str]) -> dict:
    """执行用户代码，用样例测试，返回结果。"""
    results: list[dict] = []
    passed = 0
    total = len(samples) // 2

    for i in range(0, len(samples), 2):
        sample_in = samples[i]
        expected_out = samples[i + 1] if i + 1 < len(samples) else ""
        case_num = i // 2 + 1

        result = {
            "case": case_num,
            "status": "pending",
            "input": sample_in[:200],
            "expected": expected_out[:200],
            "actual": "",
            "time_ms": 0,
            "error": "",
        }

        try:
            start = time.perf_counter()
            proc = subprocess.run(
                ["python", "-c", code],
                input=sample_in,
                capture_output=True,
                text=True,
                timeout=_JUDGE_TIMEOUT,
            )
            elapsed = (time.perf_counter() - start) * 1000
            result["time_ms"] = round(elapsed, 1)

            if proc.returncode != 0:
                result["status"] = "runtime_error"
                result["error"] = proc.stderr[:500] or f"Exit code {proc.returncode}"
            else:
                actual = proc.stdout.strip()
                expected = expected_out.strip()
                result["actual"] = actual[:500]
                if actual == expected:
                    result["status"] = "accepted"
                    passed += 1
                else:
                    result["status"] = "wrong_answer"
                    # 显示差异提示
                    if len(actual) < 100 and len(expected) < 100:
                        result["error"] = f"期望: {expected}\n实际: {actual}"

        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = f"超时 ({_JUDGE_TIMEOUT}s)"

        results.append(result)

    return {
        "passed": passed,
        "total": total,
        "results": results,
        "all_pass": passed == total and total > 0,
    }


# ── API 路由 ──────────────────────────────────────


@app.route("/")
def index() -> str:
    """返回主页面 HTML（SPA）。"""
    return _HTML_PAGE


@app.route("/api/problems")
def api_problems():
    """返回所有题目列表。"""
    try:
        problems = _parse_problems()
        return jsonify([
            {"id": p["id"], "title": p["title"], "sample_count": p["sample_count"]}
            for p in problems
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/problem/<pid>")
def api_problem(pid: str):
    """返回单个题目的详细信息（含 Markdown 和样例解析结果）。"""
    try:
        md_path = _get_problems_dir() / f"{pid}.md"
        if not md_path.exists():
            return jsonify({"error": "题目不存在"}), 404

        content = md_path.read_text(encoding="utf-8")
        title = _extract_title(content, pid)
        samples = _extract_samples(content)

        # 构建样例展示（配对展示）
        sample_pairs = []
        for i in range(0, len(samples), 2):
            sample_pairs.append({
                "input": samples[i],
                "output": samples[i + 1] if i + 1 < len(samples) else "",
            })

        return jsonify({
            "id": pid,
            "title": title,
            "content": content,
            "samples": sample_pairs,
            "sample_count": len(sample_pairs),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/run", methods=["POST"])
def api_run():
    """执行用户代码并返回判题结果。"""
    try:
        data = request.get_json(force=True)
        code = data.get("code", "")
        pid = data.get("problem_id", "")

        if not code.strip():
            return jsonify({"error": "代码不能为空"}), 400

        # 解析题目样例
        if pid:
            md_path = _get_problems_dir() / f"{pid}.md"
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                samples = _extract_samples(content)
            else:
                samples = []
        else:
            samples = []

        if not samples:
            return jsonify({"error": "该题目没有样例数据"}), 400

        result = _run_judge(code, samples)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 前端 HTML ─────────────────────────────────────


_HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Auto-tools OJ</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/theme/monokai.min.css">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "Microsoft YaHei", sans-serif; height: 100vh; display: flex; flex-direction: column; }
header { background: #1a1a2e; color: #fff; padding: 6px 16px; display: flex; align-items: center; gap: 16px; font-size: 14px; }
header h1 { font-size: 16px; }
header select { padding: 4px 8px; border-radius: 4px; border: none; font-size: 13px; min-width: 180px; }

.main { display: flex; flex: 1; overflow: hidden; }
.panel-left { width: 45%; border-right: 1px solid #ddd; display: flex; flex-direction: column; overflow: hidden; }
.panel-right { width: 55%; display: flex; flex-direction: column; overflow: hidden; }
.panel-left-header { padding: 8px 12px; background: #f5f5f5; border-bottom: 1px solid #ddd; font-weight: bold; font-size: 13px; }
.panel-left-body { flex: 1; overflow-y: auto; padding: 12px 16px; }
.panel-right-header { padding: 6px 10px; background: #f5f5f5; border-bottom: 1px solid #ddd; display: flex; align-items: center; justify-content: space-between; font-size: 13px; }
.editor-wrap { flex: 1; overflow: hidden; }
.editor-wrap .CodeMirror { height: 100% !important; }
.result-panel { max-height: 200px; overflow-y: auto; border-top: 1px solid #ddd; background: #fafafa; }
.result-item { padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 13px; display: flex; align-items: flex-start; gap: 8px; }
.result-item.pass { background: #e8f5e9; }
.result-item.fail { background: #ffebee; }
.result-item .icon { font-size: 16px; min-width: 20px; }
.result-item .info { flex: 1; }
.result-item .info .detail { font-size: 11px; color: #666; margin-top: 2px; white-space: pre-wrap; }
.btn { padding: 5px 14px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-run { background: #4caf50; color: #fff; }
.btn-run:hover { background: #388e3c; }
.btn-run:disabled { background: #9e9e9e; cursor: not-allowed; }
.summary { padding: 6px 12px; font-size: 13px; font-weight: bold; }
.summary.success { color: #2e7d32; }
.summary.fail { color: #c62828; }

/* Markdown styles */
.markdown { font-size: 13px; line-height: 1.7; color: #333; }
.markdown h1,.markdown h2,.markdown h3 { margin: 8px 0 4px; color: #1a1a2e; }
.markdown h2 { font-size: 15px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
.markdown p { margin: 4px 0; }
.markdown code { background: #f0f0f0; padding: 1px 4px; border-radius: 2px; font-size: 12px; }
.markdown pre { background: #f5f5f5; padding: 8px 12px; border-radius: 4px; overflow-x: auto; font-size: 12px; margin: 4px 0; }
.markdown ul,.markdown ol { padding-left: 20px; }
</style>
</head>
<body>

<header>
  <h1>⚡ Auto-tools OJ</h1>
  <span style="color:#aaa">|</span>
  <select id="problemSelect" onchange="loadProblem()">
    <option value="">-- 选择题目 --</option>
  </select>
  <span style="font-size:12px;color:#aaa;flex:1"></span>
  <span style="font-size:12px;color:#aaa">Python 3</span>
</header>

<div class="main">
  <div class="panel-left">
    <div class="panel-left-header" id="problemTitle">请选择题目</div>
    <div class="panel-left-body markdown" id="problemBody">
      <p style="color:#999">← 从上方下拉框选择一道 CSP 真题</p>
    </div>
  </div>
  <div class="panel-right">
    <div class="panel-right-header">
      <span>💻 代码编辑器</span>
      <button class="btn btn-run" id="runBtn" onclick="runCode()">▶ 运行测试</button>
    </div>
    <div class="editor-wrap" id="editorWrap"></div>
    <div class="result-panel" id="resultPanel" style="display:none"></div>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/python/python.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.0/marked.min.js"></script>

<script>
var editor = CodeMirror(document.getElementById('editorWrap'), {
  mode: 'python',
  theme: 'monokai',
  lineNumbers: true,
  indentUnit: 4,
  tabSize: 4,
  value: '# 选择题目后开始写代码\n',
});

var currentProblem = null;

// 加载题目列表
fetch('/api/problems')
  .then(r => r.json())
  .then(problems => {
    var sel = document.getElementById('problemSelect');
    problems.forEach(function(p) {
      var opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.id + ' - ' + p.title;
      sel.appendChild(opt);
    });
  })
  .catch(console.error);

function loadProblem() {
  var pid = document.getElementById('problemSelect').value;
  if (!pid) return;

  fetch('/api/problem/' + pid)
    .then(r => r.json())
    .then(function(data) {
      currentProblem = data;
      document.getElementById('problemTitle').textContent = data.id + '. ' + data.title;
      document.getElementById('problemBody').innerHTML = marked.parse(data.content);
      document.getElementById('resultPanel').style.display = 'none';
      editor.setValue('# ' + data.id + '. ' + data.title + '\n# 在这里写你的 Python 代码...\n\n');
    })
    .catch(console.error);
}

function runCode() {
  if (!currentProblem) { alert('请先选择题目'); return; }
  var code = editor.getValue();
  var btn = document.getElementById('runBtn');
  btn.disabled = true;
  btn.textContent = '⏳ 运行中...';

  fetch('/api/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({code: code, problem_id: currentProblem.id})
  })
    .then(r => r.json())
    .then(function(res) {
      btn.disabled = false;
      btn.textContent = '▶ 运行测试';

      var panel = document.getElementById('resultPanel');
      panel.style.display = 'block';

      var html = '';
      if (res.passed !== undefined) {
        var cls = res.all_pass ? 'success' : 'fail';
        html += '<div class="summary ' + cls + '">' +
          (res.all_pass ? '✓ 全部通过' : '✗ 未通过') +
          ' (' + res.passed + '/' + res.total + ')' +
          '</div>';
      } else {
        html += '<div class="summary fail">错误: ' + (res.error || '未知') + '</div>';
      }

      (res.results || []).forEach(function(r) {
        var cls = r.status === 'accepted' ? 'pass' : 'fail';
        var icon = r.status === 'accepted' ? '✅' :
                   r.status === 'wrong_answer' ? '❌' :
                   r.status === 'timeout' ? '⏱️' : '💥';
        var statusText = r.status === 'accepted' ? '通过' :
                         r.status === 'wrong_answer' ? '答案错误' :
                         r.status === 'timeout' ? '超时' : '运行错误';

        html += '<div class="result-item ' + cls + '">' +
          '<span class="icon">' + icon + '</span>' +
          '<div class="info">' +
            '<b>样例 ' + r.case + '</b> — ' + statusText +
            (r.time_ms ? ' (' + r.time_ms + 'ms)' : '') +
            (r.error ? '<div class="detail">' + r.error + '</div>' : '') +
          '</div>' +
        '</div>';
      });

      panel.innerHTML = html;
    })
    .catch(function(err) {
      btn.disabled = false;
      btn.textContent = '▶ 运行测试';
      console.error(err);
    });
}
</script>
</body>
</html>"""
