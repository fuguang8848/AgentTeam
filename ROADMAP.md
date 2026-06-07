# AgentTeam Evolution Roadmap

## ç°ç¶ (v0.2)

```
åç¨æ?â?åæº â?æä»¶ç³»ç» â?CLI é©±å¨
```

- æææ°æ®å¨ `~/.agentteam/`ï¼å¢ééç½®ãä»»å¡ãæ¶æ¯ï¼
- ææ?agent å¿é¡»å¨åä¸å°æºå?
- çº¯æä»?I/Oï¼é¶ä¾èµ

---

## Phase 1: Transport æ½è±¡å±?(v0.3)

**ç®æ **: è®©æ¶æ¯éä¿¡å±å¯ææï¼ä¸æ¹ä¸å±æ¥å£ã?

**æ¶æåå**:
```
ç°å¨:
  MailboxManager â?ç´æ¥è¯»åæä»¶

Phase 1:
  MailboxManager â?Transport(æ¥å£)
                   âââ FileTransport (é»è®¤ï¼å½åè¡ä¸?
                   âââ (æªæ¥: RedisTransport, ...)
```

**å·ä½ä»»å¡**:

| ä»»å¡ | æè¿° | å»ºè®® |
|------|------|------|
| å®ä¹ Transport æ¥å£ | `send()`, `receive()`, `peek()`, `peek_count()`, `broadcast()` | äººå A |
| éæ FileTransport | æ?`mailbox.py` å½åçæä»¶æä½æ½æ?`FileTransport` ç±?| äººå A |
| éæ MailboxManager | éè¿ `AgentTeam_TRANSPORT=file` éæ© backend | äººå A |
| TaskStore æ½è±¡ | åæ ·æ½åº `FileTaskStore`ï¼é¢çæ¥å?| äººå B |
| æµè¯ | ç¡®ä¿éæåè¡ä¸ºä¸å?| äººå B |

**äº¤ä»ç?*:
```
agentteam/transport/
âââ __init__.py
âââ base.py           # Transport æ½è±¡åºç±»
âââ file.py           # FileTransport (å½åè¡ä¸º)

agentteam/store/
âââ __init__.py
âââ base.py           # TaskStore æ½è±¡åºç±»
âââ file.py           # FileTaskStore (å½åè¡ä¸º)
```

**éªæ¶**: ææç°æå½ä»¤è¡ä¸ºä¸åï¼`AgentTeam_TRANSPORT=file` ä¸ºé»è®¤å¼ã?

---

## Phase 2: Redis Transport (v0.4)

**ç®æ **: æ¯æè·¨æºå¨æ¶æ¯éä¿¡ã?

**æ¶æåå**:
```
æºå¨A (leader) âââ RedisTransport âââ?
                                    âââ Redis Server
æºå¨B (worker) âââ RedisTransport âââ?

å¢ééç½® / ä»»å¡ â?ä»ç¶ç¨æä»¶ï¼æå±äº«æä»¶ç³»ç»ï¼
æ¶æ¯éä¿¡ â?Redis (é«é¢ï¼å®æ?
```

**å·ä½ä»»å¡**:

| ä»»å¡ | æè¿° | å»ºè®® |
|------|------|------|
| RedisTransport å®ç° | `LPUSH`/`RPOP` å®ç° send/receive | äººå A |
| è¿æ¥ç®¡ç | URL éç½®ãè¿æ¥æ± ãæ­çº¿éè¿?| äººå A |
| éç½®æ¹å¼ | `AgentTeam_TRANSPORT=redis` + `AgentTeam_REDIS_URL=redis://...` | äººå B |
| broadcast å®ç° | éè¦ç¥éå¢éæååè¡?â?ä¾èµ TeamManager | äººå B |
| æ··åæ¨¡å¼ | æ¶æ¯èµ?Redisï¼éç½?ä»»å¡èµ°æä»?| äººå B |
| éææµè¯ | ä¸¤å°æºå¨ï¼æä¸¤ä¸ª containerï¼å®éè·é?| ä¸èµ?|

**æ°å¢ä¾èµ**: `redis` (pypi)ï¼å¯éå®è£?`pip install agentteam[redis]`

**éªæ¶**:
```bash
# æºå¨ A
export AgentTeam_TRANSPORT=redis
export AgentTeam_REDIS_URL=redis://192.168.1.100:6379
agentteam team spawn-team dev-team -n leader
agentteam spawn tmux claude --team dev-team -n worker1 --task "..."

# æºå¨ B
export AgentTeam_TRANSPORT=redis
export AgentTeam_REDIS_URL=redis://192.168.1.100:6379
agentteam inbox receive dev-team --agent worker1
# => æ¶å°æ¶æ¯ â?
```

---

## Phase 3: å±äº«ç¶æå± (v0.5)

**ç®æ **: å¢ééç½®åä»»å¡ä¹è½è·¨æºå¨å±äº«ã?

Phase 2 åªè§£å³äºæ¶æ¯è·¨æºå¨ï¼ä½å¢ééç½®ï¼`config.json`ï¼åä»»å¡ï¼`task-*.json`ï¼è¿å¨æ¬å°æä»¶ã?

**ä¸¤ç§è·¯çº¿ï¼éä¸ä¸ªï¼**:

### è·¯çº¿ A: NFS / å±äº«æä»¶ç³»ç»

```bash
# æææºå¨æè½½åä¸ä¸?NFS
export AgentTeam_DATA_DIR=/mnt/shared/AgentTeam
# é¶ä»£ç æ¹å¨ï¼ç´æ¥å¯ç¨
```

æç®åï¼ä½ä¾èµç½ç»æä»¶ç³»ç»åºç¡è®¾æ½ã?

### è·¯çº¿ B: Redis ç»ä¸å­å¨

```
æ¶æ¯ â?Redis (Phase 2 å·²å)
éç½® â?Redis Hash
ä»»å¡ â?Redis Hash

ææç¶æé½å?Redisï¼æä»¶ç³»ç»åªåæ¬å°ç¼å­?
```

**å·ä½ä»»å¡ (è·¯çº¿ B)**:

| ä»»å¡ | æè¿° | å»ºè®® |
|------|------|------|
| RedisTeamStore | å¢ééç½®å­?Redis Hash | äººå A |
| RedisTaskStore | ä»»å¡å­?Redis Hash | äººå B |
| æ°æ®è¿ç§»å·¥å· | `agentteam migrate file-to-redis` | ä¸èµ?|
| ç»ä¸éç½® | `AgentTeam_BACKEND=redis` ä¸ä¸ªåéæå®ææ?| ä¸èµ?|

**éªæ¶**: ä¸¤å°æºå¨å±äº«åä¸ä¸ªå¢éãåä¸ä¸ªä»»å¡æ¿ãåä¸ä¸ªæ¶æ¯éåã?

---

## Phase 4: å¤ç¨æ·åä½?(v0.6)

**ç®æ **: ä¸åäººç agent ç»æä¸ä¸ªå¢éã?

**æ°å¢è½å**:

| è½å | æè¿° |
|------|------|
| ç¨æ·èº«ä»½ | åºå"è°ç agent"ï¼ä¸åªæ¯ agent nameï¼?|
| æéæ¨¡å | è°è½åå»ºå¢éãè°è½å å¥ãè°è½çä»»å¡ |
| å½åç©ºé´ | `user1/worker1` vs `user2/worker1` |
| Token è®¤è¯ | è¿æ¥ Redis æ¶éªè¯èº«ä»?|

```
ç¨æ· A ç?Claude Code âââ?
                        âââ Redis ââ Team: project-x
ç¨æ· B ç?Claude Code âââ?

ç¨æ· A ç?agent åç¨æ?B ç?agent å¨åä¸ä¸ªå¢ééåä½
```

---

## Phase 5: Web UI (v1.0)

**ç®æ **: æµè§å¨çæ¿ï¼æ¿ä»£ç»ç«¯ Rich æ¸²æã?

```
agentteam board serve --port 8080
```

- å®æ¶çæ¿ï¼WebSocket æ¨éï¼
- å¤å¢éæ¦è§?
- ä»»å¡ææ½
- æ¶æ¯åå²

---

## æ»è§

```
v0.2         â?åæºæä»¶ç³»ç»ï¼è½ç?
v0.3 (ç°å¨)  â?Config ç³»ç» + å¤ç¨æ·åä½?+ Web UI (å·²å®æï¼è·¨æºå¨ç¨ SSHFS)
v0.4+        â?å¯é? Transport æ½è±¡å±?/ Redis (å¦éè¶åº SSHFS çåºæ?
```

### v0.3 å·²å®æåå®?
- Config ç³»ç»ï¼`agentteam config show/set/get/health`
- å¤ç¨æ·åä½ï¼`AgentTeam_USER` / `agentteam config set user`ï¼?user, name) å¤åå¯ä¸æ?
- Web UIï¼`agentteam board serve`ï¼SSE å®æ¶æ¨éï¼æ·±è²ä¸»é¢çæ¿
- è·¨æºå¨æ¹æ¡ï¼SSHFS/äºç + `AgentTeam_DATA_DIR`ï¼é¶ä»£ç æ¹å¨

## åä½å»ºè®®

ä¸¤äººå¹¶è¡çæä½³åå·¥æ¨¡å¼ï¼

```
Phase 1:  äººå A â?Transport æ½è±¡ + FileTransport
          äººå B â?Store æ½è±¡ + FileTaskStore + æµè¯

Phase 2:  äººå A â?RedisTransport æ ¸å¿å®ç°
          äººå B â?éç½®ç³»ç» + broadcast + éææµè¯

Phase 3:  äººå A â?RedisTeamStore
          äººå B â?RedisTaskStore + è¿ç§»å·¥å·
```

æ¥å£å®ä¹ï¼Phase 1ï¼è¦åä¸èµ·å¯¹é½ï¼åé¢å°±å¯ä»¥åååçã?
