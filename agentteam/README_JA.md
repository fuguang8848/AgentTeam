<p align="center">

[English](README.md) ·
[简体中文](README_CN.md) ·
[繁體中文](README_TW.md) ·
[日本語](README_JA.md) ·
[한국어](README_KO.md) ·
[Français](README_FR.md) ·
[Español](README_ES.md) ·
[Deutsch](README_DE.md) ·
[Italiano](README_IT.md) ·
[Русский](README_RU.md) ·
[Português (Brasil)](README_PT-BR.md)



  <a href="README.md">English</a> |

  <a href="README_CN.md">ç®ä½ä¸­æ?/a> |

  <a href="README_TW.md">ç¹é«ä¸­æ</a> |

  <a href="README_JA.md">æ¥æ¬èª?/a> |

  <a href="README_KO.md">íêµ­ì?/a> |

  <a href="README_FR.md">FranÃ§ais</a> |

  <a href="README_ES.md">EspaÃ±ol</a> |

  <a href="README_DE.md">Deutsch</a> |

  <a href="README_IT.md">Italiano</a> |

  <a href="README_RU.md">Ð ÑÑÑÐºÐ¸Ð¹</a> |

  <a href="README_PT-BR.md">PortuguÃªs (Brasil)</a>

</p>



<h1 align="center">ð¦AgentTeam-OpenClaw</h1>



<p align="center">

  <strong>CLIã³ã¼ãã£ã³ã°ã¨ã¼ã¸ã§ã³ãã®ããã®ãã«ãã¨ã¼ã¸ã§ã³ãã¹ã¯ã¼ã é£æº â?<a href="https://openclaw.ai">OpenClaw</a> ãããã©ã«ãã?/strong>

</p>



<p align="center">

  <a href="https://github.com/HKUDS/ClawTeam"><img src="https://img.shields.io/badge/upstream-HKUDS%2FAgentTeam-purple?style=for-the-badge" alt="Upstream"></a>

  <a href="#-ã¯ã¤ãã¯ã¹ã¿ã¼ã"><img src="https://img.shields.io/badge/Quick_Start-3_min-blue?style=for-the-badge" alt="Quick Start"></a>

  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"></a>

</p>



<p align="center">

  <img src="https://img.shields.io/badge/python-â?.10-blue?logo=python&logoColor=white" alt="Python">

  <img src="https://img.shields.io/badge/agents-OpenClaw_%7C_Claude_Code_%7C_Codex_%7C_nanobot-blueviolet" alt="Agents">

  <img src="https://img.shields.io/badge/transport-File_%7C_ZeroMQ_P2P-orange" alt="Transport">

  <img src="https://img.shields.io/badge/version-0.3.0-teal" alt="Version">

</p>



> **[HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam) ã®ãã©ã¼ã?* â?OpenClaw ã¨ã®æ·±ãçµ±åãå®ç¾ï¼ããã©ã«ãã® `openclaw` ã¨ã¼ã¸ã§ã³ããã¨ã¼ã¸ã§ã³ããã¨ã®ã»ãã·ã§ã³åé¢ãå®è¡æ¿èªã®èªåè¨­å®ãæ¬çªç°å¢å¯¾å¿ã®ã¹ãã¼ã³ããã¯ã¨ã³ããæ­è¼ãä¸æµã®ä¿®æ­£ã¯ãã¹ã¦åæããã¾ãã?


ç®æ¨ãè¨­å®ããã ããã¨ã¼ã¸ã§ã³ãã¹ã¯ã¼ã ãæ®ããå¦çãã¾ã â?ã¯ã¼ã«ã¼ã®çæãã¿ã¹ã¯ã®åå²ãé£æºãçµæã®çµ±åã¾ã§ãã¹ã¦èªåã§ãã?


[OpenClaw](https://openclaw.ai)ï¼ããã©ã«ãï¼ã[Claude Code](https://claude.ai/claude-code)ã[Codex](https://openai.com/codex)ã[nanobot](https://github.com/HKUDS/nanobot)ã[Cursor](https://cursor.com)ãããã³ãããã CLI ã¨ã¼ã¸ã§ã³ãã§åä½ãã¾ãã?


---



## ãªã AgentTeam ãªã®ãï¼



ç¾å¨ã?AI ã¨ã¼ã¸ã§ã³ãã¯å¼·åã§ããã?*å­¤ç«ãã¦**åä½ãã¦ãã¾ããAgentTeam ãä½¿ãã°ãã¨ã¼ã¸ã§ã³ããèªå¾çã«ãã¼ã ãç·¨æããä½æ¥­ãåæããã³ãã¥ãã±ã¼ã·ã§ã³ããäººéãç´°ããç®¡çããªãã¦ãçµæãåæããããã¨ãã§ãã¾ãã?


| | AgentTeam | ä»ã®ãã«ãã¨ã¼ã¸ã§ã³ããã¬ã¼ã ã¯ã¼ã¯ |

|---|---------|----------------------------|

| **ä½¿ãã®ã¯èª°ã** | AI ã¨ã¼ã¸ã§ã³ãèªèº« | ãªã¼ã±ã¹ãã¬ã¼ã·ã§ã³ã³ã¼ããæ¸ãäººé |

| **ã»ããã¢ãã** | `pip install` + ãã­ã³ãã?ã?| Dockerãã¯ã©ã¦ã?APIãYAML è¨­å®ãã¡ã¤ã« |

| **ã¤ã³ãã©** | ãã¡ã¤ã«ã·ã¹ãã  + tmux | Redisãã¡ãã»ã¼ã¸ã­ã¥ã¼ããã¼ã¿ãã¼ã?|

| **ã¨ã¼ã¸ã§ã³ãå¯¾å¿** | ãããã CLI ã¨ã¼ã¸ã§ã³ã | ãã¬ã¼ã ã¯ã¼ã¯åºæã®ã?|

| **åé¢** | Git worktreeï¼å®ãã©ã³ãï¼?| ã³ã³ããã¾ãã¯ä»®æ³ç°å¢?|



---



## ä»çµã?


<table>

<tr>

<td width="33%">



### ã¨ã¼ã¸ã§ã³ããã¨ã¼ã¸ã§ã³ããçæ

ãªã¼ãã¼ã `agentteam spawn` ãå¼ã³åºãã¦ã¯ã¼ã«ã¼ãä½æãã¾ããåã¯ã¼ã«ã¼ã¯ç¬èªã® **Git worktree**ã?*tmux ã¦ã£ã³ãã?*ã?*ã¢ã¤ãã³ãã£ãã£**ãæã¡ã¾ãã?


```bash

agentteam spawn --team my-team \

  --agent-name worker1 \

  --task "Implement auth module"

```



</td>

<td width="33%">



### ã¨ã¼ã¸ã§ã³ãéã®éä¿¡

ã¯ã¼ã«ã¼ã¯åä¿¡ç®±ãç¢ºèªããã¿ã¹ã¯ãæ´æ°ããçµæãå ±åãã¾ã?â?ãã¹ã¦ãã­ã³ããã?*èªåæ³¨å¥**ããã?CLI ã³ãã³ããéãã¦è¡ããã¾ãã?


```bash

agentteam task list my-team --owner me

agentteam inbox send my-team leader \

  "Auth done. All tests passing."

```



</td>

<td width="33%">



### ããªãã¯è¦å®ãã ã?
ã¿ã¤ã«è¡¨ç¤ºã® tmux ãã¥ã¼ã¾ãã¯ Web UI ããã¹ã¯ã¼ã ãç£è¦ãã¾ãããªã¼ãã¼ãé£æºãæå½ãã¾ãã?


```bash

agentteam board attach my-team

# Or web dashboard

agentteam board serve --port 8080

```



</td>

</tr>

</table>



---



## ã¯ã¤ãã¯ã¹ã¿ã¼ã



### æ¹æ³ 1: ã¨ã¼ã¸ã§ã³ãã«ä»»ããï¼æ¨å¥¨ï¼



AgentTeam ãã¤ã³ã¹ãã¼ã«ããã¨ã¼ã¸ã§ã³ãã«ãã­ã³ãããä¸ãã¾ãï¼?


```

"Build a web app. Use agentteam to split the work across multiple agents."

```



ã¨ã¼ã¸ã§ã³ããèªåã§ãã¼ã ãä½æããã¯ã¼ã«ã¼ãçæããã¿ã¹ã¯ãå²ãå½ã¦ãé£æºãè¡ãã¾ã?â?ãã¹ã?`agentteam` CLI ãéãã¦ã?


### æ¹æ³ 2: æåã§æä½ãã?


```bash

# Create a team

agentteam team spawn-team my-team -d "Build the auth module" -n leader



# Spawn workers â?each gets a git worktree + tmux window

agentteam spawn --team my-team --agent-name alice --task "Implement OAuth2 flow"

agentteam spawn --team my-team --agent-name bob   --task "Write unit tests for auth"



# Watch them work

agentteam board attach my-team

```



### å¯¾å¿ã¨ã¼ã¸ã§ã³ã



| ã¨ã¼ã¸ã§ã³ã | ã¹ãã¼ã³ã³ãã³ã | ã¹ãã¼ã¿ã?|

|-------|--------------|--------|

| [OpenClaw](https://openclaw.ai) | `agentteam spawn tmux openclaw --team ...` | **ããã©ã«ã?* |

| [Claude Code](https://claude.ai/claude-code) | `agentteam spawn tmux claude --team ...` | å®å¨å¯¾å¿ |

| [Codex](https://openai.com/codex) | `agentteam spawn tmux codex --team ...` | å®å¨å¯¾å¿ |

| [nanobot](https://github.com/HKUDS/nanobot) | `agentteam spawn tmux nanobot --team ...` | å®å¨å¯¾å¿ |

| [Cursor](https://cursor.com) | `agentteam spawn subprocess cursor --team ...` | å®é¨ç?|

| ã«ã¹ã¿ã ã¹ã¯ãªãã?| `agentteam spawn subprocess python --team ...` | å®å¨å¯¾å¿ |



---



## ã¤ã³ã¹ãã¼ã«



### ã¹ããã 1: åææ¡ä»¶



AgentTeam ã«ã¯ **Python 3.10+**ã?*tmux**ãããã³å°ãªãã¨ã?ã¤ã® CLI ã³ã¼ãã£ã³ã°ã¨ã¼ã¸ã§ã³ãï¼OpenClawãClaude CodeãCodex ãªã©ï¼ãå¿è¦ã§ãã?


**æ¢ã«ã¤ã³ã¹ãã¼ã«æ¸ã¿ã®ãã®ãç¢ºèªï¼?*



```bash

python3 --version   # Need 3.10+

tmux -V             # Need any version

openclaw --version  # Or: claude --version / codex --version

```



**ä¸è¶³ãã¦ããåææ¡ä»¶ã®ã¤ã³ã¹ãã¼ã«ï¼**



| ãã¼ã?| macOS | Ubuntu/Debian |

|------|-------|---------------|

| Python 3.10+ | `brew install python@3.12` | `sudo apt update && sudo apt install python3 python3-pip` |

| tmux | `brew install tmux` | `sudo apt install tmux` |

| OpenClaw | `pip install openclaw` | `pip install openclaw` |



> OpenClaw ã®ä»£ããã?Claude Code ã?Codex ãä½¿ç¨ããå ´åã¯ãããããã®ãã­ã¥ã¡ã³ãã«å¾ã£ã¦ã¤ã³ã¹ãã¼ã«ãã¦ãã ãããOpenClaw ã¯ããã©ã«ãã§ãããå¿é ã§ã¯ããã¾ããã?


### ã¹ããã 2: AgentTeam ã®ã¤ã³ã¹ãã¼ã?


> **â ï¸ `pip install agentteam` ã?`npm install -g agentteam` ãç´æ¥å®è¡ããªãã§ãã ããï¼**

> - `pip install agentteam` ã?PyPI ä¸ã®ä¸æµãã¼ã¸ã§ã³ãã¤ã³ã¹ãã¼ã«ããããã©ã«ãã?`claude` ã?OpenClaw åãã®é©å¿ãå«ã¾ãã¦ãã¾ããã?
> - `npm install -g agentteam` ã¯ç¡é¢ä¿ã®ã¹ã¯ã¯ããã£ã³ã°ããã±ã¼ã¸ãã¤ã³ã¹ãã¼ã«ãã¾ãï¼çºè¡è?`a9logic`ï¼ã`agentteam --version` ã?"Coming Soon" ã¨è¡¨ç¤ºãããå ´åã¯èª¤ã£ãããã±ã¼ã¸ã§ããã¾ã?`npm uninstall -g agentteam` ã§åé¤ãã¦ãã ããã?
>

> **ä»¥ä¸ã?3 ã¤ã®ã³ãã³ããä½¿ç¨ãã¦ãã ãã?â?clone å¾ã® `pip install -e .` ã¯å¿é ã§ããPyPI ããã§ã¯ãªãã­ã¼ã«ã«ãªãã¸ããªããã¤ã³ã¹ãã¼ã«ãã¾ãã?*



```bash

git clone https://github.com/win4r/ClawTeam-OpenClaw-OpenClaw.git

cd AgentTeam-OpenClaw

pip install -e .    # â?å¿é ï¼ã­ã¼ã«ã«ãªãã¸ããªããã¤ã³ã¹ãã¼ã«ãpip install agentteam ã¨ã¯ç°ãªãã¾ã?
```



ãªãã·ã§ã?â?P2P ãã©ã³ã¹ãã¼ãï¼ZeroMQï¼ï¼



```bash

pip install -e ".[p2p]"

```



### ã¹ããã 3: ~/bin/AgentTeam ã·ã³ããªãã¯ãªã³ã¯ã®ä½æ



çæãããã¨ã¼ã¸ã§ã³ãã¯ãpip ã?bin ãã£ã¬ã¯ããªã?PATH ã«ãªãæ°ããã·ã§ã«ã§å®è¡ããã¾ãã`~/bin` ã«ã·ã³ããªãã¯ãªã³ã¯ãä½æãããã¨ã§ã`agentteam` ãå¸¸ã«å°éå¯è½ã«ãªãã¾ãï¼?


```bash

mkdir -p ~/bin

ln -sf "$(which agentteam)" ~/bin/AgentTeam

```



`which agentteam` ãä½ãè¿ããªãå ´åã¯ããã¤ããªãæåã§è¦ã¤ãã¦ãã ããï¼



```bash

# Common locations:

# ~/.local/bin/AgentTeam

# /opt/homebrew/bin/AgentTeam

# /usr/local/bin/AgentTeam

# /Library/Frameworks/Python.framework/Versions/3.*/bin/AgentTeam

find / -name agentteam -type f 2>/dev/null | head -5

```



æ¬¡ã«ã`~/bin` ã?PATH ã«å«ã¾ãã¦ãããã¨ãç¢ºèªãã¾ã?â?å«ã¾ãã¦ããªãå ´åã¯ `~/.zshrc` ã¾ãã?`~/.bashrc` ã«ä»¥ä¸ãè¿½å ãã¦ãã ããï¼?


```bash

export PATH="$HOME/bin:$PATH"

```



### ã¹ããã 4: OpenClaw ã¹ã­ã«ã®ã¤ã³ã¹ãã¼ã«ï¼OpenClaw ã¦ã¼ã¶ã¼ã®ã¿ï¼?


ã¹ã­ã«ãã¡ã¤ã«ã¯ãOpenClaw ã¨ã¼ã¸ã§ã³ãã«èªç¶è¨èªã§ AgentTeam ã®ä½¿ãæ¹ãæãã¾ããOpenClaw ãä½¿ç¨ãã¦ããªãå ´åã¯ããã®ã¹ããããã¹ã­ãããã¦ãã ããã?


```bash

mkdir -p ~/.openclaw/workspace/skills/AgentTeam

cp skills/openclaw/SKILL.md ~/.openclaw/workspace/skills/AgentTeam/SKILL.md

```



### ã¹ããã 5: å®è¡æ¿èªã®è¨­å®ï¼OpenClaw ã¦ã¼ã¶ã¼ã®ã¿ï¼?


çæããã?OpenClaw ã¨ã¼ã¸ã§ã³ãã¯ã`agentteam` ã³ãã³ããå®è¡ããããã®è¨±å¯ãå¿è¦ã§ãããã®è¨­å®ããªãã¨ãã¨ã¼ã¸ã§ã³ããã¤ã³ã¿ã©ã¯ãã£ããªè¨±å¯ãã­ã³ããã§ãã­ãã¯ããã¾ãã?


```bash

# Ensure security mode is "allowlist" (not "full")

python3 -c "

import json, pathlib

p = pathlib.Path.home() / '.openclaw' / 'exec-approvals.json'

if p.exists():

    d = json.loads(p.read_text())

    d.setdefault('defaults', {})['security'] = 'allowlist'

    p.write_text(json.dumps(d, indent=2))

    print('exec-approvals.json updated: security = allowlist')

else:

    print('exec-approvals.json not found â?run openclaw once first, then re-run this step')

"



# Add agentteam to the allowlist (use the absolute path â?OpenClaw 4.2+ requires it)

openclaw approvals allowlist add --agent "*" "$(which agentteam)"

```



> `openclaw approvals` ãå¤±æããå ´åãOpenClaw ã²ã¼ãã¦ã§ã¤ãèµ·åãã¦ããªãå¯è½æ§ãããã¾ããåã«ã²ã¼ãã¦ã§ã¤ãèµ·åãã¦ãããªãã©ã¤ãã¦ãã ããã?


### ã¹ããã 6: åä½ç¢ºèª



```bash

agentteam --version          # Should print version

agentteam config health      # Should show all green

```



OpenClaw ãä½¿ç¨ãã¦ããå ´åã¯ãã¹ã­ã«ãèª­ã¿è¾¼ã¾ãã¦ãããã¨ãç¢ºèªãã¦ãã ããï¼?


```bash

openclaw skills list | grep agentteam

```



### èªåã¤ã³ã¹ãã¼ã©ã?


ä¸è¨ã®ã¹ããã?2ã? ã¯ãåä¸ã®ã¹ã¯ãªããã§ãå®è¡ã§ãã¾ãï¼?


```bash

git clone https://github.com/win4r/ClawTeam-OpenClaw-OpenClaw.git

cd AgentTeam-OpenClaw

bash scripts/install-openclaw.sh

```



### ãã©ãã«ã·ã¥ã¼ãã£ã³ã?


| åé¡ | åå  | è§£æ±ºæ¹æ³ |

|---------|-------|-----|

| `agentteam: command not found` | pip ã?bin ãã£ã¬ã¯ããªã?PATH ã«ãªã?| ã¹ããã 3ï¼ã·ã³ããªãã¯ãªã³ã¯ + PATHï¼ãå®è¡ |

| çæãããã¨ã¼ã¸ã§ã³ãã `agentteam` ãè¦ã¤ããããªã | ã¨ã¼ã¸ã§ã³ãã?pip ã?PATH ãªãã®æ°ããã·ã§ã«ã§å®è¡ããã?| `~/bin/AgentTeam` ã·ã³ããªãã¯ãªã³ã¯ãå­å¨ãã`~/bin` ã?PATH ã«ãããã¨ãç¢ºèª |

| `openclaw approvals` ãå¤±æãã?| ã²ã¼ãã¦ã§ã¤ãèµ·åãã¦ããªã | åã« `openclaw gateway` ãèµ·åãã¦ãããã¹ããã?5 ããªãã©ã?|

| `exec-approvals.json not found` | OpenClaw ãä¸åº¦ãå®è¡ããã¦ããªã | `openclaw` ãä¸åº¦å®è¡ãã¦è¨­å®ãçæãã¦ãããã¹ããã?5 ããªãã©ã?|

| ã¨ã¼ã¸ã§ã³ããè¨±å¯ãã­ã³ããã§ãã­ãã¯ããã | å®è¡æ¿èªã®ã»ã­ã¥ãªãã£ã "full" ã«ãªã£ã¦ãã | ã¹ããã 5 ãå®è¡ãã?"allowlist" ã«åãæ¿ã?|

| `pip install -e .` ãå¤±æãã?| ãã«ãä¾å­é¢ä¿ãä¸è¶³ | åã« `pip install hatchling` ãå®è¡?|

| `agentteam --version` ã?"Coming Soon" ã¨è¡¨ç¤ºããã | npm ã®ã¹ã¯ã¯ããã£ã³ã°ããã±ã¼ã¸ãèª¤ã£ã¦ã¤ã³ã¹ãã¼ã«ï¼`a9logic`ãæ¬ãã­ã¸ã§ã¯ãã¨ã¯ç¡é¢ä¿ï¼ | `npm uninstall -g agentteam` ãå®è¡ããã¹ããã?2 ã«å¾ã£ã¦åã¤ã³ã¹ãã¼ã?|



---



## ã¦ã¼ã¹ã±ã¼ã¹



### 1. èªå¾å?ML ç ç©¶ â?8 ã¨ã¼ã¸ã§ã³ã x 8 GPU



[@karpathy/autoresearch](https://github.com/karpathy/autoresearch) ã«åºã¥ãã?ã¤ã®ãã­ã³ããã§ 8 ã¤ã®ç ç©¶ã¨ã¼ã¸ã§ã³ãã?H100 ä¸ã«å±éãã?000 ä»¥ä¸ã®å®é¨ãèªå¾çã«è¨­è¨ãã¾ãã?


```

Human: "Use 8 GPUs to optimize train.py. Read program.md for instructions."



Leader agent:

âââ Spawns 8 agents, each assigned a research direction (depth, width, LR, batch size...)

âââ Each agent gets its own git worktree for isolated experiments

âââ Every 30 min: checks results, cross-pollinates best configs to new agents

âââ Reassigns GPUs as agents finish â?fresh agents start from best known config

âââ Result: val_bpb 1.044 â?0.977 (6.4% improvement) across 2430 experiments in ~30 GPU-hours

```



è©³ç´°ãªçµæ? [novix-science/autoresearch](https://github.com/novix-science/autoresearch)



### 2. ã¨ã¼ã¸ã§ã³ãé§åã½ããã¦ã§ã¢éçº



```

Human: "Build a full-stack todo app with auth, database, and React frontend."



Leader agent:

âââ Creates tasks with dependency chains (API schema â?auth + DB â?frontend â?tests)

âââ Spawns 5 agents (architect, 2 backend, frontend, tester) in separate worktrees

âââ Dependencies auto-resolve: architect completes â?backend unblocks â?tester unblocks

âââ Agents coordinate via inbox: "Here's the OpenAPI spec", "Auth endpoints ready"

âââ Leader merges all worktrees into main when complete

```



### 3. AI ããã¸ãã¡ã³ã?â?ãã³ãã¬ã¼ãèµ·å



TOML ãã³ãã¬ã¼ãã§ã?ã¤ã®ã³ãã³ãã§å®å¨ãª 7 ã¨ã¼ã¸ã§ã³ãæè³ãã¼ã ãçæãã¾ãï¼



```bash

agentteam launch hedge-fund --team fund1 --goal "Analyze AAPL, MSFT, NVDA for Q2 2026"

```



5 äººã®ã¢ããªã¹ãã¨ã¼ã¸ã§ã³ãï¼ããªã¥ã¼ãã°ã­ã¼ã¹ããã¯ãã«ã«ããã¡ã³ãã¡ã³ã¿ã«ãºãã»ã³ãã¡ã³ãï¼ãä¸¦è¡ãã¦ä½æ¥­ãã¾ãããªã¹ã¯ããã¼ã¸ã£ã¼ããã¹ã¦ã®ã·ã°ãã«ãçµ±åãã¾ãããã¼ããã©ãªãªããã¼ã¸ã£ã¼ãæçµå¤æ­ãä¸ãã¾ãã?


ãã³ãã¬ã¼ãã?TOML ãã¡ã¤ã«ã§ã â?ãããããã¡ã¤ã³ã«åããã?*ç¬èªã®ãã³ãã¬ã¼ããä½æ**ã§ãã¾ãã?


---



## æ©è½



<table>

<tr>

<td width="50%">



### ã¨ã¼ã¸ã§ã³ãã®èªå·±çµç¹å

- ãªã¼ãã¼ãã¯ã¼ã«ã¼ãçæã»ç®¡ç

- èªåæ³¨å¥ãããé£æºãã­ã³ãã?â?æåã»ããã¢ããä¸è¦

- ã¯ã¼ã«ã¼ãèªåã§ã¹ãã¼ã¿ã¹ã¨ã¢ã¤ãã«ç¶æãå ±å?
- ãããã CLI ã¨ã¼ã¸ã§ã³ããåå å¯è?


### ã¯ã¼ã¯ã¹ãã¼ã¹åé?
- åã¨ã¼ã¸ã§ã³ããç¬èªã?**Git worktree** ãåå¾?
- ä¸¦è¡ã¨ã¼ã¸ã§ã³ãéã§ãã¼ã¸ã³ã³ããªã¯ããªã?
- ãã§ãã¯ãã¤ã³ãããã¼ã¸ãã¯ãªã¼ã³ã¢ããã³ãã³ã

- ãã©ã³ãå½åè¦å: `agentteam/{team}/{agent}`



### ä¾å­é¢ä¿ä»ãã¿ã¹ã¯ç®¡ç?
- å±æã«ã³ãã³: `pending` â?`in_progress` â?`completed` / `blocked`

- `--blocked-by` ãã§ã¼ã³ã¨å®äºæã®èªåã¢ã³ãã­ãã?
- `task wait` ããã¹ã¦ã®ã¿ã¹ã¯å®äºã¾ã§å¾æ©



</td>

<td width="50%">



### ã¨ã¼ã¸ã§ã³ãéã¡ãã»ã¼ã¸ã³ã°

- ãã¤ã³ããã¼ãã¤ã³ãåä¿¡ç®±ï¼éä¿¡ãåä¿¡ããã¼ã¯ï¼?
- å¨ãã¼ã ã¡ã³ãã¼ã¸ã®ãã­ã¼ãã­ã£ã¹ã

- ãã¡ã¤ã«ãã¼ã¹ï¼ããã©ã«ãï¼ã¾ãã?ZeroMQ P2P ãã©ã³ã¹ãã¼ã?


### ã¢ãã¿ãªã³ã°ã¨ããã·ã¥ãã¼ã

- `board show` â?ã¿ã¼ããã«ã«ã³ãã?
- `board live` â?èªåæ´æ°ããã·ã¥ãã¼ã

- `board attach` â?ã¿ã¤ã«è¡¨ç¤ºã® tmux ãã¥ã?
- `board serve` â?ãªã¢ã«ã¿ã¤ã æ´æ°ã?Web UI



### ãã¼ã ãã³ãã¬ã¼ã?
- TOML ãã¡ã¤ã«ã§ãã¼ã ã®ã¢ã¼ã­ã¿ã¤ããå®ç¾©ï¼ã­ã¼ã«ãã¿ã¹ã¯ããã­ã³ããï¼?
- ã³ãã³ã1ã? `agentteam launch <template>`

- å¤æ°ç½®æ: `{goal}`ã`{team_name}`ã`{agent_name}`

- **ã¨ã¼ã¸ã§ã³ããã¨ã®ã¢ãã«å²ãå½ã¦**ï¼ãã¬ãã¥ã¼ï¼? ç°ãªãã­ã¼ã«ã«ç°ãªãã¢ãã«ãå²ãå½ã¦ â?[ä¸è¨åç§](#ã¨ã¼ã¸ã§ã³ããã¨ã®ã¢ãã«å²ãå½ã¦ãã¬ãã¥ã?



</td>

</tr>

</table>



**ãã®ä»?** ãã©ã³æ¿èªã¯ã¼ã¯ãã­ã¼ãã°ã¬ã¼ã¹ãã«ãªã©ã¤ããµã¤ã¯ã«ç®¡çãå¨ã³ãã³ãã?`--json` åºåãã¯ã­ã¹ãã·ã³å¯¾å¿ï¼NFS/SSHFS ã¾ãã?P2Pï¼ããã«ãã¦ã¼ã¶ã¼ãã¼ã ã¹ãã¼ã¹ãèªåã­ã¼ã«ããã¯ä»ãã¹ãã¼ã³æ¤è¨¼ãä¸¦è¡å®å¨ã®ããã?`fcntl` ãã¡ã¤ã«ã­ãã¯ã?


---



## OpenClaw çµ±å



ãã®ãã©ã¼ã¯ã?[OpenClaw](https://openclaw.ai) ã?*ããã©ã«ãã¨ã¼ã¸ã§ã³ã?*ã«ãã¦ãã¾ããAgentTeam ãªãã§ã¯ãå OpenClaw ã¨ã¼ã¸ã§ã³ãã¯å­¤ç«ãã¦åä½ãã¾ããAgentTeam ãããããã«ãã¨ã¼ã¸ã§ã³ããã©ãããã©ã¼ã ã«å¤ãã¾ãã?


| æ©è½ | OpenClaw åä½ | OpenClaw + AgentTeam |

|-----------|---------------|-------------------|

| **ã¿ã¹ã¯å²ãå½ã?* | ã¨ã¼ã¸ã§ã³ããã¨ã®æåã¡ãã»ã¼ã¸ã³ã° | ãªã¼ãã¼ãèªå¾çã«åå²ãå²ãå½ã¦ãç£è¦?|

| **ä¸¦è¡éçº** | å±æã®ä½æ¥­ãã£ã¬ã¯ãã?| ã¨ã¼ã¸ã§ã³ããã¨ã«åé¢ããã Git worktree |

| **ä¾å­é¢ä¿** | æåãã¼ãªã³ã?| `--blocked-by` ã¨èªåã¢ã³ãã­ãã?|

| **ã³ãã¥ãã±ã¼ã·ã§ã?* | AGI ãªã¬ã¼çµç±ã®ã?| ãã¤ã¬ã¯ããªãã¤ã³ããã¼ãã¤ã³ãåä¿¡ç®± + ãã­ã¼ãã­ã£ã¹ã |

| **å¯è¦³æ¸¬æ?* | ã­ã°ã®é²è¦?| ã«ã³ãã³ãã¼ã?+ ã¿ã¤ã«è¡¨ç¤ºã® tmux ãã¥ã?|



ã¹ã­ã«ãã¤ã³ã¹ãã¼ã«ããããä»»æã®ãã£ã³ãã«ã§ OpenClaw ãããã«è©±ãããã¦ãã ããï¼



| ããªãã®çºè¨ | å®è¡ãããå¦ç?|

|-------------|-------------|

| ã?ã¨ã¼ã¸ã§ã³ãã®ãã¼ã ãä½ã£ã¦ã¦ã§ãã¢ããªãæ§ç¯ãã¦ã?| ãã¼ã ãã¿ã¹ã¯ãä½æããtmux ã?5 ã¨ã¼ã¸ã§ã³ããçæ?|

| ãããã¸ãã¡ã³ãåæãã¼ã ãèµ·åãã¦ã?| 7 ã¨ã¼ã¸ã§ã³ãã?`agentteam launch hedge-fund` ãå®è¡?|

| ãã¨ã¼ã¸ã§ã³ããã¼ã ã®ã¹ãã¼ã¿ã¹ãç¢ºèªãã¦ã?| ã«ã³ãã³åºåã?`agentteam board show` ãå®è¡?|



```

  You (Telegram/Discord/TUI)

         â?
         â?
  ââââââââââââââââââââ?
  â? OpenClaw Gateway â? â?activates agentteam skill

  ââââââââââ¬ââââââââââ?
           â?
           â?
  ââââââââââââââââââââ?    agentteam spawn     âââââââââââââââââââ?
  â? Leader Agent    â?ââââââââââââââââââââââ?â? openclaw tui   â?
  â? (openclaw)      â?âââ?                   â? (tmux window)  â?
  â?                 â?  â?                   â? git worktree   â?
  â? Manages swarm   â?  ââââââââââââââââââââ?âââââââââââââââââââ?
  â? via agentteam    â?  â?                   â? openclaw tui   â?
  â? CLI             â?  ââââââââââââââââââââ?âââââââââââââââââââ?
  ââââââââââââââââââââ?  â?                   â? openclaw tui   â?
                         ââââââââââââââââââââ?âââââââââââââââââââ?
                                               All coordinate via

                                               ~/.agentteam/ (tasks, inboxes)

```



---



## ã¢ã¼ã­ãã¯ãã?


```

  Human: "Optimize this LLM"

         â?
         â?
  ââââââââââââââââ?    agentteam spawn     ââââââââââââââââ?
  â? Leader      â?âââââââââââââââââââââââ?â? Worker      â?
  â? (any agent) â?âââââââ?               â? git worktree â?
  â?             â?      ââââââââââââââââ?â? tmux window  â?
  â? spawn       â?      â?               ââââââââââââââââ?
  â? task create â?      ââââââââââââââââ?â? Worker      â?
  â? inbox send  â?      â?               â? git worktree â?
  â? board show  â?      ââââââââââââââââ?â? tmux window  â?
  ââââââââââââââââ?                       ââââââââââââââââ?
                                                 â?
                                                 â?
                                      âââââââââââââââââââââââ?
                                      â?   ~/.agentteam/     â?
                                      â?âââ teams/   (who) â?
                                      â?âââ tasks/   (what)â?
                                      â?âââ inboxes/ (talk)â?
                                      â?âââ workspaces/    â?
                                      âââââââââââââââââââââââ?
```



ãã¹ã¦ã®ã¹ãã¼ãã?`~/.agentteam/` ã?JSON ãã¡ã¤ã«ã¨ãã¦ä¿å­ããã¾ãããã¼ã¿ãã¼ã¹ããµã¼ãã¼ãä¸è¦ã§ãã`fcntl` ãã¡ã¤ã«ã­ãã¯ã«ããã¢ãããã¯æ¸ãè¾¼ã¿ã§ã¯ã©ãã·ã¥å®å¨æ§ãç¢ºä¿ãã¦ãã¾ãã?


| è¨­å® | ç°å¢å¤æ° | ããã©ã«ãå?|

|---------|---------|---------|

| ãã¼ã¿ãã£ã¬ã¯ãã?| `AgentTeam_DATA_DIR` | `~/.agentteam` |

| ãã©ã³ã¹ãã¼ã?| `AgentTeam_TRANSPORT` | `file` |

| ã¯ã¼ã¯ã¹ãã¼ã¹ã¢ã¼ã | `AgentTeam_WORKSPACE` | `auto` |

| ã¹ãã¼ã³ããã¯ã¨ã³ã | `AgentTeam_DEFAULT_BACKEND` | `tmux` |



---



## ã³ãã³ããªãã¡ã¬ã³ã¹



<details open>

<summary><strong>ã³ã¢ã³ãã³ã</strong></summary>



```bash

# Team lifecycle

agentteam team spawn-team <team> -d "description" -n <leader>

agentteam team discover                    # List all teams

agentteam team status <team>               # Show members

agentteam team cleanup <team> --force      # Delete team



# Spawn agents

agentteam spawn --team <team> --agent-name <name> --task "do this"

agentteam spawn tmux codex --team <team> --agent-name <name> --task "do this"



# Task management

agentteam task create <team> "subject" -o <owner> --blocked-by <id1>,<id2>

agentteam task update <team> <id> --status completed   # auto-unblocks dependents

agentteam task list <team> --status blocked --owner worker1

agentteam task wait <team> --timeout 300



# Messaging

agentteam inbox send <team> <to> "message"

agentteam inbox broadcast <team> "message"

agentteam inbox receive <team>             # consume messages

agentteam inbox peek <team>                # read without consuming



# Monitoring

agentteam board show <team>                # terminal kanban

agentteam board live <team> --interval 3   # auto-refresh

agentteam board attach <team>              # tiled tmux view

agentteam board serve --port 8080          # web UI

```



</details>



<details>

<summary><strong>ã¯ã¼ã¯ã¹ãã¼ã¹ããã©ã³ãã©ã¤ããµã¤ã¯ã«ãè¨­å®?/strong></summary>



```bash

# Workspace (git worktree management)

agentteam workspace list <team>

agentteam workspace checkpoint <team> <agent>    # auto-commit

agentteam workspace merge <team> <agent>         # merge back to main

agentteam workspace cleanup <team> <agent>       # remove worktree



# Plan approval

agentteam plan submit <team> <agent> "plan" --summary "TL;DR"

agentteam plan approve <team> <plan-id> <agent> --feedback "LGTM"

agentteam plan reject <team> <plan-id> <agent> --feedback "Revise X"



# Lifecycle

agentteam lifecycle request-shutdown <team> <agent> --reason "done"

agentteam lifecycle approve-shutdown <team> <request-id> <agent>

agentteam lifecycle idle <team>



# Templates

agentteam launch <template> --team <name> --goal "Build X"

agentteam template list



# Config

agentteam config show

agentteam config set transport p2p

agentteam config health

```



</details>



---



## ã¨ã¼ã¸ã§ã³ããã¨ã®ã¢ãã«å²ãå½ã¦ï¼ãã¬ãã¥ã¼ï¼?


> **ãã©ã³ã:** [`feat/per-agent-model-assignment`](https://github.com/win4r/ClawTeam-OpenClaw-OpenClaw/tree/feat/per-agent-model-assignment)

>

> ãã®æ©è½ã¯ãå¥ãã©ã³ãã§æ©æãã¹ãåãã«å¬éããã¦ãã¾ããOpenClaw ã?`--model` ãã©ã°ããªãªã¼ã¹ããæ¬¡ç¬¬ã`main` ã«ãã¼ã¸ãããäºå®ã§ãã?


ãã«ãã¨ã¼ã¸ã§ã³ãã¹ã¯ã¼ã ã«ããã¦ãã³ã¹ãã¨ããã©ã¼ãã³ã¹ã®ãã¬ã¼ããªããæé©åããããã«ãç°ãªãã¨ã¼ã¸ã§ã³ãã­ã¼ã«ã«ç°ãªãã¢ãã«ãå²ãå½ã¦ã¾ãã?


```bash

# Install from the feature branch

pip install -e "git+https://github.com/win4r/ClawTeam-OpenClaw-OpenClaw.git@feat/per-agent-model-assignment#egg=agentteam"

```



**ãã³ãã¬ã¼ãã§ã®ã¨ã¼ã¸ã§ã³ããã¨ã®ã¢ãã«æå®ï¼?*

```toml

[template]

name = "my-team"

command = ["openclaw"]

model = "sonnet-4.6"              # default for all agents

model_strategy = "auto"           # or: leadersâstrong, workersâbalanced



[template.leader]

name = "lead"

model = "opus"                    # override for leader



[[template.agents]]

name = "worker"

model_tier = "cheap"              # cost tiers: strong / balanced / cheap

```



**CLI ãã©ã°ï¼**

```bash

agentteam spawn --model opus                          # single agent

agentteam launch my-template --model gpt-5.4          # override all agents

agentteam launch my-template --model-strategy auto     # auto-assign by role

```



è©³ç´°ã?[issue #1](https://github.com/win4r/ClawTeam-OpenClaw-OpenClaw/issues/1) ã§æ©è½ãªã¯ã¨ã¹ãã¨ãã£ã¹ã«ãã·ã§ã³ãåç§ãã¦ãã ããã?


---



## ã­ã¼ãããã



| ãã¼ã¸ã§ã?| åå®¹ | ã¹ãã¼ã¿ã?|

|---------|------|--------|

| v0.3 | ãã¡ã¤ã« + P2P ãã©ã³ã¹ãã¼ããWeb UIããã«ãã¦ã¼ã¶ã¼ããã³ãã¬ã¼ã?| ãªãªã¼ã¹æ¸ã¿ |

| v0.4 | Redis ãã©ã³ã¹ãã¼ã?â?ã¯ã­ã¹ãã·ã³ã¡ãã»ã¼ã¸ã³ã?| è¨ç»ä¸?|

| v0.5 | å±æã¹ãã¼ãã¬ã¤ã¤ã¼ â?ãã·ã³éã®ãã¼ã è¨­å® | è¨ç»ä¸?|

| v0.6 | ã¨ã¼ã¸ã§ã³ããã¼ã±ãããã¬ã¤ã?â?ã³ãã¥ããã£ãã³ãã¬ã¼ã | æ¤è¨ä¸?|

| v0.7 | ã¢ãããã£ãã¹ã±ã¸ã¥ã¼ãªã³ã° â?åçã¿ã¹ã¯åå²ãå½ã¦ | æ¤è¨ä¸?|

| v1.0 | ãã­ãã¯ã·ã§ã³ã°ã¬ã¼ã â?èªè¨¼ãæ¨©éãç£æ»ã­ã?| æ¤è¨ä¸?|



---



## ã³ã³ããªãã¥ã¼ã·ã§ã³



ã³ã³ããªãã¥ã¼ã·ã§ã³ãæ­è¿ãã¾ãï¼?


- **ã¨ã¼ã¸ã§ã³ãçµ±å** â?ããå¤ãã?CLI ã¨ã¼ã¸ã§ã³ãã®ãµãã¼ã?
- **ãã¼ã ãã³ãã¬ã¼ã?* â?æ°ãããã¡ã¤ã³åãã® TOML ãã³ãã¬ã¼ã

- **ãã©ã³ã¹ãã¼ãããã¯ã¨ã³ã?* â?RedisãNATS ãªã©

- **ããã·ã¥ãã¼ãæ¹å** â?Web UIãGrafana

- **ãã­ã¥ã¡ã³ã** â?ãã¥ã¼ããªã¢ã«ã¨ãã¹ããã©ã¯ãã£ã?


---



## è¬è¾



- [@karpathy/autoresearch](https://github.com/karpathy/autoresearch) â?èªå¾å?ML ç ç©¶ãã¬ã¼ã ã¯ã¼ã?
- [OpenClaw](https://openclaw.ai) â?ããã©ã«ãã¨ã¼ã¸ã§ã³ãããã¯ã¨ã³ã?
- [Claude Code](https://claude.ai/claude-code) ããã?[Codex](https://openai.com/codex) â?å¯¾å¿ AI ã³ã¼ãã£ã³ã°ã¨ã¼ã¸ã§ã³ã

- [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) â?ããã¸ãã¡ã³ããã³ãã¬ã¼ãã®ã¤ã³ã¹ãã¬ã¼ã·ã§ã?
- [CLI-Anything](https://github.com/HKUDS/CLI-Anything) â?å§å¦¹ãã­ã¸ã§ã¯ã



## ã©ã¤ã»ã³ã?


MIT â?èªç±ã«ä½¿ç¨ãæ¹å¤ãåéå¸ã§ãã¾ãã?


---



<div align="center">



**AgentTeam** â?*ã¨ã¼ã¸ã§ã³ãã¹ã¯ã¼ã ã¤ã³ããªã¸ã§ã³ã¹ã?



</div>

