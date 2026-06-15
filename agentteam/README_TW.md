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

  <strong>é¢åå½ä»¤åç¨å¼ç¢¼æºè½é«çå¤æºè½é«éç¾¤åä½ â?é è¨­ä½¿ç¨ <a href="https://openclaw.ai">OpenClaw</a></strong>

</p>



<p align="center">

  <a href="https://github.com/HKUDS/ClawTeam"><img src="https://img.shields.io/badge/upstream-HKUDS%2FAgentTeam-purple?style=for-the-badge" alt="Upstream"></a>

  <a href="#-å¿«ééå§?><img src="https://img.shields.io/badge/Quick_Start-3_min-blue?style=for-the-badge" alt="Quick Start"></a>

  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License"></a>

</p>



<p align="center">

  <img src="https://img.shields.io/badge/python-â?.10-blue?logo=python&logoColor=white" alt="Python">

  <img src="https://img.shields.io/badge/agents-OpenClaw_%7C_Claude_Code_%7C_Codex_%7C_nanobot-blueviolet" alt="Agents">

  <img src="https://img.shields.io/badge/transport-File_%7C_ZeroMQ_P2P-orange" alt="Transport">

  <img src="https://img.shields.io/badge/version-0.3.0-teal" alt="Version">

</p>



> **[HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam) çååçæ?*ï¼æ·±åº¦æ´å?OpenClawï¼é è¨­ä½¿ç?`openclaw` æºè½é«ãæ¯åæºè½é«ç¨ç«æè©±éé¢ãå·è¡ææ¬èªåéç½®ï¼ä»¥åç¶éçç¢ç°å¢é©è­çååå¾ç«¯ãææä¸æ¸¸ä¿®å¾©åå·²åæ­¥ã?


æ¨è¨­å®ç®æ¨ï¼æºè½é«éç¾¤èçå©ä¸çä¸å?â?ååå·¥ä½èãæåä»»åãåèª¿éåãåä½µçµæã?


æ¯æ´ [OpenClaw](https://openclaw.ai)ï¼é è¨­ï¼ã[Claude Code](https://claude.ai/claude-code)ã[Codex](https://openai.com/codex)ã[nanobot](https://github.com/HKUDS/nanobot)ã[Cursor](https://cursor.com) åä»»ä½å½ä»¤åæºè½é«ã?


---



## çºä»éº¼é¸æ?AgentTeamï¼?


ç¶åçäººå·¥æºæ§æºè½é«åè½å¼·å¤§ï¼ä½é½å¨**å­¤ç«**éä½ãAgentTeam è®æºè½é«èªçµç¹çºåé â?æåå·¥ä½ãäºç¸æºéãå¯èçµæï¼ç¡éäººé¡äºå¿èº¬è¦ªã?


| | AgentTeam | å¶ä»å¤æºè½é«æ¡æ¶ |

|---|---------|----------------------------|

| **èª°å¨ä½¿ç¨** | äººå·¥æºæ§æºè½é«èªèº?| äººé¡ç·¨å¯«ç·¨æç¨å¼ç¢?|

| **è¨­å®** | `pip install` + ä¸å¥æç¤ºè© | Dockerãé²ç«?APIãYAML è¨­å®æª?|

| **åºç¤è¨­æ½** | æªæ¡ç³»çµ± + tmux | Redisãè¨æ¯ä½åãè³æåº« |

| **æºè½é«æ¯æ?* | ä»»ä½å½ä»¤åæºè½é« | åéç¹å®æ¡æ¶ |

| **éé¢æ¹å¼** | Git worktreesï¼çå¯¦åæ¯ï¼ | å®¹å¨æèæ¬ç°å¢?|



---



## éä½åç



<table>

<tr>

<td width="33%">



### æºè½é«ååæºè½é«

é å°èå¼å?`agentteam spawn` å»ºç«å·¥ä½èãæ¯åå·¥ä½èé½ææç¨ç«ç?**git worktree**ã?*tmux è¦çª**å?*èº«ä»½æ¨è­**ã?


```bash

agentteam spawn --team my-team \

  --agent-name worker1 \

  --task "Implement auth module"

```



</td>

<td width="33%">



### æºè½é«ä¹éäºç¸å°è©?
å·¥ä½èæª¢æ¥æ¶ä»¶å£ãæ´æ°ä»»åãåå ±çµæ?â?å¨é¨éé**èªåæ³¨å¥**æç¤ºè©çå½ä»¤åæä»¤å®æã?


```bash

agentteam task list my-team --owner me

agentteam inbox send my-team leader \

  "Auth done. All tests passing."

```



</td>

<td width="33%">



### æ¨åªéè§ç?
ééåå²å¼?tmux æª¢è¦æ?Web ä»é¢ç£æ§éç¾¤ãé å°èè² è²¬åèª¿ä¸åã?


```bash

agentteam board attach my-team

# Or web dashboard

agentteam board serve --port 8080

```



</td>

</tr>

</table>



---



## å¿«ééå§?


### æ¹å¼ä¸ï¼è®æºè½é«èªè¡é©åï¼æ¨è¦ï¼?


å®è£ AgentTeamï¼ç¶å¾åæ¨çæºè½é«ç¼åºæç¤ºï¼



```

"Build a web app. Use agentteam to split the work across multiple agents."

```



æºè½é«èªåå»ºç«åéãååå·¥ä½èãåéä»»åä¸¦åèª¿ â?å¨é¨éé `agentteam` å½ä»¤åå®æã?


### æ¹å¼äºï¼æåé©å



```bash

# Create a team

agentteam team spawn-team my-team -d "Build the auth module" -n leader



# Spawn workers â?each gets a git worktree + tmux window

agentteam spawn --team my-team --agent-name alice --task "Implement OAuth2 flow"

agentteam spawn --team my-team --agent-name bob   --task "Write unit tests for auth"



# Watch them work

agentteam board attach my-team

```



### æ¯æ´çæºè½é«



| æºè½é«?| ååæä»¤ | çæ?|

|-------|--------------|--------|

| [OpenClaw](https://openclaw.ai) | `agentteam spawn tmux openclaw --team ...` | **é è¨­** |

| [Claude Code](https://claude.ai/claude-code) | `agentteam spawn tmux claude --team ...` | å®æ´æ¯æ´ |

| [Codex](https://openai.com/codex) | `agentteam spawn tmux codex --team ...` | å®æ´æ¯æ´ |

| [nanobot](https://github.com/HKUDS/nanobot) | `agentteam spawn tmux nanobot --team ...` | å®æ´æ¯æ´ |

| [Cursor](https://cursor.com) | `agentteam spawn subprocess cursor --team ...` | å¯¦é©æ?|

| èªè¨è³æ¬ | `agentteam spawn subprocess python --team ...` | å®æ´æ¯æ´ |



---



## å®è£



### ç¬¬ä¸æ­¥ï¼åç½®æ¢ä»¶



AgentTeam éè¦?**Python 3.10+**ã?*tmux** ä»¥åè³å°ä¸åå½ä»¤åç¨å¼ç¢¼æºè½é«ï¼OpenClawãClaude CodeãCodex ç­ï¼ã?


**æª¢æ¥æ¨å·²æçç°å¢ï¼?*



```bash

python3 --version   # Need 3.10+

tmux -V             # Need any version

openclaw --version  # Or: claude --version / codex --version

```



**å®è£ç¼ºå°çåç½®æ¢ä»¶ï¼**



| å·¥å· | macOS | Ubuntu/Debian |

|------|-------|---------------|

| Python 3.10+ | `brew install python@3.12` | `sudo apt update && sudo apt install python3 python3-pip` |

| tmux | `brew install tmux` | `sudo apt install tmux` |

| OpenClaw | `pip install openclaw` | `pip install openclaw` |



> å¦æä½¿ç¨ Claude Code æ?Codex èé OpenClawï¼è«æç§å®ååèªçæä»¶é²è¡å®è£ãOpenClaw æ¯é è¨­é¸é ï¼ä½ä¸¦éå´æ ¼å¿éã?


### ç¬¬äºæ­¥ï¼å®è£ AgentTeam



> **â ï¸ è«å¿ç´æ¥å·è¡ `pip install agentteam` æ?`npm install -g agentteam`ï¼?*

> - `pip install agentteam` æå®è£?PyPI ä¸çä¸æ¸¸çæ¬ï¼é è¨­ä½¿ç?`claude` ä¸ç¼ºå°?OpenClaw é©éã?
> - `npm install -g agentteam` æå®è£ä¸åç¡éçæ¶æ³¨å¥ä»¶ï¼ç¼ä½è?`a9logic`ï¼ãå¦æ?`agentteam --version` é¡¯ç¤º "Coming Soon"ï¼è¡¨ç¤ºè£é¯äºï¼è«å?`npm uninstall -g agentteam`ã?
>

> **æ­£ç¢ºåæ³æ¯ä¸é¢ä¸æ¢å½ä»¤ââclone ä¹å¾ç?`pip install -e .` æ¯å¿é çï¼å®å¾æ¬å°ååº«å®è£ï¼ä¸æ¯å¾ PyPIã?*



```bash

git clone https://github.com/win4r/ClawTeam-OpenClaw-OpenClaw.git

cd AgentTeam-OpenClaw

pip install -e .    # â?å¿é å·è¡ï¼å¾æ¬å°ååº«å®è£ï¼ä¸åæ¼ pip install agentteam

```



å¯é¸ â?P2P å³è¼¸å±¤ï¼ZeroMQï¼ï¼



```bash

pip install -e ".[p2p]"

```



### ç¬¬ä¸æ­¥ï¼å»ºç« `~/bin/AgentTeam` ç¬¦èé£çµ



è¢«ååçæºè½é«å¨å¨æ°ç?shell ç°å¢ä¸­å·è¡ï¼å¯è½æ²æå°?pip ç?bin ç®éå å¥ PATHãå¨ `~/bin` ä¸­å»ºç«ç¬¦èé£çµå¯ç¢ºä¿?`agentteam` å§çµå¯éï¼?


```bash

mkdir -p ~/bin

ln -sf "$(which agentteam)" ~/bin/AgentTeam

```



å¦æ `which agentteam` æ²æåå³çµæï¼è«æåå°æ¾äºé²ä½æªæ¡ï¼?


```bash

# Common locations:

# ~/.local/bin/AgentTeam

# /opt/homebrew/bin/AgentTeam

# /usr/local/bin/AgentTeam

# /Library/Frameworks/Python.framework/Versions/3.*/bin/AgentTeam

find / -name agentteam -type f 2>/dev/null | head -5

```



ç¶å¾ç¢ºä¿ `~/bin` å¨æ¨ç?PATH ä¸?â?å¦æå°æªå å¥ï¼è«å°ä»¥ä¸å§å®¹æ°å¢è³ `~/.zshrc` æ?`~/.bashrc`ï¼?


```bash

export PATH="$HOME/bin:$PATH"

```



### ç¬¬åæ­¥ï¼å®è£ OpenClaw æè½ï¼åé OpenClaw ä½¿ç¨èï¼



æè½æªæ¡è® OpenClaw æºè½é«è½å¤ ééèªç¶èªè¨ä½¿ç¨ AgentTeamãå¦ææ¨ä¸ä½¿ç?OpenClawï¼è«è·³éæ­¤æ­¥é©ã?


```bash

mkdir -p ~/.openclaw/workspace/skills/AgentTeam

cp skills/openclaw/SKILL.md ~/.openclaw/workspace/skills/AgentTeam/SKILL.md

```



### ç¬¬äºæ­¥ï¼éç½®å·è¡ææ¬ï¼åé?OpenClaw ä½¿ç¨èï¼



è¢«ååç OpenClaw æºè½é«éè¦æ¬éä¾å·è¡ `agentteam` æä»¤ãå¦ææ²æéç½®ï¼æºè½é«æå¨äºåå¼æ¬éæç¤ºä¸­è¢«é»å¡ã?


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



> å¦æ `openclaw approvals` å¤±æï¼OpenClaw ééå¨å¯è½æªå¨å·è¡ãè«åååééå¨ï¼ç¶å¾éè©¦ã?


### ç¬¬å­æ­¥ï¼é©è­



```bash

agentteam --version          # Should print version

agentteam config health      # Should show all green

```



å¦æä½¿ç¨ OpenClawï¼ééé©è­æè½æ¯å¦å·²è¼å¥ï¼?


```bash

openclaw skills list | grep agentteam

```



### èªååå®è£è³æ?


ä¸è¿°ç¬¬äºè³å­æ­¥ä¹å¯ééå®ä¸è³æ¬å®æï¼?


```bash

git clone https://github.com/win4r/ClawTeam-OpenClaw-OpenClaw.git

cd AgentTeam-OpenClaw

bash scripts/install-openclaw.sh

```



### çé£æè§£



| åé¡ | åå  | è§£æ±ºæ¹æ³ |

|---------|-------|-----|

| `agentteam: command not found` | pip ç?bin ç®éæªå¨ PATH ä¸?| å·è¡ç¬¬ä¸æ­¥ï¼ç¬¦èé£çµ + PATHï¼?|

| è¢«ååçæºè½é«æ¾ä¸å° `agentteam` | æºè½é«å¨æ²æ pip PATH çå¨æ?shell ä¸­å·è¡?| é©è­ `~/bin/AgentTeam` ç¬¦èé£çµæ¯å¦å­å¨ä¸?`~/bin` å·²å¨ PATH ä¸?|

| `openclaw approvals` å¤±æ | ééå¨æªå¨å·è¡?| ååå?`openclaw gateway`ï¼ç¶å¾éè©¦ç¬¬äºæ­¥ |

| `exec-approvals.json not found` | OpenClaw å¾æªå·è¡é?| åå·è¡ä¸æ¬?`openclaw` ä»¥ç¢çè¨­å®æªï¼ç¶å¾éè©¦ç¬¬äºæ­¥ |

| æºè½é«å¨æ¬éæç¤ºä¸­è¢«é»å¡ | å·è¡ææ¬å®å¨æ¨¡å¼ç?"full" | å·è¡ç¬¬äºæ­¥åæçº "allowlist" |

| `pip install -e .` å¤±æ | ç¼ºå°å»ºç½®ä¾è³´ | åå·è¡?`pip install hatchling` |

| `agentteam --version` é¡¯ç¤º "Coming Soon" | èª¤è£äº?npm ååæ¶æ³¨å¥ä»¶ï¼`a9logic`ï¼èæ¬å°æ¡ç¡éï¼ | `npm uninstall -g agentteam`ï¼ç¶å¾æç¬¬äºæ­¥éæ°å®è£?|



---



## ä½¿ç¨æ¡ä¾



### 1. èªä¸»æ©å¨å­¸ç¿ç ç©¶ â?8 åæºè½é« x 8 å¼?GPU



åºæ¼ [@karpathy/autoresearch](https://github.com/karpathy/autoresearch)ãä¸å¥æç¤ºè©å³å¯å?H100 ä¸åå?8 åç ç©¶æºè½é«ï¼èªä¸»è¨­è¨è¶é?2000 åå¯¦é©ã?


```

Human: "Use 8 GPUs to optimize train.py. Read program.md for instructions."



Leader agent:

âââ Spawns 8 agents, each assigned a research direction (depth, width, LR, batch size...)

âââ Each agent gets its own git worktree for isolated experiments

âââ Every 30 min: checks results, cross-pollinates best configs to new agents

âââ Reassigns GPUs as agents finish â?fresh agents start from best known config

âââ Result: val_bpb 1.044 â?0.977 (6.4% improvement) across 2430 experiments in ~30 GPU-hours

```



å®æ´çµæï¼[novix-science/autoresearch](https://github.com/novix-science/autoresearch)



### 2. æºè½é«é©åçè»é«å·¥ç¨



```

Human: "Build a full-stack todo app with auth, database, and React frontend."



Leader agent:

âââ Creates tasks with dependency chains (API schema â?auth + DB â?frontend â?tests)

âââ Spawns 5 agents (architect, 2 backend, frontend, tester) in separate worktrees

âââ Dependencies auto-resolve: architect completes â?backend unblocks â?tester unblocks

âââ Agents coordinate via inbox: "Here's the OpenAPI spec", "Auth endpoints ready"

âââ Leader merges all worktrees into main when complete

```



### 3. äººå·¥æºæ§å°æ²åºé â?æ¨¡æ¿åå



ä¸å?TOML æ¨¡æ¿å³å¯ééä¸æ¢æä»¤ååå®æ´ç 7 æºè½é«æè³åéï¼



```bash

agentteam launch hedge-fund --team fund1 --goal "Analyze AAPL, MSFT, NVDA for Q2 2026"

```



5 ååæå¸«æºè½é«ï¼å¹å¼åãæé·åãæè¡åãåºæ¬é¢ãæç·é¢ï¼ä¸¦è¡å·¥ä½ãé¢¨éªç®¡çæºè½é«ç¶åææè¨èãæè³çµåç®¡çæºè½é«ååºæçµæ±ºç­ã?


æ¨¡æ¿æ?TOML æªæ¡ â?æ¨å¯ä»¥çºä»»ä½é å**å»ºç«èªå·±çæ¨¡æ?*ã?


---



## åè½ç¹æ?


<table>

<tr>

<td width="50%">



### æºè½é«èªçµç¹

- é å°èååä¸¦ç®¡çå·¥ä½è?
- èªåæ³¨å¥åèª¿æç¤ºè©?â?é¶æåè¨­å®?
- å·¥ä½èèªè¡åå ±çæåéç½®çæ?
- ä»»ä½å½ä»¤åæºè½é«çå¯åè



### å·¥ä½åéé¢

- æ¯åæºè½é«ææç¨ç«ç?**git worktree**

- ä¸¦è¡æºè½é«ä¹éä¸æç¢çåä½µè¡çª?
- æ¯æ´æª¢æ¥é»ãåä½µåæ¸çæä»¤

- åæ¯å½åè¦åï¼`agentteam/{team}/{agent}`



### å«ä¾è³´éä¿çä»»åè¿½è¹¤

- å±äº«çæ¿ï¼`pending` â?`in_progress` â?`completed` / `blocked`

- `--blocked-by` ä¾è³´éï¼å®ææèªåè§£é¤é»å¡?
- `task wait` é»å¡ç­å¾ç´å°ææä»»åå®æ?


</td>

<td width="50%">



### æºè½é«ééè¨

- é»å°é»æ¶ä»¶å£ï¼å³éãæ¥æ¶ãé è¦½ï¼

- åææåéæå¡å»£æ?
- åºæ¼æªæ¡ï¼é è¨­ï¼æ?ZeroMQ P2P å³è¼¸



### ç£æ§èåè¡¨æ¿

- `board show` â?çµç«¯æ©çæ?
- `board live` â?èªåéæ°æ´çåè¡¨æ¿

- `board attach` â?åå²å¼?tmux æª¢è¦æææºè½é«

- `board serve` â?å³ææ´æ°ç?Web ä»é¢



### åéæ¨¡æ¿

- TOML æªæ¡å®ç¾©åéååï¼è§è²ãä»»åãæç¤ºè©ï¼?
- ä¸æ¢æä»¤ï¼`agentteam launch <template>`

- è®æ¸æ¿æï¼`{goal}`ã`{team_name}`ã`{agent_name}`

- **ææºè½é«åéæ¨¡å**ï¼é è¦½çï¼ï¼çºä¸åè§è²åéä¸åæ¨¡å?â?è©³è¦[ä¸æ¹](#ææºè½é«åéæ¨¡åé è¦½ç?



</td>

</tr>

</table>



**æ´å¤åè½ï¼?*è¨ç«å¯©æ¹å·¥ä½æµãåªéççå½é±æç®¡çãæææä»¤æ¯æ?`--json` è¼¸åºãè·¨æ©å¨æ¯æ´ï¼NFS/SSHFS æ?P2Pï¼ãå¤ä½¿ç¨èå½åç©ºéãå«èªååæ»¾çååé©è­ã`fcntl` æªæ¡éç¢ºä¿ä¸¦è¡å®å¨ã?


---



## OpenClaw æ´å



æ¬ååçæ¬å° [OpenClaw](https://openclaw.ai) è¨­çº**é è¨­æºè½é«?*ãæ²æ?AgentTeam æï¼æ¯å?OpenClaw æºè½é«åèªå­¤ç«å·¥ä½ãAgentTeam å°å¶è½åçºå¤æºè½é«å¹³å°ã?


| è½å | å®ç¨ä½¿ç¨ OpenClaw | OpenClaw + AgentTeam |

|-----------|---------------|-------------------|

| **ä»»ååé** | æåéä¸å³éè¨æ?| é å°èèªä¸»æåãåéãç£æ?|

| **ä¸¦è¡éç¼** | å±äº«å·¥ä½ç®é | æ¯åæºè½é«ç¨ç«ç?git worktrees |

| **ä¾è³´éä¿** | æåè¼ªè©¢ | `--blocked-by` èªåè§£é¤é»å¡ |

| **éè¨æ¹å¼** | åéé AGI ä¸­ç¹¼ | ç´æ¥é»å°é»æ¶ä»¶å£ + å»£æ­ |

| **å¯è§æ¸¬æ?* | é±è®æ¥èª | çæ¿ + åå²å¼?tmux æª¢è¦ |



å®è£æè½å¾ï¼å³å¯å¨ä»»ä½é »éèæ¨ç?OpenClaw æ©å¨äººå°è©±ï¼



| æ¨èªªçå§å®?| ç¼ççäºæ?|

|-------------|-------------|

| "å»ºç«ä¸å?5 æºè½é«åéä¾éç¼ Web æç¨ç¨å¼" | å»ºç«åéãä»»åï¼å?tmux ä¸­åå?5 åæºè½é« |

| "ååä¸åå°æ²åºéåæåé? | å·è¡ `agentteam launch hedge-fund`ï¼åå?7 åæºè½é« |

| "æª¢æ¥æçæºè½é«åéçæ? | å·è¡ `agentteam board show` é¡¯ç¤ºçæ¿è¼¸åº |



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



## æ¶æ§



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



ææçæä»¥ JSON æªæ¡å½¢å¼å²å­å?`~/.agentteam/` ä¸­ãç¡éè³æåº«ï¼ç¡éä¼ºæå¨ãéé `fcntl` æªæ¡éçåå­å¯«å¥ç¢ºä¿ç¶æ©å®å¨ã?


| è¨­å®é ?| ç°å¢è®æ¸ | é è¨­å?|

|---------|---------|---------|

| è³æç®é | `AgentTeam_DATA_DIR` | `~/.agentteam` |

| å³è¼¸å±?| `AgentTeam_TRANSPORT` | `file` |

| å·¥ä½åæ¨¡å¼ | `AgentTeam_WORKSPACE` | `auto` |

| ååå¾ç«¯ | `AgentTeam_DEFAULT_BACKEND` | `tmux` |



---



## æä»¤åè?


<details open>

<summary><strong>æ ¸å¿æä»¤</strong></summary>



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

<summary><strong>å·¥ä½åãè¨ç«ãçå½é±æãè¨­å®?/strong></summary>



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



## ææºè½é«åéæ¨¡åï¼é è¦½çï¼?


> **åæ¯ï¼?*[`feat/per-agent-model-assignment`](https://github.com/win4r/ClawTeam-OpenClaw-OpenClaw/tree/feat/per-agent-model-assignment)

>

> æ­¤åè½å¯å¨ç¨ç«åæ¯ä¸é²è¡æ©ææ¸¬è©¦ãå¾éå¥ç?OpenClaw `--model` ææ¨æ­£å¼ç¼å¸å¾ï¼å°åä½µè³ `main`ã?


çºä¸åæºè½é«è§è²åéä¸åæ¨¡åï¼å¨å¤æºè½é«éç¾¤ä¸­å¯¦ç¾æ´ä½³çææ¬/æè½æ¬è¡¡ã?


```bash

# Install from the feature branch

pip install -e "git+https://github.com/win4r/ClawTeam-OpenClaw-OpenClaw.git@feat/per-agent-model-assignment#egg=agentteam"

```



**æ¨¡æ¿ä¸­çææºè½é«æ¨¡åéç½®ï¼?*

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



**å½ä»¤åææ¨ï¼**

```bash

agentteam spawn --model opus                          # single agent

agentteam launch my-template --model gpt-5.4          # override all agents

agentteam launch my-template --model-strategy auto     # auto-assign by role

```



è©³è¦ [issue #1](https://github.com/win4r/ClawTeam-OpenClaw-OpenClaw/issues/1) çå®æ´åè½éæ±èè¨è«ã?


---



## ç¼å±è·¯ç·



| çæ¬ | å§å®¹ | çæ?|

|---------|------|--------|

| v0.3 | æªæ¡ + P2P å³è¼¸ãWeb ä»é¢ãå¤ä½¿ç¨èãæ¨¡æ?| å·²ç¼å¸?|

| v0.4 | Redis å³è¼¸ â?è·¨æ©å¨è¨æ¯å³é?| è¨ç«ä¸?|

| v0.5 | å±äº«çæå±¤ â?è·¨æ©å¨åéè¨­å®?| è¨ç«ä¸?|

| v0.6 | æºè½é«å¸å ?â?ç¤¾ç¾¤æ¨¡æ¿ | æ¢ç´¢ä¸?|

| v0.7 | èªé©ææç¨?â?åæä»»åéæ°åé | æ¢ç´¢ä¸?|

| v1.0 | çç¢ç­ç´ â?èªè­ãæ¬éãç¨½æ ¸æ¥èª?| æ¢ç´¢ä¸?|



---



## åèè²¢ç»



æåæ­¡è¿åé¡è²¢ç»ï¼



- **æºè½é«æ´å?* â?æ¯æ´æ´å¤å½ä»¤åæºè½é«

- **åéæ¨¡æ¿** â?é¢åæ°é åç TOML æ¨¡æ¿

- **å³è¼¸å¾ç«¯** â?RedisãNATS ç­?
- **åè¡¨æ¿æ¹é?* â?Web ä»é¢ãGrafana

- **æä»¶** â?æå­¸èæä½³å¯¦è¸?


---



## è´è¬



- [@karpathy/autoresearch](https://github.com/karpathy/autoresearch) â?èªä¸»æ©å¨å­¸ç¿ç ç©¶æ¡æ¶

- [OpenClaw](https://openclaw.ai) â?é è¨­æºè½é«å¾ç«?
- [Claude Code](https://claude.ai/claude-code) å?[Codex](https://openai.com/codex) â?æ¯æ´çäººå·¥æºæ§ç¨å¼ç¢¼æºè½é«?
- [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) â?å°æ²åºéæ¨¡æ¿éæä¾æº

- [CLI-Anything](https://github.com/HKUDS/CLI-Anything) â?å§å¦¹å°æ¡



## ææ¬æ¢æ¬¾



MIT â?å¯èªç±ä½¿ç¨ãä¿®æ¹èåç¼ã?


---



<div align="center">



**AgentTeam** â?*æºè½é«éç¾¤åä½ã?



</div>

