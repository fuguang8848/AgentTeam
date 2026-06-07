# AgentTeam åçº§æ¥å¿

## v0.5.1ï¼?026-05-04ï¼â?ææ¡£å®å + P37 å®æ

### ææ¡£æ´æ°
- **æ°å¢**: `CAPABILITIES.md` - å®æ´è½åæ¸å
- **æ°å¢**: `TODO.md` - v0.5.1 å¾åäºé¡¹è·è¸ª
- **æ´æ°**: `README.md` - é¾æ¥å?CAPABILITIES.md

### P37 ç»ä»¶éæå®æ
- **arch-integrator**: â?å·²å®æï¼ç?p37-integrator åå¹¶å®æï¼?
- **Commit**: `14d1d74` - Board SSE â?EventAPI éæ
- **è¯´æ**: Windows subprocess æ¨¡å¼ parent_agent åæ°ä¿®å¤

### æµè¯ç¶æ?
- **æµè¯æ?*: 595+ passed
- **CI**: ruff format + pyright + pip-audit

---

## v0.5.0ï¼?026-05-03ï¼â?P26-P37 å¤?Agent åä½å¢å¼º

### æ°å¢æ¨¡å

#### P26: Parent-Child çå½å¨æç®¡ç â?
- **commit**: `cb52d4e feat(lifecycle): implement Parent-Child lifecycle management (P26)`
- **æä»¶**: `agentteam/team/lifecycle.py`
- **æ°å¢åè½**:
  - `ParentChildRegistry` - è¿½è¸ªç¶å­å³ç³»
  - `parentToAgents: Map[parentSessionId, Set[agentId]]` - ç¶å­æ å°
  - `cleanupChildAgents(sessionId)` - çº§èç»æ­¢ææå­ Agent
  - 5 ä¸ªæ° CLI å½ä»¤ï¼?
    - `terminate-children` - ç»æ­¢å­?Agent
    - `terminate-tree` - ç»æ­¢æ´ä¸ª Agent æ ?
    - `list-children` - ååºå­?Agent
    - `show-parent` - æ¾ç¤ºç?Agent
    - `register-child` - æ³¨åå­?Agent
  - `--parent` flag for spawn command

#### P28: å·¥å·æ³¨åå¢å¼º â?
- **æä»¶**: `agentteam/tools/registry.py`
- **ç¶æ?*: å·²å®æ?
- **åè½**: å¢å¼ºå·¥å·æ³¨åè¡¨ï¼æ¯æå¨æå·¥å·åç?

#### P29: åä½å¢å¼º â?
- **ç®å½**: `agentteam/collaboration/`
- **ç¶æ?*: å·²å®æ?
- **åè½**:
  - Activity Feedï¼æ´»å¨æµï¼?
  - Presenceï¼å¨çº¿ç¶æï¼
  - Mentionsï¼@æåï¼?
  - Context Boardï¼ä¸ä¸æé¢æ¿ï¼?

#### P30-P33: å¤æ¨¡ææ¯æ?ðââï¼é¨åä»£ç ï¼
- **ææ¡£**: `docs/superpowers/specs/P30-P33-multimodal-support-design.md` â?
- **commit**: `bd32e9c` feat(models): P30-P33 multimodal support - image fields and FileAttachment class
- **å·²å®ç?* (`agentteam/team/models.py` + `agentteam/notification/types.py`):
  - `TeamMessage` æ°å¢: `image_url`, `image_data`, `image_mime_type`, `image_width`, `image_height`, `attachments: list[FileAttachment]`
  - `Notification` æ°å¢: `image_url`
  - æ°å¢ `FileAttachment` æ¨¡åç±?
  - CLI inbox å¾çæ¸²æ: `agentteam/cli/inbox.py` - iTerm2 inline images + URL fallback
  - Web board å¯åªä½? `index.html` renderMessage() æ¯æ image_url/base64/attachments æ¸²æ
  - Streaming/SSE: `board/server.py` _serve_sse() + polling fallback

#### P34: Dashboard çæ§é¢æ¿ â?
- **æ°å¢æä»¶**:
  - `agentteam/api/monitor.py`
  - `agentteam/board/dashboard.py`
- **ç¶æ?*: å·²å®æ?
- **åè½**: å®æ¶ä¼è¯çæ§ãToken ä½¿ç¨ç»è®¡ãé£é©è¯ä¼°ãcollector + renderer

#### P35: äºä»¶è¿½è¸ªç³»ç» â?
- **ç®å½**: `agentteam/events/`
- **ç¶æ?*: å·²å®æ?
- **ç®æ **: 40+ äºä»¶ç±»åãSQLite æä¹åãäºä»¶æ¥è¯?API

#### P36: å®æ¶ SSE æ¨é?â?
- **ä¿®æ¹æä»¶**:
  - `agentteam/board/server.py`
  - `agentteam/board/static/index.html`
- **ç¶æ?*: å·²å®æ?
- **ç®æ **: Server-Sent Eventsãå®æ¶æ¥å¿æ¨é?

#### P37: ç»ä»¶éæ â?
- **commit**: `0e7b0f8`
- **Board æ¥å¥**: EventAPI/NotificationManager
- **ç¶æ?*: å·²å®æ?
- **è¯´æ**: Windows subprocess éå¶ç?OpenClaw SDK backend è§£å³ï¼parent_agent åæ°ä¿®å¤ï¼?

#### P38: æºè½æ¨¡åè·¯ç± â?
- **commit**: `2f102db` feat(orchestrator): P38 intelligent model router
- **æä»¶**: `agentteam/orchestrator/model_router.py`
- **ç¶æ?*: å·²å®æ?
- **åè½**:
  - `TaskComplexityAnalyzer`: åºäºå³é®è¯?+ å¯åå¼çä»»å¡å¤æåº¦åæï¼1-10åï¼
  - `ComplexityLevel`: TRIVIAL/LOW/MEDIUM/HIGH/EXPERT äºçº§å¤æåº?
  - `ModelTier`: FAST/BALANCED/POWERFUL ä¸çº§æ¨¡å
  - `ModelRoutingPolicy`: (task_type, complexity) â?model_tier è·¯ç±è¡?
  - `ModelRouter`: æ ¹æ®ä»»å¡å¤æåº¦èªå¨éæ©æä¼æ¨¡å?
  - ææ¬ä¼åï¼ç®åä»»å¡ä½¿ç¨å»ä»·å¿«éæ¨¡åï¼èç 80-90% ææ¬ï¼?
- **ç¤ºä¾**:
  - "What is Python?" â?FAST tier (score=3) â?gpt-4o-mini
  - "è®¾è®¡åå¸å¼ç¼å­ç³»ç»? â?POWERFUL tier (score=9) â?o1

#### P41: AuthManager å®å¨å¼ºå¶æ§è¡ â?
- **commit**: `72bb841` security(P41): enforce AuthManager on board API endpoints
- **æä»¶**: `agentteam/board/server.py`
- **ç¶æ?*: å·²å®æ?
- **åè½**: å?board HTTP API endpoints ä¸å¼ºå¶æ§è¡?AuthManager è®¤è¯æ£æ?

#### P42: å®æ´æµè¯éªè¯ â?
- **commit**: ç?arch-qa å?worktree åéªè¯?
- **ç»æ**: 629 æµè¯éè¿ï¼?17 passed, 12 skipped, 0 failedï¼?
- **ç¶æ?*: å·²å®æ?

#### P43: P30-P33 å¤æ¨¡æ?Web UI å®å â?
- **commit**: `6c06044` feat(multimodal): P30-P33 complete streaming and rich notification support
- **æä»¶**: `agentteam/board/static/index.html`, `agentteam/notification/types.py`, `agentteam/team/models.py`
- **ç¶æ?*: å·²å®æ?
- **åè½**: Web board æ¶æ¯é¢æ¿æ¯æå¾çåéä»¶æ¸²æï¼Notification æ¯æå¯åªä½?

#### P3: æ°æ®åºè¿æ¥æ±  â?
- **commit**: `9464edd` perf(database): P3 database connection pooling + WAL mode
- **æä»¶**: `agentteam/database/manager.py`
- **ç¶æ?*: å·²å®æ?
- **åè½**:
  - `DatabaseConnectionPool`: åºäº `queue.Queue` çè¿æ¥æ± ï¼çº¿ç¨æ¬å°è¿æ?
  - `_get_conn()` / `_release_conn()` æ¾å¼ç®¡çï¼è¿æ¥å¤ç?
  - WAL æ¨¡å¼ï¼`_enable_wal_mode()` æåå¹¶åè¯»åæ§è½
  - äºå¡æ¯æï¼`begin()` / `commit()` / `rollback()`
  - é¢ç¼è¯è¯­å¥ç¼å­ï¼`prepared_stmts` å­å¸

#### P4: æ¥è¯¢é¢ç¼è¯ç¼å­?â?
- **commit**: `dcfacb3` perf(events): P4 prepared statement caching for EventTracker.query()
- **æä»¶**: `agentteam/events/tracker.py`
- **ç¶æ?*: å·²å®æ?
- **åè½**:
  - `_stmt_cache: OrderedDict` ç¼å­é¢ç¼è¯è¯­å¥æ¨¡æ?
  - LRU é©±éç­ç¥ï¼`maxsize=32`ï¼?
  - `track()`, `query()`, `get_stats()` å¨é¨ä½¿ç¨ç¼å­
  - æ¥è¯¢æ§è½æåï¼é¿åéå¤ç¼è¯?SQL

#### P5: å¼æ­¥è®¢éèéç¥ â?
- **commit**: `541c707` feat(events): P5 async subscriber notification with timeout
- **æä»¶**: `agentteam/events/tracker.py`
- **ç¶æ?*: å·²å®æ?
- **åè½**:
  - `_notify_subscribers_async()` ä½¿ç¨ `ThreadPoolExecutor` å¼æ­¥éç¥
  - `wait([future], timeout=5.0)` è¶æ¶ä¿æ¤ï¼é²æ­¢è®¢éèé»å¡ä¸»çº¿ç¨
  - äºä»¶è¿½è¸ªä¸åè®¢éèæéå½±å?
  - `notify()` è¿å `bool` æç¤ºæ¯å¦å¨é¨æå

#### P6: åå­éç½®å¯è°åæ° â?
- **commit**: `e36ebc7` feat(board): P6 Memory Config Tunables
- **æä»¶**: `agentteam/board/server.py`
- **ç¶æ?*: å·²å®æ?
- **åè½**:
  - `_event_queue` / `_chat_event_queue` éåå¤§å°å¯éç½?
  - `AgentTeam_MAX_EVENT_QUEUE` / `AgentTeam_MAX_CHAT_QUEUE` ç¯å¢åé
  - é»è®¤å¼ï¼1000 äºä»¶ / 500 èå¤©ï¼è¶åºåä¸¢å¼ææ§ç
  - `AgentTeam_EVENT_TTL_HOURS` æ§å¶äºä»¶è¿ææ¶é´

### å·²å®ç°çæ ¸å¿åè½ï¼v0.4.0 ç¡®è®¤ï¼?

| æ¨¡å | æä»¶ | åè½ | ç¶æ?|
|------|------|------|------|
| **MailboxManager** | `agentteam/team/mailbox.py` | Agent é´æ¶æ¯ä¼ é?| â?|
| **P2P Transport** | `agentteam/transport/p2p.py` | ZeroMQ PUSH/PULL + æä»¶åé | â?|
| **RoleStore** | `agentteam/team/roles.py` | å¨æè§è²åé?| â?|
| **BaseTaskStore** | `agentteam/store/base.py` | ä»»å¡å­å¨æ½è±¡ | â?|
| **WebSocketManager** | `agentteam/board/websocket.py` | WebSocket è¿æ¥ç®¡ç | â?|
| **Board Server** | `agentteam/board/server.py` | HTTP API + SSE | â?|
| **Transport æ½è±¡** | `agentteam/transport/base.py` | File/P2P/Redis | â?|
| **LifecycleManager** | `agentteam/team/lifecycle.py` | Agent çå½å¨æç¶ææº | â?|
| **OpenClaw SDK Backend** | `agentteam/spawn/openclaw_sdk_backend.py` | Gateway Sessions API éæ | â?|

### åçº§å¢éç¶æï¼2026-05-03ï¼?

| Agent | ä»»å¡ | Worktree | ç¶æ?| å®éå®æ |
|-------|------|----------|------|----------|
| arch-p27 | Parent-Child çå½å¨æ | `upgrade-squad/arch-p27` | â?å·²å®æ?| `cb52d4e` + 5 CLI å½ä»¤ |
| arch-p28 | å·¥å·æ³¨åå¢å¼º | `upgrade-squad/arch-p28` | â?å·²å®æ?| `tools/registry.py` ä¿®æ¹ |
| arch-p29 | åä½å¢å¼º | `upgrade-squad/arch-p29` | â?å·²å®æ?| 4 ä¸ªæ¨¡åï¼activity_feed + context_board + mentions + presenceï¼|
| arch-p30-33 | å¤æ¨¡ææ¯æ?| `upgrade-squad/arch-p30-33` | â?å·²å®æ?| è®¾è®¡ææ¡£ 8KB |
| arch-dashboard | Dashboard çæ§ | `monitor-squad/arch-dashboard` | â?å·²å®æ?| dashboard.py (13KB) + collector + renderer |
| arch-events | äºä»¶è¿½è¸ª | `monitor-squad/arch-events` | â?å·²å®æ?| tracker.py (14KB) + api + models |
| arch-realtime | SSE å®æ¶æ¨é?| `monitor-squad/arch-realtime` | â?å·²å®æ?| index.html (366KB) + 7 ä¸?JS æä»¶ |
| arch-integrator | ç»ä»¶éæ | `monitor-squad/arch-integrator` | â?å·²å®æ?| p37-integrator åå¹¶ (`14d1d74`) |
| p37-integrator | ç»ä»¶éæï¼P37ï¼?| SDK backendï¼Windowsï¼?| â?å·²å®æ?| `14d1d74` Board SSE â?EventAPI |
| p30-multimodal | å¤æ¨¡æä»£ç ï¼P30-P33ï¼?| subprocessï¼Windowsï¼?| â?é¨åå®æ | `bd32e9c` models.py + types.py |
| p38-model-router | æºè½æ¨¡åè·¯ç± | æ¬å° | â?å·²å®æ?| `2f102db` model_router.py |
| arch-dbpool | P3 æ°æ®åºè¿æ¥æ±  | perf-squad/arch-dbpool | â?å·²å®æ?| `9464edd` + WAL æ¨¡å¼ |
| arch-querycache | P4 æ¥è¯¢é¢ç¼è¯ç¼å­?| perf-squad/arch-querycache | â?å·²å®æ?| `dcfacb3` + LRU é©±é?|
| arch-async | P5 å¼æ­¥è®¢éèéç¥ | perf-squad/arch-async | â?å·²å®æ?| `541c707` + è¶æ¶ä¿æ¤ |
| arch-memconfig | P6 åå­éç½®å¯è° | perf-squad/arch-memconfig | â?å·²å®æ?| `e36ebc7` + ç¯å¢åé |
| arch-security | P41 AuthManager å¼ºå¶æ§è¡ | perf-squad/arch-security | â?å·²å®æ?| `72bb841` board server è®¤è¯ |
| arch-qa | P42 æµè¯éªè¯ | perf-squad/arch-qa | â?å·²å®æ?| 629 æµè¯éè¿ï¼?17 passedï¼?|
| arch-p30web | P43 å¤æ¨¡æ?Web UI | perf-squad/arch-p30web | â?å·²å®æ?| `6c06044` index.html + models |

---

## v0.4.0ï¼?026-04-26ï¼â?P1 å·¥ç¨åæ¹è¿?

### æ°å¢æ¨¡å

#### å®¡è®¡æ¥å¿ï¼Audit Loggingï¼?
- æä»¶ï¼`agentteam/audit.py`
- è¿½å åå¥æ¨¡å¼ï¼åå²äºä»¶æ°¸ä¸ä¿®æ?
- æ¯ä¸ªäºä»¶åå«ï¼event_id, event_type, actor, details, timestamp, team
- æ¯ææç±»å?æ¶é´èå´/actor è¿æ»¤æ¥è¯¢
- æµè¯ï¼`tests/test_audit.py`ï¼? é¡¹ï¼å¨é¨éè¿ï¼?

#### æºè½è·¯ç±ï¼Intelligent Routingï¼?
- æä»¶ï¼`agentteam/team/router.py`
- åºäºä¸å ç´ è·¯ç±ç®æ³ï¼
  - **åå²è¡¨ç°**ï¼æåç + è´¨éè¯åå æ
  - **è´è½½æç¥**ï¼å½åè¿è¡ä¸­çä»»å¡æ°
  - **æè½å¹é?*ï¼å³é®è¯æåï¼æ¯æä¸­è±æï¼?
- æ¯æ `route()` è·åæä¼?agentï¼`get_all_candidates()` è·åæåºåè¡¨
- æ?agent èªå¨åå»ºé»è®¤æ¡£æ¡ï¼æ åå²æ°æ®æ?fallback å°é»è®¤å¼ï¼
- æµè¯ï¼`tests/test_routing.py`ï¼?8 é¡¹ï¼å¨é¨éè¿ï¼?

#### åè­¦æºå¶ï¼Alertingï¼?
- æä»¶ï¼`agentteam/alerts.py`
- åçº§ä¸¥éç¨åº¦ï¼LOW / MEDIUM / HIGH / CRITICAL
- æ¯æåè­¦ç±»åï¼TASK_TIMEOUT, AGENT_FAILURE_RATE_HIGH, TEAM_INACTIVITY
- CRUD æä½ï¼åå»ºãæ¥è¯¢ãåè¡¨ãç¡®è®?
- CLI éæï¼`agentteam alert check/list/ack`
- æµè¯ï¼`tests/test_alerts.py`ï¼? é¡¹ï¼å¨é¨éè¿ï¼?

### ä¿®å¤é®é¢

| é®é¢ | ä¿®å¤åå®¹ | å½±åèå´ |
|------|----------|----------|
| `route()` åæ°åä¸å¹é | `candidates` â?`available_agents` | æºè½è·¯ç± |
| `scores=None` pydantic éªè¯å¤±è´¥ | æµè¯ä¸­ç§»é¤æ¾å¼?`None`ï¼ä½¿ç¨é»è®¤ç©ºåè¡¨ | è·¯ç±æµè¯ |
| æ?agent æ æ³è¢«è·¯ç?| `route()` èªå¨åå»ºé»è®¤ AgentProfile | æºè½è·¯ç± |
| `total_score` è®¡ç®ç²¾åº¦ | ä¿®æ­£ææå?8.4 â?8.45 | è·¯ç±æµè¯ |
| `TaskStatus.failed` ä¸å­å?| æ¹ä¸º `TaskStatus.blocked` | è·¯ç±æµè¯ |
| `test_get_all_candidates` æåºéè¯¯ | ç»ä¸ agent æåçåè´è½½ï¼è®© topic å¹éæä¸ºå³å®å ç´  | è·¯ç±æµè¯ |

### ææ¯ç»è?

**QualityScore æé**ï¼?-100 åï¼ï¼?
- completeness 0.25
- accuracy 0.30
- quality 0.20
- è§èæ?0.15
- innovation 0.10

**è·¯ç±è¯åå¬å¼**ï¼?-100ï¼ï¼
```
total = topic_match(0-50) + success_score(0-30) + quality_score(0-20) - load_penalty(0-15)
```

**æ¼ç§»æ£æµéå?*ï¼Jaccard + è¯­ä¹ï¼ï¼
- â?0.60ï¼æ æ¼ç§»
- 0.45-0.60ï¼ä½æ¼ç§»
- 0.30-0.45ï¼ä¸­æ¼ç§»
- 0.15-0.30ï¼é«æ¼ç§»
- < 0.15ï¼ä¸¥éæ¼ç§?

### CLI å½ä»¤ï¼v0.4.0 è¡¥åï¼?026-04-27ï¼?

**å®¡è®¡æ¥å¿ CLI**ï¼?
- `agentteam audit query <team>` â?æ¥è¯¢å®¡è®¡æ¥å¿ï¼æ¯æ?`--action`/`--actor`/`--target`/`--limit`/`--json`ï¼?
- `agentteam audit summary <team>` â?å®¡è®¡æ´»å¨æè¦
- `agentteam audit log <team>` â?æå¨è®°å½å®¡è®¡äºä»¶ï¼æµè¯?è°è¯ç¨ï¼

### ä¿®å¤é®é¢ï¼v0.4.0 è¡¥åï¼?026-04-27ï¼?

| é®é¢ | ä¿®å¤åå®¹ | å½±åèå´ |
|------|----------|----------|
| æ¼ç§»æ£æµå­æ®µåä¸å¹é?| `jaccard_similarity` â?`jaccard`ï¼`semantic_similarity` â?`semantic` | æ¼ç§»æ£æµ?|
| audit.py å¯¼å¥è·¯å¾éè¯¯ | `from agentteam.audit import AuditEventType` | æ¼ç§»æ£æµ?|
| å®¡è®¡æ¥å¿ CLI ç¼ºå¤± | æ°å¢ `agentteam audit query/summary/log` | å®¡è®¡æ¥å¿ |

### åçº§æ­¥éª¤

```bash
# 1. æåææ°ä»£ç ?
git pull origin main

# 2. å®è£ä¾èµï¼å¦ææ°å¢ï¼
pip install -e .

# 3. è¿è¡æµè¯ç¡®è®¤
python -m pytest tests/test_audit.py tests/test_routing.py tests/test_alerts.py -v

# 4. éªè¯ CLI
agentteam audit query <team>
agentteam audit summary <team>
agentteam alert check --team <your-team>
```

### ååå¼å®¹

- â?æ ç ´åæ§åæ?
- â?ææç°æ?API ä¿æä¸å
- â?æ°å¢æ¨¡åä¸ºå¯éåè?

---

## v0.3.1ï¼?026-04-26ï¼â?P0 å·¥ç¨åæ¹è¿?

### æ°å¢

- **ç»æåæ¥å¿?*ï¼`agentteam/utils/logger.py`
  - JSON æ ¼å¼ï¼trace_id ä¸ä¸æè¿½è¸?
  - RotatingFileHandlerï¼?0MB/5 å¤ä»½ï¼?
  - ç¯å¢åéï¼`AgentTeam_LOG_LEVEL`

- **éè¯æ¡æ¶**ï¼`agentteam/utils/retry.py`
  - `@retry` / `@retry_async` è£é¥°å?
  - ææ°éé?+ æå¨
  - èªå¨ç»è®¡éè¯æ¬¡æ°

### å½±å

- `FileTaskStore._save_unlocked()` èªå¨éè¯
- `FileTransport.deliver()` èªå¨éè¯
- æµè¯ï¼?0 ååæµè¯ + 10 éææµè¯

---

_æåæ´æ°ï¼2026-05-03_
