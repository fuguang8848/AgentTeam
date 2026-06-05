# AgentTeam-OpenClaw Architecture Review



> **Review Date**: 2026-05-04  

> **Reviewer**: architect (æ¶æå®¡æ¥)  

> **Version Reviewed**: v0.5.1  



---



## ð Executive Summary



AgentTeam-OpenClaw æ¯ä¸ä¸ªç»æè¯å¥½çå¤æºè½ä½åä½æ¡æ¶ï¼éç¨æ¨¡ååæ¶æè®¾è®¡ãä»£ç ç»ç»æ¸æ°ï¼æ ¸å¿ç»ä»¶èè´£æç¡®ãæ»ä½è¯ä¼°ï¼?*ä¼ç§ (A-)**



**ä¼ç¹**:

- æ¨¡ååè®¾è®¡ï¼èè´£æ¸æ°

- Repository æ¨¡å¼å®ç°è¯å¥½

- äºä»¶é©±å¨æ¶æå®æ´

- å¤ç§ Spawn Backend æä¾çµæ´»æ?
- æºè½æ¨¡åè·¯ç± (P38) è®¾è®¡åç



**éè¦æ¹è¿?*:

- å¨å±åä¾æ¨¡å¼å½±åæµè¯æ?
- Board Server ä»£ç è¿äºåºå¤§

- é¨åæ¨¡åå­å¨å¾ªç¯ä¾èµé£é©

- éç½®ç¡¬ç¼ç é®é¢?


---



## ðï¸?æ¶ææ¦è§



```

âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â?                     CLI Layer                              â?
â?  (agentteam/team/, agentteam/cli/, agentteam/spawn/)        â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
                              â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â?                   Core SDK Layer                           â?
â?  (CTTeam, CTAgent, CTTask, CTMessage - core.py)           â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
                              â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â?                 Orchestration Layer                        â?
â?  (orchestrator/, spawn/, session/, events/)               â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
                              â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â?                   Storage Layer                            â?
â?  (database/, store/, memory/, transport/)                  â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
                              â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â?                   Board UI Layer                           â?
â?  (board/server.py, board/static/, api/)                    â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
```



---



## â?ä¼ç¹åæ



### 1. æ¨¡ååæ¶æ?(è¯å: 9/10)



**ä¼ç¹**:

- æ¸æ°çæ¨¡ååå?(team, events, spawn, board, database ç­?

- æ¯ä¸ªæ¨¡åææç¡®çèè´£

- æ¨¡åé´éè¿æ¥å£éä¿¡



**ç¤ºä¾**:

```

agentteam/

âââ team/           # å¢éçå½å¨æç®¡ç

âââ events/         # äºä»¶è¿½è¸ª

âââ spawn/          # Agent çæ

âââ orchestrator/   # ä»»å¡ç¼æ

âââ database/       # æ°æ®åºå±

âââ board/          # Web UI

âââ ...

```



### 2. Repository æ¨¡å¼ (è¯å: 8/10)



**å®ç°**:

```python

# database/repositories/base.py

class BaseRepository(ABC):

    @abstractmethod

    def create(self, entity): ...

    @abstractmethod

    def get(self, id): ...

    @abstractmethod

    def update(self, id, updates): ...

    @abstractmethod

    def delete(self, id): ...

```



**ä¼ç¹**:

- æ°æ®è®¿é®é»è¾éä¸­

- ä¾¿äºååæµè¯ (å¯æ³¨å?mock)

- æ¸æ°ç?CRUD æ¥å£



**é®é¢**:

- é¨å Repository ä½¿ç¨ `list()` è¿åææè®°å½ï¼æ åé¡?
- å»ºè®®: å¯¹å¤§æ°æ®éè¡¨æ·»å  `limit/offset` æ¯æ



### 3. äºä»¶é©±å¨æ¶æ (è¯å: 8/10)



**EventTracker è®¾è®¡**:

```python

# å¨å±è®¢éèæ¨¡å¼?
_event_subscribers: list[Callable] = []



def track(self, event: AgentTeamEvent):

    # å­å¨å?SQLite

    conn.execute("INSERT INTO events ...", ...)

    # éç¥è®¢éè?
    _notify_event_subscribers(event)

```



**ä¼ç¹**:

- å¼æ­¥è®¢ééç¥ (ThreadPoolExecutor + 5s è¶æ¶ä¿æ¤)

- æ¯ææ¹éäºä»¶è·è¸ª

- æ¥è¯¢ API ä¸°å¯



**é®é¢**:

- å¨å±åä¾ `_tracker` ä¸å©äºæµè¯?
- å»ºè®®: ä½¿ç¨ä¾èµæ³¨å¥



### 4. æ°æ®åºè¿æ¥æ±  (è¯å: 9/10)



**P3 ä¼åå®ç°**:

```python

class DatabaseConnectionPool:

    pool_size: int = 5

    

    def _get_conn(self) -> sqlite3.Connection:

        conn = self._conn_queue.get()

        if conn is None:

            conn = sqlite3.connect(...)

        return conn

    

    def _release_conn(self, conn):

        self._conn_queue.put(conn)

```



**ä¼ç¹**:

- åºäº `queue.Queue` çè¿æ¥å¤ç?
- WAL æ¨¡å¼æåå¹¶åæ§è½

- é¢ç¼è¯è¯­å¥ç¼å­?(LRU 32æ?



### 5. æºè½æ¨¡åè·¯ç± (è¯å: 8/10)



**P38 ModelRouter è®¾è®¡**:

```python

class ModelRouter:

    def route_task(self, task_description: str, 

                   task_type: TaskType, ...) -> RoutingDecision:

        # 1. åæä»»å¡å¤æåº?
        complexity, score = self.complexity_analyzer.analyze(...)

        # 2. è·åæ¨èæ¨¡åå±?
        tier = self.routing_policy.get_model_tier(task_type, complexity)

        # 3. éæ©å·ä½æ¨¡å

        model = self._select_model_for_tier(tier, task_type)

```



**ä¼ç¹**:

- åºäºå³é®è¯?+ å¯åå¼çå¤æåº¦åæ?
- ä»»å¡ç±»å â?æ¨¡åå±è·¯ç±è¡¨

- ææ¬ä¼å (~80-90% èç)



**é®é¢**:

- æ¨¡ååè¡¨ç¡¬ç¼ç ?
- å»ºè®®: éç½®æä»¶å¤é¨å?


### 6. Spawn Backend æ¶æ (è¯å: 9/10)



**6 ç§?Backend**:

| Backend | éç¨åºæ¯ |

|---------|----------|

| tmux | Linux/macOS é»è®¤ |

| subprocess | éç¨å­è¿ç¨?|

| openclaw_sdk | OpenClaw Gateway API |

| openclaw_api | OpenClaw REST API |

| terminal_buffer | ç»ç«¯ç¼å² |

| auto | èªå¨æ£æµ?|



**ä¼ç¹**:

- ç­ç¥æ¨¡å¼å®ç°

- ç»ä¸çæ½è±¡æ¥å?
- ä¾¿äºæ©å±æ?Backend



---



## â ï¸ éè¦æ¹è¿çé®é¢



### é®é¢ 1: å¨å±åä¾æ¨¡å¼ (ä¸¥éåº? ä¸?



**ä½ç½®**: 

- `agentteam/events/tracker.py` - `_tracker: Optional[EventTracker] = None`

- `agentteam/core.py` - `get_team = lambda name: CTTeam(name)`



**é®é¢**:

- å¨å±ç¶æé¾ä»¥æµè¯?
- è·¨æµè¯å¯è½æ±¡æ?
- åä¾åå§åé¡ºåºä¸ç¡®å®



**å»ºè®®**:

```python

# ä½¿ç¨ä¾èµæ³¨å¥

class EventTracker:

    def __init__(self, db_path: Optional[str] = None):

        self._conn: Optional[sqlite3.Connection] = None

        # éå¨å±åä¾



# æµè¯æ¶æ³¨å?mock

def test_something():

    mock_tracker = MockEventTracker()

    service = MyService(tracker=mock_tracker)

```



### é®é¢ 2: Board Server è¿äºåºå¤§ (ä¸¥éåº? ä¸?



**ä½ç½®**: `agentteam/board/server.py` (900+ è¡?



**é®é¢**:

- åæä»¶è¶è¿?900 è¡?
- æ··åäº?HTTP Handlerãä¸å¡é»è¾ãéææä»¶æå?
- ç»´æ¤å°é¾



**å»ºè®®**:

```

board/

âââ server.py           # ä¸»æå¡å¨

âââ handlers/           # è¯·æ±å¤çå?
â?  âââ __init__.py

â?  âââ team_handler.py

â?  âââ task_handler.py

â?  âââ session_handler.py

â?  âââ events_handler.py

âââ static/             # éæèµæº?
âââ templates/         # HTML æ¨¡æ¿

```



### é®é¢ 3: éç½®ç¡¬ç¼ç ?(ä¸¥éåº? ä½?



**ä½ç½®**:

- `orchestrator/model_router.py` - `MODEL_TIERS` ç¡¬ç¼ç ?
- `database/manager.py` - `pool_size: int = 5`



**å»ºè®®**:

```python

# ä»éç½®æä»¶è¯»å?
MODEL_TIERS = json.load(open("config/model_tiers.json"))



# æç¯å¢åé?
pool_size = int(os.environ.get("AgentTeam_DB_POOL_SIZE", "5"))

```



### é®é¢ 4: å¾ªç¯ä¾èµé£é© (ä¸¥éåº? ä¸?



**ä½ç½®**:

- `agentteam/parser/integration.py` â?`from agentteam.parser import ActivityEvent`

- `agentteam/core.py` å¯¼å¥ `agentteam.spawn`



**å»ºè®®**:

```python

# ä½¿ç¨ TYPE_CHECKING é¿åè¿è¡æ¶å¾ªç¯å¯¼å?
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    from agentteam.parser import ActivityEvent

else:

    ActivityEvent = object  # è¿è¡æ?mock

```



### é®é¢ 5: éè¯¯å¤çä¸ä¸è?(ä¸¥éåº? ä½?



**ä½ç½®**: å¤ä¸ªæ¨¡å



**ç¤ºä¾**:

```python

# æçå°æ¹è¿å None

def get(self, id) -> Optional[Entity]:

    return None



# æçå°æ¹æåºå¼å¸¸

def get(self, id):

    raise ValueError(f"Entity {id} not found")

```



**å»ºè®®**: ç»ä¸éè¯¯å¤çç­ç¥ï¼å»ºè®®ä½¿ç¨èªå®ä¹å¼å¸¸ç±?


---



## ð æ¶æè¯å



| ç»´åº¦ | è¯å | è¯´æ |

|------|------|------|

| æ¨¡åå?| 9/10 | æ¸æ°çæ¨¡ååå?|

| å¯æµè¯æ?| 6/10 | å¨å±åä¾å½±åæµè¯ |

| æ§è½ | 8/10 | è¿æ¥æ±?+ ç¼å­ä¼å |

| å¯æ©å±æ?| 8/10 | å¤?Backend è®¾è®¡è¯å¥½ |

| ä»£ç è´¨é | 7/10 | é¨åä»£ç è¿äºéä¸­ |

| **æ»ä½** | **A-** | **ä¼ç§** |



---



## ð¯ æ¹è¿å»ºè®®ä¼åçº?


### P0 (立即修复)

1. **Board Server 拆分** → 保持单文件，已添加结构化 docstring（server.py BoardHandler 类注释）；物理拆分风险高，3104 行但职责已按 resource 分组路由表
2. **全局状态消除** → core.py 的 `create_team`/`get_team` lambda 已改为具名函数；EventTracker 的 `set_tracker`/`reset_tracker` 已导出到 `events/__init__.py`，支持依赖注入

### P1 (近期改进)

3. **配置外部化** → `config.py` 的 `pool_size` 支持 `AGENTTEAM_DB_POOL_SIZE`；`model_router.py` 的 `MODEL_TIERS` 支持 `AGENTTEAM_MODEL_TIERS_JSON` / `AGENTTEAM_MODEL_TIERS_FILE`
4. **循环依赖修复** → `parser/integration.py` 和 `core.py` 已加 `TYPE_CHECKING` guard
5. **错误处理统一** → 新增 `exceptions.py`，定义了完整异常类体系，已替换 `core.py`、`team/manager.py`、`tools/registry.py` 中的 `ValueError`

### P2 (长期规划)

6. **数据库迁移系统** → 使用 migrations 文件夹
7. **监控指标标准化** → 统一 metrics 接口
8. **插件系统完善** → 支持动态加载


---



## ð éå½



### A. æ ¸å¿æä»¶æ¸å



| æä»¶ | è¡æ° | èè´£ |

|------|------|------|

| core.py | 350+ | CTTeam/CTAgent/CTTask æ ¸å¿æ¨¡å |
| server.py | 3104 | Board HTTP Server |
| server.py | 900+ | Board HTTP Server |

| manager.py | 300+ | DatabaseManager |

| tracker.py | 400+ | EventTracker |

| model_router.py | 400+ | æºè½æ¨¡åè·¯ç± |



### B. ä¾èµå³ç³»å?


```

CLI

  âââ core.py (CTTeam)

        âââ team/

        â?    âââ lifecycle.py

        â?    âââ mailbox.py

        â?    âââ roles.py

        âââ spawn/

        â?    âââ base.py

        â?    âââ [6 backends]

        âââ events/

              âââ tracker.py



Board Server

  âââ board/server.py

  âââ board/websocket.py

  âââ api/

```



---



*æ¬æ¶æå®¡æ¥æ¥åç± architect agent çæ*

*æåæ´æ? 2026-05-04*

