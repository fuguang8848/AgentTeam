# AgentTeam åçº§è®¡å v0.5.0

> åºäº SpectrAI æ¶æçµæï¼å®ç°çæ­£çå¤?Agent åä½æ¡æ¶

---

## ð åçº§è¿åº¦æ»è§

| é¡¹ç® | ä»»å¡ | ç¶æ?| è´è´£äº?| å®éå®æ |
|------|------|------|--------|----------|
| P26 | Parent-Child çå½å¨æç®¡ç | â?**å·²å®æ?* | arch-p27 | `cb52d4e` - ParentChildRegistry + 5 CLI |
| P27 | turn_complete äºä»¶é©±å¨ | â?**å·²å®æ?* | arch-p27 | éæå?lifecycle |
| P28 | å·¥å·æ³¨åå¢å¼º | â?**å·²å®æ?* | arch-p28 | `tools/registry.py` å·²ä¿®æ?|
| P29 | åä½å¢å¼º | â?**å·²å®æ?* | arch-p29 | `activity_feed.py` + `context_board.py` + `mentions.py` + `presence.py` |
| P30-P33 | å¤æ¨¡ææ¯æ?| â?**å·²å®æ?* | arch-p30-33 | `P30-P33-multimodal-support-design.md` |
| P34 | Dashboard çæ§é¢æ¿ | â?**å·²å®æ?* | arch-dashboard | `dashboard.py` (13KB) + `collector.py` + `renderer.py` |
| P35 | äºä»¶è¿½è¸ªç³»ç» | â?**å·²å®æ?* | arch-events | `tracker.py` (14KB) + `api.py` + `models.py` |
| P36 | å®æ¶ SSE æ¨é?| â?**å·²å®æ?* | arch-realtime | `index.html` (366KB) + 7 ä¸?JS æä»¶ |
| P37 | ç»ä»¶éææµè¯ | ð è¿è¡ä¸?| arch-integrator | å¾å¼å§?|

---

## â?å·²å®æåè½ï¼v0.4.0ï¼?

### æ ¸å¿æ¨¡å

| æ¨¡å | æä»¶ | åè½ |
|------|------|------|
| **MailboxManager** | `agentteam/team/mailbox.py` | Agent é´æ¶æ¯ä¼ éï¼Transport æ½è±¡ |
| **P2P Transport** | `agentteam/transport/p2p.py` | ZeroMQ PUSH/PULL + æä»¶åé |
| **RoleStore** | `agentteam/team/roles.py` | å¨æè§è²åéï¼developer/reviewer/tester/architect/coordinatorï¼?|
| **BaseTaskStore** | `agentteam/store/base.py` | ä»»å¡å­å¨æ½è±¡ï¼æä»¶éå¹¶åæ§å¶ |
| **WebSocketManager** | `agentteam/board/websocket.py` | WebSocket è¿æ¥ç®¡ç |
| **Board Server** | `agentteam/board/server.py` | HTTP API + SSE å®æ¶æ¨é?|
| **Transport æ½è±¡** | `agentteam/transport/base.py` | File/P2P/Redis/ClaimedMessage |
| **çå½å¨æç®¡ç** | `agentteam/team/lifecycle.py` | Agent çå½å¨æç¶ææº |
| **å®¡è®¡æ¥å¿** | `agentteam/audit/` | æä½å®¡è®¡è¿½æº¯ |
| **åè­¦ç³»ç»** | `agentteam/alerts/` | åçº§åè­¦æºå¶ |
| **è®°å¿ç³»ç»** | `agentteam/memory/` | åå±è®°å¿å­å¨ |
| **æè½å¼æ?* | `agentteam/skill/` | Skill èªå¨åå»ºåæ§è¡?|

### CLI å½ä»¤

```bash
# å¢éç®¡ç
agentteam team create <team>           # åå»ºå¢é
agentteam team status <team>           # å¢éç¶æ?
agentteam team members <team>          # ååºæå

# æ¶æ¯ä¼ é?
agentteam inbox send <team> <to> <msg> # åéæ¶æ?
agentteam inbox peek <team>           # æ¥çæ¶æ¯
agentteam inbox receive <team>        # æ¥æ¶æ¶æ¯

# ä»»å¡ç®¡ç
agentteam task create <team> <subject> # åå»ºä»»å¡
agentteam task list <team>            # ååºä»»å¡
agentteam task update <team> <id> --status completed  # æ´æ°ç¶æ?

# è§è²ç®¡ç
agentteam role assign <team> <agent> <role>  # åéè§è²

# Agent Spawn
agentteam spawn <backend> --team <team> --agent-name <name>  # çæ Agent

# çå½å¨æ
agentteam lifecycle on-exit --team <team> --agent <name>  # éåºæ¶æ¸ç
```

---

## ð è¿è¡ä¸­åè½ï¼v0.5.0ï¼?

### P26: Parent-Child çå½å¨æç®¡ç â?

**commit**: `cb52d4e feat(lifecycle): implement Parent-Child lifecycle management (P26)`

æ°å¢åè½ï¼?
- `ParentChildRegistry` - è¿½è¸ªç¶å­å³ç³»
- `parentToAgents: Map[parentSessionId, Set[agentId]]`
- `cleanupChildAgents(sessionId)` - çº§èç»æ­¢
- 5 ä¸ªæ° CLI å½ä»¤ï¼?
  - `terminate-children`
  - `terminate-tree`
  - `list-children`
  - `show-parent`
  - `register-child`
- `--parent` flag for spawn command

### P28: å·¥å·æ³¨åå¢å¼º ð

**ä¿®æ¹æä»¶**: `agentteam/tools/registry.py`

ç®æ ï¼?
- å¢å¼ºå·¥å·æ³¨åè¡?
- æ¯æå¨æå·¥å·åç?
- MCP å·¥å·éæ

### P29: åä½å¢å¼º ð

**æ°å¢ç®å½**: `agentteam/collaboration/`

ç®æ åè½ï¼?
- Activity Feedï¼æ´»å¨æµï¼?
- Presenceï¼å¨çº¿ç¶æï¼
- Mentionsï¼@æåï¼?
- Context Boardï¼ä¸ä¸æé¢æ¿ï¼?

### P30-P33: å¤æ¨¡ææ¯æ?ð

**ææ¡£**: `docs/superpowers/specs/P30-P33-multimodal-support-design.md`

ç®æ ï¼?
- é³é¢è¾å¥/è¾åº
- è§è§çè§£
- æä»¶å¤ç
- æªå¾/å±å¹æè·

### P34: Dashboard çæ§é¢æ¿ ð

**æ°å¢æä»¶**:
- `agentteam/api/monitor.py`
- `agentteam/board/dashboard.py`

ç®æ ï¼?
- å®æ¶ä¼è¯çæ§
- Token ä½¿ç¨ç»è®¡
- é£é©è¯ä¼°

### P35: äºä»¶è¿½è¸ªç³»ç» ð

**æ°å¢ç®å½**: `agentteam/events/`

ç®æ ï¼?
- 40+ äºä»¶ç±»å
- SQLite æä¹å?
- äºä»¶æ¥è¯¢ API

### P36: å®æ¶ SSE æ¨é?ð

**ä¿®æ¹æä»¶**:
- `agentteam/board/server.py`
- `agentteam/board/static/index.html`

ç®æ ï¼?
- Server-Sent Events
- å®æ¶æ¥å¿æ¨é?
- åç«¯ Dashboard éæ

---

## ð å¾å¼å§åè?

### P37: ç»ä»¶éææµè¯

**è´è´£äº?*: arch-integrator

ç®æ ï¼?
- éªè¯ P26-P36 åç»ä»¶è½ååå·¥ä½
- ç«¯å°ç«¯æµè¯?
- æ§è½åºåæµè¯

### æ°å¢åè½è§åï¼åºäº?SpectrAI Agent Teamsï¼?

| åè½ | æè¿° | ä¼åçº?|
|------|------|--------|
| **SharedTaskList DB** | SQLite æä¹åä»»å¡éåï¼æ¿ä»£ JSON æä»¶ï¼?| P1 |
| **TeamBus MCP å·¥å·** | team_message_role / team_broadcast ç­?5 ä¸?MCP å·¥å· | P1 |
| **å¢éæ°æ®åºè¡¨** | teams / roles / instances / members / tasks / messages 6 å¼ è¡¨ | P2 |
| **TaskKanban å¯è§å?* | çæ¿è§å¾å±ç¤ºä»»å¡æµè½¬ | P2 |
| **TeamMessageFlow** | å¯¹è¯æµå±ç¤ºæåéä¿¡ | P3 |

---

## ðï¸?æ¶æå?

```
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â?                   AgentTeam Framework                        â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â? CLI Layer                                                   â?
â? âââ team create/list/status                                 â?
â? âââ inbox send/peek/receive                                 â?
â? âââ task create/list/update                                â?
â? âââ role assign/list                                       â?
â? âââ lifecycle on-exit/terminate-children                   â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â? Core Layer                                                  â?
â? âââ MailboxManager (Transport abstraction)                   â?
â? â?  âââ FileTransport (default)                            â?
â? â?  âââ P2PTransport (ZeroMQ PUSH/PULL)                   â?
â? â?  âââ RedisTransport (optional)                          â?
â? âââ RoleStore (dynamic role assignment)                    â?
â? âââ BaseTaskStore (task storage)                          â?
â? âââ LifecycleManager (state machine)                       â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â? Agent Layer                                                 â?
â? âââ AgentManager (spawn/monitor/terminate)                 â?
â? âââ ParentChildRegistry (hierarchical lifecycle)            â?
â? âââ AgentRegistry (agent registration)                     â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â? Integration Layer                                           â?
â? âââ OpenClaw SDK Backend (sessions.create/send)            â?
â? âââ MCP Tools (team operations)                           â?
â? âââ WebSocket Manager (real-time updates)                  â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â? Storage Layer                                               â?
â? âââ SQLite Database (optional)                             â?
â? âââ File System (JSON tasks/messages)                     â?
â? âââ LanceDB (vector memory)                               â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
```

---

## ð ç¸å³ææ¡£

- [README.md](README.md) - é¡¹ç®æ¦è¿°
- [RELEASE_NOTES.md](RELEASE_NOTES.md) - åå¸è¯´æ
- [CHANGELOG.md](CHANGELOG.md) - åæ´æ¥å¿
- [AgentTeam_API.md](docs/AgentTeam_API.md) - API ææ¡£
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - æ¶æè®¾è®¡

---

## ð¤ è´¡ç®è?

- **arch-p27**: Parent-Child çå½å¨æç®¡ç
- **arch-p28**: å·¥å·æ³¨åå¢å¼º
- **arch-p29**: åä½å¢å¼º
- **arch-p30-33**: å¤æ¨¡ææ¯æ?
- **arch-dashboard**: Dashboard çæ§é¢æ¿
- **arch-events**: äºä»¶è¿½è¸ªç³»ç»
- **arch-realtime**: å®æ¶ SSE æ¨é?
- **arch-integrator**: ç»ä»¶éææµè¯

---

_Last updated: 2026-05-03_
