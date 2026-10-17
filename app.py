import ast
import json
import shutil
import subprocess
import tempfile
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST, PORT = "127.0.0.1", 8000
MAX_CODE = 100_000
LANGUAGES = {
    "python": ("Python", ".py", None),
    "c": ("C", ".c", "gcc"),
    "cpp": ("C++", ".cpp", "g++"),
    "java": ("Java", ".java", "javac"),
    "javascript": ("JavaScript", ".js", "node"),
}

# The interface is embedded in this Python file; no separate frontend files are needed.
PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VisionFix — Code Inspector</title>
<style>
:root{color-scheme:dark;--bg:#0a1020;--panel:#111a2d;--line:#293650;--text:#edf3ff;--muted:#93a2be;--purple:#b19aff;--cyan:#68e4d2;--red:#ff9ca9;--amber:#ffd08a}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 10% 0%,#292052 0,transparent 36%),radial-gradient(ellipse at 100% 35%,#123b43 0,transparent 30%),var(--bg);font:14px "Segoe UI",Arial,sans-serif;color:var(--text);min-height:100vh}
header{height:76px;border-bottom:1px solid #ffffff13;display:flex;align-items:center;justify-content:space-between;padding:0 max(22px,calc((100vw - 1000px)/2))}
.brand{display:flex;align-items:center;gap:11px;font-weight:800;font-size:19px;letter-spacing:-.6px}.brand em{font-style:normal;color:var(--purple)}.brand small{display:block;font:8px Consolas,monospace;letter-spacing:1.5px;color:#8290ad;margin-top:5px}.logo{width:32px;height:32px;border:1px solid #4b5078;border-radius:9px;display:flex;align-items:center;justify-content:center;gap:3px;background:#171e36}.logo i{display:block;width:4px;border-radius:5px;background:var(--purple)}.logo i:nth-child(1){height:10px}.logo i:nth-child(2){height:18px;background:var(--cyan)}.logo i:nth-child(3){height:13px}.pill{font-size:11px;color:#a7b5cc;border:1px solid #34445a;border-radius:22px;padding:8px 12px}.pill:before{content:"";display:inline-block;width:6px;height:6px;background:var(--cyan);border-radius:50%;margin-right:8px}
main{max-width:980px;margin:auto;padding:0 22px}.hero{text-align:center;padding:64px 0 40px}.eyebrow,.kicker{font:10px Consolas,monospace;letter-spacing:1.5px;color:#b9b3f5}.eyebrow{display:inline-block;border:1px solid #3b4263;border-radius:22px;padding:9px 13px;background:#15182b}.hero h1{font-size:clamp(40px,6vw,66px);letter-spacing:-3px;line-height:1.06;margin:22px 0 17px}.hero h1 span{background:linear-gradient(100deg,#b39aff,#68e4d2);color:transparent;background-clip:text}.hero p{color:var(--muted);line-height:1.8;margin:0}.stats{display:flex;align-items:center;justify-content:center;gap:28px;margin-top:28px}.stat strong{display:block;font:20px Consolas,monospace}.stat small{display:block;font:9px Consolas,monospace;color:#8492ae;letter-spacing:1px;margin-top:5px}.sep{width:1px;height:28px;background:#34405a}
.workspace{border:1px solid #2d3a55;background:#111a2dec;border-radius:16px;padding:23px;box-shadow:0 25px 80px #0003}.heading{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}.heading h2,.section h2{font-size:22px;letter-spacing:-.6px;margin:7px 0 0}.privacy{font-size:10px;color:#9aabc5}.privacy b{color:var(--cyan)}.editor{border:1px solid #303d58;border-radius:10px;overflow:hidden;background:#0a1120}.bar{height:41px;background:#172137;border-bottom:1px solid #293650;display:flex;align-items:center;justify-content:space-between;padding:0 14px;color:#dce6f8;font:11px Consolas,monospace}.file:before{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;background:#f0bf69;margin-right:9px}.ready{color:#8492ae;font-size:10px}.controls{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid #202c42}.controls label{font:9px Consolas,monospace;color:#8492ae;letter-spacing:1px}.controls select{background:#1b263d;border:1px solid #3a4763;color:#e8efff;padding:8px;border-radius:6px}.spacer{flex:1}button{font-family:inherit;cursor:pointer}.plain{background:transparent;border:0;color:#a2afc8;font-size:11px;padding:7px 5px}.plain:hover{color:white}.codebox{display:flex;min-height:230px}.gutter{min-width:43px;padding:15px 12px;text-align:right;border-right:1px solid #1c2740;color:#4c5b79;font:12px/1.9 Consolas,monospace;white-space:pre;user-select:none}.codebox textarea{display:block;flex:1;min-width:0;min-height:230px;resize:vertical;border:0;outline:0;background:transparent;color:#dce8fb;padding:15px 17px;font:12px/1.9 Consolas,monospace;tab-size:4;white-space:pre;overflow:auto}.codebox textarea::placeholder{color:#53617d}.editorfoot{height:33px;display:flex;justify-content:space-between;align-items:center;padding:0 13px;border-top:1px solid #202b40;color:#7785a0;font:9px Consolas,monospace}.action{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-top:16px}.safe{display:flex;gap:10px;align-items:center}.safe .symbol{font-size:19px;color:var(--cyan)}.safe strong{display:block;font-size:11px}.safe small{display:block;color:#8492ad;font-size:10px;margin-top:4px}.primary{display:flex;align-items:center;gap:12px;border:0;border-radius:8px;background:linear-gradient(100deg,#b19aff,#77dacf);color:#11172a;font-weight:700;padding:13px 18px}.primary:hover{filter:brightness(1.08)}.primary:disabled{opacity:.6;cursor:wait}
.results{margin-top:20px;border:1px solid #33405a;border-radius:10px;padding:18px;background:#0b1425}.hidden{display:none!important}.resulthead{display:flex;justify-content:space-between;gap:12px;align-items:center}.resultlabel{display:flex;gap:11px;align-items:center}.resulticon{width:34px;height:34px;display:grid;place-items:center;border-radius:9px;background:#173a37;color:var(--cyan);font-size:18px}.resulticon.error{background:#472631;color:var(--red)}.resulticon.warning{background:#45351e;color:var(--amber)}.resulthead h3{font-size:16px;margin:5px 0 0}.tool{font:10px Consolas,monospace;color:#a5b2ca;border:1px solid #35415b;border-radius:20px;padding:7px 9px}.summary{font-size:12px;color:#aab7ce;line-height:1.7;margin:16px 0}.issue{border:1px solid #2c3850;border-radius:7px;background:#111b2f;padding:11px;margin-top:8px}.issue-meta{font:10px Consolas,monospace;color:#ffb7a6;margin-bottom:6px}.issue-msg{font:11px/1.7 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere}.solution{margin-top:14px;border:1px solid #35534f;background:#102522;border-radius:9px;padding:14px}.solution h4{margin:0 0 7px;font-size:12px;color:#8ee5c7}.solution p{font-size:11px;line-height:1.8;color:#c1d6d1;margin:0 0 10px}.solution pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#091a18;border:1px solid #28413d;border-radius:7px;padding:12px;color:#d6f4eb;font:11px/1.7 Consolas,monospace;max-height:260px;overflow:auto}.fixactions{display:flex;gap:9px;flex-wrap:wrap}.fixbtn{border:1px solid #4b8d7c;background:#1a4a40;color:#d8fff3;padding:9px 12px;border-radius:7px;font-size:11px}.fixbtn:hover{filter:brightness(1.12)}.tips{border-top:1px solid #29344c;margin-top:15px;padding-top:13px}.tips h4{font-size:11px;margin:0 0 7px}.tips ul{margin:0;padding-left:18px;font-size:11px;line-height:1.9;color:#9eacc5}
.section{padding:62px 0 24px}.sectionhead{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:20px}.sectionhead p{max-width:290px;color:#8998b3;font-size:11px;line-height:1.8;margin:0}.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}.langcard{display:flex;align-items:center;gap:9px;border:1px solid #26334c;background:#111a2d;border-radius:9px;padding:13px 10px}.langicon{width:30px;height:30px;display:grid;place-items:center;flex:0 0 30px;border-radius:8px;font:11px Consolas,monospace}.py{background:#393426;color:#ffdc7c}.c{background:#1d3249;color:#8fc4ff}.cpp{background:#282f50;color:#a8b9ff}.java{background:#412b2a;color:#ffb79b}.js{background:#3b3825;color:#ffe477}.langcard strong{font-size:11px;display:block}.langcard small{font-size:9px;line-height:1.4;color:#8492ad;display:block;margin-top:4px}.note{display:flex;gap:11px;margin-top:14px;padding:14px;border:1px solid #2d414f;border-radius:9px;background:#101f2a;color:#91a2ba;font-size:10px;line-height:1.8}.note b{color:#cbd8e9}.info{flex:0 0 19px;width:19px;height:19px;border:1px solid #477e7c;border-radius:50%;display:grid;place-items:center;color:var(--cyan)}.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}.step{border-left:1px solid #3d4563;padding-left:16px}.stepno{font:11px Consolas,monospace;color:var(--cyan)}.step h3{font-size:13px;margin:12px 0 7px}.step p{font-size:11px;line-height:1.8;color:#8796b0;margin:0}footer{min-height:80px;display:flex;align-items:center;justify-content:space-between;border-top:1px solid #202b40;color:#7d8ba5;font-size:10px;margin-top:30px}.footbrand{font-weight:800;font-size:15px;color:#e9efff}.footbrand em{font-style:normal;color:var(--purple)}
@media(max-width:740px){header{padding:0 16px;height:68px}main{padding:0 14px}.hero{padding:52px 0 36px}.hero h1{letter-spacing:-2px}.hero p{font-size:12px}.stats{gap:13px}.stat strong{font-size:17px}.stat small{font-size:7px;letter-spacing:.4px}.workspace{padding:14px}.heading{align-items:flex-start}.privacy{max-width:125px;text-align:right;line-height:1.6}.controls{gap:6px;padding:9px}.controls label{display:none}.controls select{max-width:120px}.plain{font-size:10px}.grid{grid-template-columns:repeat(2,1fr)}.langcard:last-child{grid-column:span 2}.sectionhead{align-items:flex-start;flex-direction:column;gap:10px}.steps{grid-template-columns:1fr;gap:22px}.action{align-items:stretch;flex-direction:column}.primary{justify-content:center}.resulthead{align-items:flex-start}footer{gap:10px}footer span:last-child{text-align:right}}
</style></head><body>
<header><div class="brand"><span class="logo"><i></i><i></i><i></i></span><span>Vision<em>Fix</em><small>CODE DIAGNOSTICS</small></span></div><span class="pill">Runs on your computer</span></header>
<main><section class="hero"><div class="eyebrow">✦ &nbsp; YOUR PERSONAL CODE CHECKER</div><h1>Less debugging.<br><span>More building.</span></h1><p>Paste your code. Check syntax. Get a clearer next step.<br>No login or third-party AI account required.</p><div class="stats"><div class="stat"><strong>05</strong><small>LANGUAGES</small></div><div class="sep"></div><div class="stat"><strong>0</strong><small>LOGIN REQUIRED</small></div><div class="sep"></div><div class="stat"><strong>LOCAL</strong><small>BY DEFAULT</small></div></div></section>
<section class="workspace"><div class="heading"><div><div class="kicker">WORKSPACE / ANALYZE</div><h2>Code inspector</h2></div><div class="privacy"><b>◆</b> Code stays on this computer</div></div>
<div class="editor"><div class="bar"><span class="file" id="filename">main.py</span><span class="ready">● Ready to inspect</span></div><div class="controls"><label for="language">LANGUAGE</label><select id="language"><option value="python">Python</option><option value="c">C</option><option value="cpp">C++</option><option value="java">Java</option><option value="javascript">JavaScript</option></select><span class="spacer"></span><button class="plain" id="example">↻ Load example</button><button class="plain" id="clear">Clear</button></div><div class="codebox"><div class="gutter" id="gutter">1</div><textarea id="code" spellcheck="false" autocomplete="off" placeholder="# Paste your code here..." aria-label="Paste code here"></textarea></div><div class="editorfoot"><span>Ctrl + Enter to inspect</span><span id="count">0 characters</span></div></div>
<div class="action"><div class="safe"><span class="symbol">✳</span><span><strong>Safe by design</strong><small>VisionFix checks syntax; it does not run your program.</small></span></div><button class="primary" id="analyze">⌕ &nbsp; Analyze code &nbsp; →</button></div>
<div id="results" class="results hidden" aria-live="polite"><div class="resulthead"><div class="resultlabel"><span id="resulticon" class="resulticon">✓</span><div><div class="kicker">ANALYSIS REPORT</div><h3 id="resulttitle">Syntax check passed</h3></div></div><span class="tool" id="tool">Python parser</span></div><p class="summary" id="summary"></p><div id="issues"></div><div id="solution" class="solution hidden"><h4>✦ Suggested solution</h4><p id="solutiontext"></p><pre id="fixedcode" class="hidden"></pre><div class="fixactions"><button id="applyfix" class="fixbtn hidden">Apply suggested fix to editor</button><button id="copyfix" class="fixbtn hidden">Copy corrected code</button></div></div><div class="tips" id="tipsbox"><h4>Next steps</h4><ul id="tips"></ul></div></div></section>
<section class="section"><div class="sectionhead"><div><div class="kicker">SUPPORTED LANGUAGES</div><h2>One workspace. Five languages.</h2></div><p>One simple workflow for the languages you study and build with.</p></div><div class="grid"><div class="langcard"><span class="langicon py">Py</span><span><strong>Python</strong><small>Built-in parser</small></span></div><div class="langcard"><span class="langicon c">C</span><span><strong>C</strong><small>GCC if installed</small></span></div><div class="langcard"><span class="langicon cpp">C++</span><span><strong>C++</strong><small>G++ if installed</small></span></div><div class="langcard"><span class="langicon java">Jv</span><span><strong>Java</strong><small>JDK if installed</small></span></div><div class="langcard"><span class="langicon js">JS</span><span><strong>JavaScript</strong><small>Node.js if installed</small></span></div></div><div class="note"><span class="info">i</span><span><b>Good to know:</b> Python checking works with Python itself. Full C, C++, Java and JavaScript checks need their compiler/runtime installed and available on PATH. If a tool is missing, VisionFix explains this and performs only a basic delimiter check.</span></div></section>
<section class="section"><div class="kicker">BUILT FOR LEARNING</div><h2>Helpful, without the mystery.</h2><div class="steps" style="margin-top:25px"><div class="step"><span class="stepno">01</span><h3>Paste your code</h3><p>Choose a language and add the snippet you want to check.</p></div><div class="step"><span class="stepno">02</span><h3>Inspect syntax</h3><p>Python parses the code or calls an installed syntax checker.</p></div><div class="step"><span class="stepno">03</span><h3>Understand the result</h3><p>Review the reported message and practical next steps.</p></div></div></section>
<footer><span class="footbrand">Vision<em>Fix</em></span><span>Made for curious minds · Python-only edition</span></footer></main>
<script>
const $=id=>document.getElementById(id);
const examples={
python:'def greet(name):\\n    print("Hello, " + name)\\n\\ngreet("World")',
c:'#include <stdio.h>\\n\\nint main(void) {\\n    printf("Hello, world!\\\\n");\\n    return 0;\\n}',
cpp:'#include <iostream>\\nusing namespace std;\\n\\nint main() {\\n    cout << "Hello, world!" << endl;\\n    return 0;\\n}',
java:'public class Main {\\n    public static void main(String[] args) {\\n        System.out.println("Hello, world!");\\n    }\\n}',
javascript:'function greet(name) {\\n  console.log("Hello, " + name);\\n}\\n\\ngreet("World");'
};
const names={python:'main.py',c:'main.c',cpp:'main.cpp',java:'Main.java',javascript:'main.js'};
function meta(){let n=Math.max(1,$('code').value.split('\\n').length);$('gutter').textContent=Array.from({length:n},(_,i)=>i+1).join('\\n');$('count').textContent=$('code').value.length.toLocaleString()+' characters';$('filename').textContent=names[$('language').value];}
function loadExample(){$('code').value=examples[$('language').value].replaceAll('\\\\n','\\n');meta();$('results').classList.add('hidden');}
$('language').addEventListener('change',()=>{meta();$('results').classList.add('hidden')});$('code').addEventListener('input',meta);$('example').addEventListener('click',loadExample);
$('clear').addEventListener('click',()=>{$('code').value='';meta();$('results').classList.add('hidden');$('code').focus()});
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
let latestFixedCode=null;
function show(data){const s=data.status||'warning';$('resulticon').className='resulticon'+(s==='error'?' error':s==='warning'?' warning':'');$('resulticon').textContent=s==='success'?'✓':s==='error'?'!':'i';$('resulttitle').textContent=s==='success'?'Syntax check passed':s==='error'?'Issues found':'Partial check';$('summary').textContent=data.summary||'Analysis finished.';$('tool').textContent=data.tool||data.language||'VisionFix';$('issues').innerHTML='';(data.issues||[]).forEach(it=>{let d=document.createElement('div');d.className='issue';d.innerHTML='<div class="issue-meta">'+esc(it.line?'LINE '+it.line+(it.column?' · COLUMN '+it.column:''):'DIAGNOSTIC')+'</div><div class="issue-msg">'+esc(it.message)+'</div>'+(it.snippet?'<div class="snippet">↳ '+esc(it.snippet)+'</div>':'');$('issues').appendChild(d)});
const sol=data.solution||'No safe automatic correction is available for this exact error. Use the explanation above and check the first reported error.';$('solutiontext').textContent=sol;latestFixedCode=data.fixed_code||null;$('fixedcode').textContent=latestFixedCode||'';$('fixedcode').classList.toggle('hidden',!latestFixedCode);$('applyfix').classList.toggle('hidden',!latestFixedCode);$('copyfix').classList.toggle('hidden',!latestFixedCode);$('solution').classList.toggle('hidden',s==='success'&&!data.solution);
$('tips').innerHTML='';(data.tips||[]).forEach(t=>{let li=document.createElement('li');li.textContent=t;$('tips').appendChild(li)});$('tipsbox').classList.toggle('hidden',!(data.tips||[]).length);$('results').classList.remove('hidden');$('results').scrollIntoView({behavior:'smooth',block:'nearest'});}
$('applyfix').addEventListener('click',()=>{if(latestFixedCode!==null){$('code').value=latestFixedCode;meta();$('code').focus();$('summary').textContent='Suggested fix applied. Click Analyze code to validate it again.';}});
$('copyfix').addEventListener('click',async()=>{if(latestFixedCode!==null){try{await navigator.clipboard.writeText(latestFixedCode);$('copyfix').textContent='Copied!';}catch(e){$('solutiontext').textContent='Clipboard access was blocked. Select and copy the corrected code shown above.';}}});
$('analyze').addEventListener('click',async()=>{if(!$('code').value.trim()){$('code').focus();$('code').placeholder='Paste some code first, then click Analyze code...';return;}$('analyze').disabled=true;$('analyze').textContent='Analyzing…';try{let r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({language:$('language').value,code:$('code').value})});let d=await r.json();if(!r.ok)throw Error(d.error||'Analysis failed');show(d)}catch(e){show({status:'error',summary:e.message||'Could not connect to VisionFix.',tips:['Make sure the Python server is running.','Refresh the page and try again.']})}finally{$('analyze').disabled=false;$('analyze').textContent='⌕  Analyze code  →'}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();$('analyze').click()}});meta();
</script></body></html>"""

def basic_delimiter_check(language, code):
    stack, issues = [], []
    pairs = {")": "(", "]": "[", "}": "{"}
    quote = None
    escaped = False
    block_comment = False
    for line_no, line in enumerate(code.splitlines(), 1):
        i = 0
        while i < len(line):
            ch, nxt = line[i], line[i:i+2]
            if block_comment:
                if nxt == "*/":
                    block_comment = False
                    i += 2
                else:
                    i += 1
                continue
            if quote:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    quote = None
                i += 1
                continue
            if language in ("c", "cpp", "java", "javascript"):
                if nxt == "/*":
                    block_comment = True
                    i += 2
                    continue
                if nxt == "//":
                    break
            if language == "python" and ch == "#":
                break
            if ch in ("'", '"', "`"):
                quote = ch
            elif ch in "([{":
                stack.append((ch, line_no, i + 1))
            elif ch in ")]}":
                if not stack or stack[-1][0] != pairs[ch]:
                    issues.append({"line": line_no, "column": i+1, "message": f"Unexpected closing delimiter {ch!r}.", "snippet": line.strip()})
                    break
                stack.pop()
            i += 1
    if stack:
        ch, line_no, col = stack[-1]
        lines = code.splitlines()
        issues.append({"line": line_no, "column": col, "message": f"Possible unclosed delimiter {ch!r}.", "snippet": lines[line_no-1].strip() if line_no <= len(lines) else ""})
    if not issues:
        issues.append({"line": None, "column": None, "message": "No obvious delimiter issue found. This is a lightweight check, not a full parser.", "snippet": ""})
    return issues

def get_line(output):
    for pattern in (r":(\d+):\d+:", r"\.java:(\d+):", r"\((\d+),\d+\)"):
        match = re.search(pattern, output)
        if match:
            return int(match.group(1))
    return None

def build_solution(language, code, message, line_number=None):
    """Give plain-language guidance and only auto-edit very obvious Python cases."""
    low = (message or "").lower()
    lines = code.splitlines()
    if language == "python":
        if "expected ':'" in low and line_number and 1 <= line_number <= len(lines):
            original = lines[line_number - 1]
            stripped = original.rstrip()
            if stripped and not stripped.endswith(":") and not stripped.endswith((";", "\\")):
                # Only offer a patch when the parser explicitly asks for a colon.
                fixed_lines = lines[:]
                fixed_lines[line_number - 1] = stripped + ":"
                fixed = "\n".join(fixed_lines) + ("\n" if code.endswith("\n") else "")
                return ("Python expected a colon at the end of this statement. This commonly happens after if/elif/else, for/while, def, class, try/except, or with statements. Review the line before applying the suggested colon.", fixed)
        if "indentationerror" in low or "unexpected indent" in low or "unindent" in low:
            return ("Python indentation must be consistent. Use the same indentation style (usually 4 spaces), and make sure lines inside a block are indented while the next top-level statement is not.", None)
        if "never closed" in low or "was never closed" in low or "unexpected eof" in low:
            return ("A bracket or quote may be missing near the reported line or just above it. Match every opening (, [, { and quote with its closing partner. The parser's reported line can be where it noticed the problem, not where it began.", None)
        if "invalid syntax" in low:
            return ("Python could not parse this statement. Check the reported line and the line above it for a missing colon, unmatched quote/bracket, misspelled keyword, or accidental use of = where == was intended. No automatic edit is applied because several causes are possible.", None)
        if "unterminated string" in low:
            return ("A text string appears to start with a quote but not end with a matching quote. Check for matching single or double quotes on the reported line.", None)
        return ("Read the parser message and inspect the reported line plus the line immediately above it. Correct the first syntax error before checking later errors; no safe automatic edit was identified.", None)
    if "expected" in low and (":" in message or "semicolon" in low):
        return ("The compiler/parser expected a punctuation mark or token near this location. Inspect the reported line and the one before it; missing braces, semicolons, parentheses, or commas can cause follow-up errors.", None)
    if "cannot find symbol" in low or "undeclared" in low:
        return ("A variable, function, or name may be misspelled or not declared in this scope. Check capitalization and confirm the name is declared before use.", None)
    if "expected ';'" in low or "expected ;" in low:
        return ("This language likely needs a semicolon at the end of the reported statement. Check the exact compiler location before adding it.", None)
    if "not found" in low or "not recognized" in low or "not installed" in low:
        return ("The required compiler or runtime may be missing or unavailable on PATH. Install the appropriate tool and reopen the terminal before trying again.", None)
    return ("Start with the first diagnostic. Compiler messages can be cascading errors, so fix the earliest reported issue first. Check punctuation, spelling, declarations, and matching brackets; VisionFix cannot safely infer every intended correction.", None)

def analyze(language, code):
    language = language.strip().lower()
    if language not in LANGUAGES:
        return 400, {"error": "Choose Python, C, C++, Java, or JavaScript."}
    if not code.strip():
        return 400, {"error": "Please paste some code first."}
    if len(code) > MAX_CODE:
        return 413, {"error": "Code is too large. Keep it under 100,000 characters."}
    label, extension, tool = LANGUAGES[language]
    if language == "python":
        try:
            ast.parse(code)
            return 200, {"language": label, "status": "success", "summary": "Python syntax looks valid.", "issues": [], "tips": ["This checks syntax only; it cannot prove the program's logic is correct.", "Test your code with expected inputs."], "tool": "Python AST parser"}
        except SyntaxError as e:
            msg = e.msg or "Syntax error"
            solution, fixed_code = build_solution(language, code, msg, e.lineno)
            result = {"language": label, "status": "error", "summary": "Python found a syntax error. Review the suggested explanation before changing your code.", "issues": [{"line": e.lineno or 1, "column": e.offset or 1, "message": msg, "snippet": (e.text or "").strip()}], "solution": solution, "tips": ["The reported line may be where Python noticed the problem, not where it began.", "After applying a suggested fix, run Analyze code again.", "Syntax checks cannot confirm that the program's logic is correct."], "tool": "Python AST parser"}
            if fixed_code is not None:
                result["fixed_code"] = fixed_code
            return 200, result
    executable = shutil.which(tool)
    if not executable:
        return 200, {"language": label, "status": "warning", "summary": f"{tool} is not installed or not available on PATH, so a full syntax check could not run.", "issues": basic_delimiter_check(language, code), "solution": f"{tool} is required for a full syntax check. Install it and make sure it is available on PATH. Until then, this is only a basic bracket/quote check and may miss real errors.", "tips": [f"Install {tool} and add it to PATH for a full syntax check.", "The lightweight fallback cannot detect every syntax error.", "VisionFix does not execute submitted programs."], "tool": "Lightweight fallback"}
    filename = "Main.java" if language == "java" else "snippet" + extension
    with tempfile.TemporaryDirectory(prefix="visionfix_") as folder:
        source = Path(folder) / filename
        source.write_text(code, encoding="utf-8")
        if language in ("c", "cpp"):
            command = [executable, "-fsyntax-only", "-Wall", str(source)]
        elif language == "javascript":
            command = [executable, "--check", str(source)]
        else:
            command = [executable, "-Xlint:none", "-d", folder, str(source)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, shell=False, cwd=folder)
        except subprocess.TimeoutExpired:
            return 200, {"language": label, "status": "error", "summary": "The syntax checker timed out and was stopped.", "issues": [], "tips": ["Try a smaller code sample."], "tool": tool}
        except OSError:
            return 200, {"language": label, "status": "error", "summary": f"Could not start {tool}. Check the installation.", "issues": [], "tips": ["Verify that the tool is installed and available on PATH."], "tool": tool}
        output = (result.stderr or result.stdout or "").strip()
        if result.returncode == 0:
            return 200, {"language": label, "status": "success", "summary": "The installed syntax checker reported no errors.", "issues": [], "tips": ["Syntax checks cannot guarantee correct program logic.", "Test with safe, representative inputs."], "tool": tool}
        line_number = get_line(output)
        solution, fixed_code = build_solution(language, code, output, line_number)
        result = {"language": label, "status": "error", "summary": "The syntax checker reported a problem. Review the suggested next step below.", "issues": [{"line": line_number, "column": None, "message": output or "Syntax check failed.", "snippet": ""}], "solution": solution, "tips": ["Fix the first reported error before later ones; later messages may be consequences.", "Compiler output formats differ, so the detected line number may not always be available.", "VisionFix checks syntax; it does not run or prove the program's logic."], "tool": tool}
        if fixed_code is not None:
            result["fixed_code"] = fixed_code
        return 200, result

class Handler(BaseHTTPRequestHandler):
    server_version = "VisionFix/1.0"
    def send_body(self, status, body, content_type="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/":
            self.send_body(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif route == "/api/health":
            self.send_body(200, b'{"status":"ok","service":"VisionFix"}')
        else:
            self.send_body(404, b'{"error":"Not found"}')
    def do_POST(self):
        if urlparse(self.path).path != "/api/analyze":
            self.send_body(404, b'{"error":"Not found"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_CODE + 1000:
            self.send_body(413, b'{"error":"Request is empty or too large"}')
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("language"), str) or not isinstance(payload.get("code"), str):
                raise ValueError
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            self.send_body(400, b'{"error":"Send valid JSON with language and code strings."}')
            return
        status, result = analyze(payload["language"], payload["code"])
        self.send_body(status, json.dumps(result, ensure_ascii=False).encode("utf-8"))
    def log_message(self, fmt, *args):
        print("[VisionFix] " + (fmt % args))

def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print("=" * 48)
    print("VisionFix — Python-only edition")
    print(f"Open: http://{HOST}:{PORT}")
    print("No pip installs required. Press Ctrl+C to stop.")
    print("=" * 48)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nVisionFix stopped.")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
