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

  <strong>Coordination multi-agents en essaim pour agents de codage CLI â?<a href="https://openclaw.ai">OpenClaw</a> par dÃ©faut</strong>

</p>



<p align="center">

  <a href="https://github.com/HKUDS/AgentTeam"><img src="https://img.shields.io/badge/upstream-HKUDS%2FAgentTeam-purple?style=for-the-badge" alt="Upstream"></a>

  <a href="#-dÃ©marrage-rapide"><img src="https://img.shields.io/badge/Quick_Start-3_min-blue?style=for-the-badge" alt="DÃ©marrage rapide"></a>

  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="Licence"></a>

</p>



<p align="center">

  <img src="https://img.shields.io/badge/python-â?.10-blue?logo=python&logoColor=white" alt="Python">

  <img src="https://img.shields.io/badge/agents-OpenClaw_%7C_Claude_Code_%7C_Codex_%7C_nanobot-blueviolet" alt="Agents">

  <img src="https://img.shields.io/badge/transport-File_%7C_ZeroMQ_P2P-orange" alt="Transport">

  <img src="https://img.shields.io/badge/version-0.3.0-teal" alt="Version">

</p>



> **Fork de [HKUDS/AgentTeam](https://github.com/HKUDS/AgentTeam)** avec intÃ©gration approfondie d'OpenClaw : agent `openclaw` par dÃ©faut, isolation de session par agent, configuration automatique des autorisations d'exÃ©cution, et backends de lancement renforcÃ©s pour la production. Toutes les corrections upstream sont synchronisÃ©es.



Vous dÃ©finissez l'objectif. L'essaim d'agents s'occupe du reste â?lancement de travailleurs, rÃ©partition des tÃ¢ches, coordination et fusion des rÃ©sultats.



Compatible avec [OpenClaw](https://openclaw.ai) (par dÃ©faut), [Claude Code](https://claude.ai/claude-code), [Codex](https://openai.com/codex), [nanobot](https://github.com/HKUDS/nanobot), [Cursor](https://cursor.com), et tout agent CLI.



---



## Pourquoi AgentTeam ?



Les agents IA actuels sont puissants mais travaillent de maniÃ¨re **isolÃ©e**. AgentTeam permet aux agents de s'auto-organiser en Ã©quipes â?rÃ©partissant le travail, communiquant et convergeant vers des rÃ©sultats sans micro-gestion humaine.



| | AgentTeam | Autres frameworks multi-agents |

|---|---------|----------------------------|

| **Qui l'utilise** | Les agents IA eux-mÃªmes | Les humains Ã©crivant du code d'orchestration |

| **Mise en place** | `pip install` + un prompt | Docker, API cloud, fichiers YAML |

| **Infrastructure** | SystÃ¨me de fichiers + tmux | Redis, files de messages, bases de donnÃ©es |

| **Support d'agents** | Tout agent CLI | SpÃ©cifique au framework uniquement |

| **Isolation** | Git worktrees (vraies branches) | Conteneurs ou environnements virtuels |



---



## Comment Ã§a marche



<table>

<tr>

<td width="33%">



### Les agents engendrent des agents

Le leader appelle `agentteam spawn` pour crÃ©er des travailleurs. Chacun obtient son propre **git worktree**, sa **fenÃªtre tmux** et son **identitÃ©**.



```bash

agentteam spawn --team my-team \

  --agent-name worker1 \

  --task "Implement auth module"

```



</td>

<td width="33%">



### Les agents communiquent entre eux

Les travailleurs consultent leurs boÃ®tes de rÃ©ception, mettent Ã  jour les tÃ¢ches et rapportent les rÃ©sultats â?le tout via des commandes CLI **auto-injectÃ©es** dans leur prompt.



```bash

agentteam task list my-team --owner me

agentteam inbox send my-team leader \

  "Auth done. All tests passing."

```



</td>

<td width="33%">



### Vous observez simplement

Surveillez l'essaim depuis une vue tmux en mosaÃ¯que ou l'interface Web. Le leader gÃ¨re la coordination.



```bash

agentteam board attach my-team

# Or web dashboard

agentteam board serve --port 8080

```



</td>

</tr>

</table>



---



## DÃ©marrage rapide



### Option 1 : Laisser l'agent piloter (RecommandÃ©)



Installez AgentTeam, puis donnez cette instruction Ã  votre agent :



```

"Build a web app. Use agentteam to split the work across multiple agents."

```



L'agent crÃ©e automatiquement une Ã©quipe, lance des travailleurs, assigne les tÃ¢ches et coordonne â?le tout via la CLI `agentteam`.



### Option 2 : Piloter manuellement



```bash

# Create a team

agentteam team spawn-team my-team -d "Build the auth module" -n leader



# Spawn workers â?each gets a git worktree + tmux window

agentteam spawn --team my-team --agent-name alice --task "Implement OAuth2 flow"

agentteam spawn --team my-team --agent-name bob   --task "Write unit tests for auth"



# Watch them work

agentteam board attach my-team

```



### Agents supportÃ©s



| Agent | Commande de lancement | Statut |

|-------|--------------|--------|

| [OpenClaw](https://openclaw.ai) | `agentteam spawn tmux openclaw --team ...` | **Par dÃ©faut** |

| [Claude Code](https://claude.ai/claude-code) | `agentteam spawn tmux claude --team ...` | Support complet |

| [Codex](https://openai.com/codex) | `agentteam spawn tmux codex --team ...` | Support complet |

| [nanobot](https://github.com/HKUDS/nanobot) | `agentteam spawn tmux nanobot --team ...` | Support complet |

| [Cursor](https://cursor.com) | `agentteam spawn subprocess cursor --team ...` | ExpÃ©rimental |

| Scripts personnalisÃ©s | `agentteam spawn subprocess python --team ...` | Support complet |



---



## Installation



### Ãtape 1 : PrÃ©requis



AgentTeam nÃ©cessite **Python 3.10+**, **tmux**, et au moins un agent de codage CLI (OpenClaw, Claude Code, Codex, etc.).



**VÃ©rifiez ce que vous avez dÃ©jÃ  :**



```bash

python3 --version   # Need 3.10+

tmux -V             # Need any version

openclaw --version  # Or: claude --version / codex --version

```



**Installez les prÃ©requis manquants :**



| Outil | macOS | Ubuntu/Debian |

|------|-------|---------------|

| Python 3.10+ | `brew install python@3.12` | `sudo apt update && sudo apt install python3 python3-pip` |

| tmux | `brew install tmux` | `sudo apt install tmux` |

| OpenClaw | `pip install openclaw` | `pip install openclaw` |



> Si vous utilisez Claude Code ou Codex au lieu d'OpenClaw, installez-les selon leur propre documentation. OpenClaw est l'agent par dÃ©faut mais n'est pas strictement requis.



### Ãtape 2 : Installer AgentTeam



> **â ï¸ N'exÃ©cutez PAS `pip install agentteam` ou `npm install -g agentteam` directement :**

> - `pip install agentteam` installe la version upstream depuis PyPI, qui utilise `claude` par dÃ©faut et ne contient pas les adaptations OpenClaw.

> - `npm install -g agentteam` installe un paquet usurpateur sans lien (Ã©diteur `a9logic`). Si `agentteam --version` affiche "Coming Soon", c'est le mauvais paquet. ExÃ©cutez d'abord `npm uninstall -g agentteam`.

>

> **Utilisez les trois commandes ci-dessous â?le `pip install -e .` aprÃ¨s le clone est obligatoire. Il installe depuis le dÃ©pÃ´t local, pas depuis PyPI.**



```bash

git clone https://github.com/win4r/AgentTeam-OpenClaw.git

cd AgentTeam-OpenClaw

pip install -e .    # â?Obligatoire ! Installe depuis le dÃ©pÃ´t local, PAS identique Ã  pip install agentteam

```



Optionnel â?Transport P2P (ZeroMQ) :



```bash

pip install -e ".[p2p]"

```



### Ãtape 3 : CrÃ©er le lien symbolique `~/bin/AgentTeam`



Les agents lancÃ©s s'exÃ©cutent dans des shells vierges qui n'ont pas forcÃ©ment le rÃ©pertoire bin de pip dans le PATH. Un lien symbolique dans `~/bin` garantit que `agentteam` est toujours accessible :



```bash

mkdir -p ~/bin

ln -sf "$(which agentteam)" ~/bin/AgentTeam

```



Si `which agentteam` ne retourne rien, trouvez le binaire manuellement :



```bash

# Common locations:

# ~/.local/bin/AgentTeam

# /opt/homebrew/bin/AgentTeam

# /usr/local/bin/AgentTeam

# /Library/Frameworks/Python.framework/Versions/3.*/bin/AgentTeam

find / -name agentteam -type f 2>/dev/null | head -5

```



Puis assurez-vous que `~/bin` est dans votre PATH â?ajoutez ceci Ã  `~/.zshrc` ou `~/.bashrc` si ce n'est pas le cas :



```bash

export PATH="$HOME/bin:$PATH"

```



### Ãtape 4 : Installer le skill OpenClaw (utilisateurs OpenClaw uniquement)



Le fichier skill apprend aux agents OpenClaw comment utiliser AgentTeam en langage naturel. Ignorez cette Ã©tape si vous n'utilisez pas OpenClaw.



```bash

mkdir -p ~/.openclaw/workspace/skills/AgentTeam

cp skills/openclaw/SKILL.md ~/.openclaw/workspace/skills/AgentTeam/SKILL.md

```



### Ãtape 5 : Configurer les autorisations d'exÃ©cution (utilisateurs OpenClaw uniquement)



Les agents OpenClaw lancÃ©s ont besoin de la permission d'exÃ©cuter les commandes `agentteam`. Sans cela, les agents seront bloquÃ©s par des invites de permission interactives.



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



> Si `openclaw approvals` Ã©choue, la passerelle OpenClaw n'est peut-Ãªtre pas en cours d'exÃ©cution. DÃ©marrez-la d'abord, puis rÃ©essayez.



### Ãtape 6 : VÃ©rification



```bash

agentteam --version          # Should print version

agentteam config health      # Should show all green

```



Si vous utilisez OpenClaw, vÃ©rifiez Ã©galement que le skill est chargÃ© :



```bash

openclaw skills list | grep agentteam

```



### Installateur automatisÃ©



Les Ã©tapes 2 Ã  6 ci-dessus sont Ã©galement disponibles via un script unique :



```bash

git clone https://github.com/win4r/AgentTeam-OpenClaw.git

cd AgentTeam-OpenClaw

bash scripts/install-openclaw.sh

```



### DÃ©pannage



| ProblÃ¨me | Cause | Solution |

|---------|-------|-----|

| `agentteam: command not found` | RÃ©pertoire bin de pip absent du PATH | ExÃ©cutez l'Ãtape 3 (lien symbolique + PATH) |

| Les agents lancÃ©s ne trouvent pas `agentteam` | Les agents s'exÃ©cutent dans des shells vierges sans le PATH de pip | VÃ©rifiez que le lien symbolique `~/bin/AgentTeam` existe et que `~/bin` est dans le PATH |

| `openclaw approvals` Ã©choue | Passerelle non en cours d'exÃ©cution | DÃ©marrez `openclaw gateway` d'abord, puis rÃ©essayez l'Ãtape 5 |

| `exec-approvals.json not found` | OpenClaw n'a jamais Ã©tÃ© exÃ©cutÃ© | ExÃ©cutez `openclaw` une fois pour gÃ©nÃ©rer la configuration, puis rÃ©essayez l'Ãtape 5 |

| Les agents sont bloquÃ©s par les invites de permission | La sÃ©curitÃ© des autorisations d'exÃ©cution est en mode "full" | ExÃ©cutez l'Ãtape 5 pour passer en mode "allowlist" |

| `pip install -e .` Ã©choue | DÃ©pendances de build manquantes | ExÃ©cutez d'abord `pip install hatchling` |

| `agentteam --version` affiche "Coming Soon" | Paquet npm usurpateur installÃ© par erreur (`a9logic`, sans lien avec ce projet) | `npm uninstall -g agentteam`, puis rÃ©installer selon l'Ã©tape 2 |



---



## Cas d'utilisation



### 1. Recherche ML autonome â?8 agents x 8 GPU



BasÃ© sur [@karpathy/autoresearch](https://github.com/karpathy/autoresearch). Un seul prompt lance 8 agents de recherche sur des H100 qui conÃ§oivent plus de 2000 expÃ©riences de maniÃ¨re autonome.



```

Human: "Use 8 GPUs to optimize train.py. Read program.md for instructions."



Leader agent:

âââ Lance 8 agents, chacun assignÃ© Ã  une direction de recherche (profondeur, largeur, LR, taille de batch...)

âââ Chaque agent obtient son propre git worktree pour des expÃ©riences isolÃ©es

âââ Toutes les 30 min : vÃ©rifie les rÃ©sultats, croise les meilleures configurations vers de nouveaux agents

âââ RÃ©assigne les GPU Ã  mesure que les agents terminent â?les nouveaux agents dÃ©marrent depuis la meilleure configuration connue

âââ RÃ©sultat : val_bpb 1.044 â?0.977 (amÃ©lioration de 6.4%) sur 2430 expÃ©riences en ~30 heures-GPU

```



RÃ©sultats complets : [novix-science/autoresearch](https://github.com/novix-science/autoresearch)



### 2. IngÃ©nierie logicielle agentique



```

Human: "Build a full-stack todo app with auth, database, and React frontend."



Leader agent:

âââ CrÃ©e des tÃ¢ches avec chaÃ®nes de dÃ©pendances (schÃ©ma API â?auth + BD â?frontend â?tests)

âââ Lance 5 agents (architecte, 2 backend, frontend, testeur) dans des worktrees sÃ©parÃ©s

âââ Les dÃ©pendances se rÃ©solvent automatiquement : architecte terminÃ© â?backend dÃ©bloquÃ© â?testeur dÃ©bloquÃ©

âââ Les agents coordonnent via la boÃ®te de rÃ©ception : "Voici la spÃ©c OpenAPI", "Endpoints d'auth prÃªts"

âââ Le leader fusionne tous les worktrees dans main une fois terminÃ©

```



### 3. Hedge Fund IA â?Lancement par template



Un template TOML lance une Ã©quipe d'investissement complÃ¨te de 7 agents en une seule commande :



```bash

agentteam launch hedge-fund --team fund1 --goal "Analyze AAPL, MSFT, NVDA for Q2 2026"

```



5 agents analystes (valeur, croissance, technique, fondamentaux, sentiment) travaillent en parallÃ¨le. Le gestionnaire de risques synthÃ©tise tous les signaux. Le gestionnaire de portefeuille prend les dÃ©cisions finales.



Les templates sont des fichiers TOML â?**crÃ©ez les vÃ´tres** pour n'importe quel domaine.



---



## FonctionnalitÃ©s



<table>

<tr>

<td width="50%">



### Auto-organisation des agents

- Le leader lance et gÃ¨re les travailleurs

- Prompt de coordination auto-injectÃ© â?aucune configuration manuelle

- Les travailleurs rapportent automatiquement leur statut et leur Ã©tat d'inactivitÃ©

- Tout agent CLI peut participer



### Isolation de l'espace de travail

- Chaque agent obtient son propre **git worktree**

- Aucun conflit de fusion entre agents parallÃ¨les

- Commandes de checkpoint, fusion et nettoyage

- Nommage des branches : `agentteam/{team}/{agent}`



### Suivi des tÃ¢ches avec dÃ©pendances

- Kanban partagÃ© : `pending` â?`in_progress` â?`completed` / `blocked`

- ChaÃ®nes `--blocked-by` avec dÃ©blocage automatique Ã  l'achÃ¨vement

- `task wait` bloque jusqu'Ã  ce que toutes les tÃ¢ches soient terminÃ©es



</td>

<td width="50%">



### Messagerie inter-agents

- BoÃ®tes de rÃ©ception point Ã  point (envoyer, recevoir, consulter)

- Diffusion Ã  tous les membres de l'Ã©quipe

- Transport par fichier (par dÃ©faut) ou ZeroMQ P2P



### Surveillance et tableaux de bord

- `board show` â?kanban en terminal

- `board live` â?tableau de bord auto-rafraÃ®chi

- `board attach` â?vue tmux en mosaÃ¯que de tous les agents

- `board serve` â?interface Web avec mises Ã  jour en temps rÃ©el



### Templates d'Ã©quipe

- Les fichiers TOML dÃ©finissent des archÃ©types d'Ã©quipe (rÃ´les, tÃ¢ches, prompts)

- Une seule commande : `agentteam launch <template>`

- Substitution de variables : `{goal}`, `{team_name}`, `{agent_name}`

- **Attribution de modÃ¨le par agent** (aperÃ§u) : assignez diffÃ©rents modÃ¨les Ã  diffÃ©rents rÃ´les â?voir [ci-dessous](#attribution-de-modÃ¨le-par-agent-aperÃ§u)



</td>

</tr>

</table>



**Aussi :** workflows d'approbation de plans, gestion de cycle de vie gracieuse, sortie `--json` sur toutes les commandes, support multi-machines (NFS/SSHFS ou P2P), espaces de noms multi-utilisateurs, validation du lancement avec rollback automatique, verrouillage de fichiers `fcntl` pour la sÃ©curitÃ© en accÃ¨s concurrent.



---



## IntÃ©gration OpenClaw



Ce fork fait d'[OpenClaw](https://openclaw.ai) l'**agent par dÃ©faut**. Sans AgentTeam, chaque agent OpenClaw travaille de maniÃ¨re isolÃ©e. AgentTeam le transforme en une plateforme multi-agents.



| CapacitÃ© | OpenClaw seul | OpenClaw + AgentTeam |

|-----------|---------------|-------------------|

| **Attribution des tÃ¢ches** | Messagerie manuelle par agent | Le leader divise, assigne et surveille de maniÃ¨re autonome |

| **DÃ©veloppement parallÃ¨le** | RÃ©pertoire de travail partagÃ© | Git worktrees isolÃ©s par agent |

| **DÃ©pendances** | VÃ©rification manuelle | `--blocked-by` avec dÃ©blocage automatique |

| **Communication** | Uniquement via le relais AGI | BoÃ®te de rÃ©ception point Ã  point directe + diffusion |

| **ObservabilitÃ©** | Lecture des logs | Tableau kanban + vue tmux en mosaÃ¯que |



Une fois le skill installÃ©, parlez Ã  votre bot OpenClaw dans n'importe quel canal :



| Ce que vous dites | Ce qui se passe |

|-------------|-------------|

| "CrÃ©e une Ã©quipe de 5 agents pour construire une application web" | CrÃ©e l'Ã©quipe, les tÃ¢ches, lance 5 agents dans tmux |

| "Lance une Ã©quipe d'analyse hedge-fund" | `agentteam launch hedge-fund` avec 7 agents |

| "VÃ©rifie le statut de mon Ã©quipe d'agents" | `agentteam board show` avec sortie kanban |



```

  Vous (Telegram/Discord/TUI)

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



## Architecture



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



Tout l'Ã©tat rÃ©side dans `~/.agentteam/` sous forme de fichiers JSON. Pas de base de donnÃ©es, pas de serveur. Les Ã©critures atomiques avec verrouillage de fichiers `fcntl` garantissent la sÃ©curitÃ© en cas de crash.



| ParamÃ¨tre | Variable d'env. | Valeur par dÃ©faut |

|---------|---------|---------|

| RÃ©pertoire des donnÃ©es | `AgentTeam_DATA_DIR` | `~/.agentteam` |

| Transport | `AgentTeam_TRANSPORT` | `file` |

| Mode d'espace de travail | `AgentTeam_WORKSPACE` | `auto` |

| Backend de lancement | `AgentTeam_DEFAULT_BACKEND` | `tmux` |



---



## RÃ©fÃ©rence des commandes



<details open>

<summary><strong>Commandes principales</strong></summary>



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

<summary><strong>Espace de travail, Plan, Cycle de vie, Configuration</strong></summary>



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



## Attribution de modÃ¨le par agent (AperÃ§u)



> **Branche :** [`feat/per-agent-model-assignment`](https://github.com/win4r/AgentTeam-OpenClaw/tree/feat/per-agent-model-assignment)

>

> Cette fonctionnalitÃ© est disponible pour des tests prÃ©liminaires sur une branche sÃ©parÃ©e. Elle sera fusionnÃ©e dans `main` une fois que le flag `--model` compagnon d'OpenClaw sera livrÃ©.



Assignez diffÃ©rents modÃ¨les Ã  diffÃ©rents rÃ´les d'agents pour de meilleurs compromis coÃ»t/performance dans les essaims multi-agents.



```bash

# Install from the feature branch

pip install -e "git+https://github.com/win4r/AgentTeam-OpenClaw.git@feat/per-agent-model-assignment#egg=agentteam"

```



**ModÃ¨le par agent dans les templates :**

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



**Flags CLI :**

```bash

agentteam spawn --model opus                          # single agent

agentteam launch my-template --model gpt-5.4          # override all agents

agentteam launch my-template --model-strategy auto     # auto-assign by role

```



Voir [issue #1](https://github.com/win4r/AgentTeam-OpenClaw/issues/1) pour la demande de fonctionnalitÃ© complÃ¨te et la discussion.



---



## Feuille de route



| Version | Contenu | Statut |

|---------|------|--------|

| v0.3 | Transport fichier + P2P, interface Web, multi-utilisateurs, templates | LivrÃ© |

| v0.4 | Transport Redis â?messagerie inter-machines | PrÃ©vu |

| v0.5 | Couche d'Ã©tat partagÃ© â?configuration d'Ã©quipe inter-machines | PrÃ©vu |

| v0.6 | Marketplace d'agents â?templates communautaires | En exploration |

| v0.7 | Planification adaptative â?rÃ©assignation dynamique des tÃ¢ches | En exploration |

| v1.0 | QualitÃ© production â?authentification, permissions, journaux d'audit | En exploration |



---



## Contribuer



Les contributions sont les bienvenues :



- **IntÃ©grations d'agents** â?support de nouveaux agents CLI

- **Templates d'Ã©quipe** â?templates TOML pour de nouveaux domaines

- **Backends de transport** â?Redis, NATS, etc.

- **AmÃ©liorations du tableau de bord** â?interface Web, Grafana

- **Documentation** â?tutoriels et bonnes pratiques



---



## Remerciements



- [@karpathy/autoresearch](https://github.com/karpathy/autoresearch) â?framework de recherche ML autonome

- [OpenClaw](https://openclaw.ai) â?backend d'agent par dÃ©faut

- [Claude Code](https://claude.ai/claude-code) et [Codex](https://openai.com/codex) â?agents de codage IA supportÃ©s

- [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) â?inspiration pour le template hedge fund

- [CLI-Anything](https://github.com/HKUDS/CLI-Anything) â?projet frÃ¨re



## Licence



MIT â?libre d'utilisation, de modification et de distribution.



---



<div align="center">



**AgentTeam** â?*Intelligence en essaim d'agents.*



</div>

