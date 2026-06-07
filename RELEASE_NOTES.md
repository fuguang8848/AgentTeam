# ð AgentTeam-OpenClaw v0.4.0 åå¸è¯´æ

**åå¸æ¥æ**: 2026-05-02  
**çæ¬**: v0.4.0-openclaw  
**ç±»å**: çäº§çº§å¤æºè½ä½åè°æ¡æ?

---

## ð£ å¬å

AgentTeam-OpenClaw æ?[HKUDS/AgentTeam](https://github.com/HKUDS/AgentTeam) ççäº§çº§ forkï¼ä¸æ³?OpenClaw çæã?

> **è¿ä¸æ¯ä¸ä¸?demoãè¿æ¯å¯ä»¥ä¸çº¿ççäº§è½¯ä»¶ã?*

---

## ð v0.4.0 æ°åè½ï¼ç¸æ¯ä¸æ¸¸ v0.3.0ï¼?

### 1. ð Web UI çæ¿

**åæ´**: ð æ°å¢

ä¸ååªè½ç?CLI ç?tmux çªå£äºãç°å¨æå®æ´ç?Web çæ¿ï¼?

- **ç«¯å£**: `8080`ï¼é»è®¤ï¼
- **æ ç­¾é¡?*: çæ¿ / è®¾è®¡å?/ å®æ¶çæ§ / å·¥ä½æµ?/ è®¾ç½®
- **å®æ¶å·æ°**: Agent ç¶æãä»»å¡è¿åº¦ãæ¼ç§»é¢è­¦ä¸ç®äºç?
- **ä¸é®å¯å?*: `agentteam board serve --port 8080`

```bash
# å¯å¨ Web çæ¿
agentteam board serve --port 8080

# æµè§å¨æå¼
open http://127.0.0.1:8080
```

---

### 2. ð API è®¤è¯ç³»ç»

**åæ´**: ð æ°å¢

çäº§ç¯å¢å¿å¤ç?API å®å¨æºå¶ï¼?

- **Token è®¤è¯**: JWT-like ç­æ Token
- **Gateway Token ä¼ é?*: èªå¨ååå°å­ Agentï¼è§£å³å­ Agent æ æ³è¿æ¥çé®é¢ï¼
- **Session éç¦»**: æ¯ä¸ª Agent ç¬ç«ä¼è¯
- **ç¯å¢åéç®¡ç**: `.env` åç¦»ï¼ææä¿¡æ¯ä¸ä¸ä¼ 

---

### 3. ð§  æºè½è·¯ç±ç³»ç»

**åæ´**: ð æ°å¢

ä¸å ç´ è·¯ç±ç®æ³ï¼æ¯?éæºåé"èªæ 10 åï¼

| å ç´  | æé | è¯´æ |
|------|------|------|
| **æè½å¹é?* | 0-50 å?| å³é®è¯æåï¼æ¯æä¸­è±æï¼ |
| **åå²è¡¨ç°** | 0-30 å?| æåç?+ è´¨éè¯å |
| **è´è½½æç¥** | -15 å?| å½åä»»å¡æ°è¿å¤èªå¨éæ?|

```python
# è·¯ç±ç¤ºä¾
best_agent = router.route(
    available_agents=[alice, bob, charlie],
    task="implement authentication",
    topic="backend auth security"
)
# èªå¨éæ©æåéç Agent
```

---

### 4. ð å®¡è®¡æ¥å¿

**åæ´**: ð æ°å¢

å®æ´çäºä»¶è¿½æº¯ç³»ç»ï¼

- **äºä»¶ç±»å**: SPAWN / TASK_UPDATE / INBOX_SEND / ALERT_TRIGGER ç­?
- **å­æ®µ**: event_id / event_type / actor / details / timestamp / team
- **è¿½å åå¥**: åå²äºä»¶æ°¸ä¸ä¿®æ¹
- **æ¥è¯¢ CLI**: `agentteam audit query <team> --action SPAWN --limit 100`

```bash
# æ¥è¯¢å¢éå®¡è®¡æ¥å¿
agentteam audit query my-team --actor alice --json

# å®¡è®¡æ´»å¨æè¦
agentteam audit summary my-team
```

---

### 5. ð¨ åè­¦æºå¶

**åæ´**: ð æ°å¢

åçº§åè­¦ç³»ç»ï¼åºäºé®é¢ç¬¬ä¸æ¶é´ç¥éï¼?

| çº§å« | è¯´æ | åºæ¯ |
|------|------|------|
| **LOW** | æç¤º | ä»»å¡é¿æ¶é´æ æ´æ° |
| **MEDIUM** | æ³¨æ | Agent å¤±è´¥ç?> 10% |
| **HIGH** | è­¦å | å¢é > 5 åéæ æ´»å?|
| **CRITICAL** | ç´§æ?| å³é®ä»»å¡è¶æ¶ |

```bash
# æ£æ¥åè­?
agentteam alert check --team my-team

# ååºææåè­?
agentteam alert list --team my-team

# ç¡®è®¤åè­¦
agentteam alert ack --alert-id <id>
```

---

### 6. ð è´¨éè¯åä¸æ¼ç§»æ£æµ?

**åæ´**: ð æ°å¢

| åè½ | è¯´æ |
|------|------|
| **QualityScore** | completeness(0.25) / accuracy(0.30) / quality(0.20) / è§èæ?0.15) / innovation(0.10) |
| **æ¼ç§»æ£æµ?* | Jaccard + è¯­ä¹ç¸ä¼¼åº¦åæ ¡éªï¼éå?5 çº§ï¼æ âä¸¥éï¼?|

---

### 7. ð éè¯æ¡æ¶

**åæ´**: ð æ°å¢

åä¹ä¸ç¨æå¿ç½ç»æå¨äºï¼

- **è£é¥°å?*: `@retry` / `@retry_async`
- **ææ°éé?*: èªå¨å»¶è¿ + æå¨
- **ç»è®¡**: èªå¨è®°å½éè¯æ¬¡æ°

```python
from agentteam.utils.retry import retry

@retry(max_attempts=3, delay=1.0, backoff=2.0)
def deliver_message():
    transport.deliver(message)
```

---

### 8. ð ç»æåæ¥å¿?

**åæ´**: ð æ°å¢

çäº§çº§å¯è°è¯æ¥å¿ï¼?

- **JSON æ ¼å¼**: ç»æåè¾åºï¼æ¹ä¾¿è§£æ
- **trace_id**: å¨é¾è·¯è¿½è¸?
- **RotatingFileHandler**: 10MB/æä»¶ï¼? ä¸ªå¤ä»?
- **ç¯å¢åé**: `AgentTeam_LOG_LEVEL=DEBUG`

---

### 9. ð³ Docker æ¯æ

**åæ´**: ð æ°å¢ / å¢å¼º

```bash
# å¼åç¯å¢?
make dev

# çäº§ç¯å¢
make prod

# è¿è¡æµè¯
make test

# æ¸ç
make clean
```

`docker-compose.yml` åå«å®æ´çæå¡æ ï¼æ éæå¨å®è£ã?

---

### 10. ð§ª æµè¯è¦ç

**åæ´**: ð æ°å¢

| æµè¯æ¨¡å | ç¨ä¾æ?| ç¶æ?|
|----------|--------|------|
| P0 å·¥ç¨å?| 50+ | â?|
| P1 è·¯ç± | 18+ | â?|
| P1 åè­¦ | 5+ | â?|
| P1 å®¡è®¡ | 7+ | â?|
| éææµè¯ | 30+ | â?|
| **æ»è®¡** | **1790+** | **â?å¨é¨éè¿** |

---

### 11. ð å®æ´ææ¡£

**åæ´**: ð æ°å¢ / å¢å¼º

| ææ¡£ | åå®¹ |
|------|------|
| [README.md](README.md) | å®æ´é¡¹ç®ä»ç» |
| [API.md](API.md) | REST API å®æ´åèï¼~5000 å­ï¼ |
| [CLI.md](CLI.md) | CLI å½ä»¤è¯¦è§£ï¼~5000 å­ï¼ |
| [DEPLOY.md](DEPLOY.md) | Docker / è£¸æº / åå¸å¼é¨ç½?|
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | å¼åèæå?|
| [CONTRIBUTING.md](CONTRIBUTING.md) | è´¡ç®æå |

---

### 12. ð Shell è¡¥å¨

**åæ´**: ð æ°å¢

```bash
# å®è£ bash è¡¥å¨
./shell-completion.sh bash

# å®è£ zsh è¡¥å¨
./shell-completion.sh zsh

# å®è£ fish è¡¥å¨
./shell-completion.sh fish
```

---

### 13. ð å¤è¯­è¨ææ¡£

**åæ´**: ð æ°å¢

| è¯­è¨ | æä»¶ |
|------|------|
| ðºð¸ English | README.md |
| ð¨ð³ ç®ä½ä¸­æ?| README_CN.md |
| ð¹ð¼ ç¹é«ä¸­æ | README_TW.md |
| ð¯ðµ æ¥æ¬èª?| README_JA.md |
| ð°ð· íêµ­ì?| README_KO.md |
| ð«ð· FranÃ§ais | README_FR.md |
| ð©ðª Deutsch | README_DE.md |
| ð®ð¹ Italiano | README_IT.md |
| ð·ðº Ð ÑÑÑÐºÐ¸Ð¹ | README_RU.md |
| ð§ð· PortuguÃªs | README_PT-BR.md |

---

## ð§ ææ¯ç»è?

### çæ¬å¯¹åºå³ç³»

| ç»ä»¶ | çæ¬ |
|------|------|
| Python | â?.10 |
| OpenClaw | 4.2+ å¼å®¹ |
| Claude Code | æ¯æ |
| Codex | æ¯æ |

### æä»¶ä¼ è¾å±?

| ä¼ è¾æ¹å¼ | è¯´æ | ä¾èµ |
|----------|------|------|
| **Filesystem** | é»è®¤ï¼æ éé¢å¤ä¾èµ | æ?|
| **Redis** | åå¸å¼å¢é?| `redis` |
| **ZeroMQ P2P** | ç¹å¯¹ç?| `pyzmq` |

---

## ð åçº§è·¯å¾

### ä»ä¸æ¸?AgentTeam åçº§

```bash
# 1. æåææ°ä»£ç ?
git remote add upstream https://github.com/HKUDS/AgentTeam.git
git fetch upstream
git merge upstream/main

# 2. å®è£ä¾èµ
pip install -e .

# 3. è¿è¡æµè¯
python -m pytest tests/ -v

# 4. å¯å¨ Web çæ¿éªè¯
agentteam board serve --port 8080
```

### ä»æ§çæ¬åçº§

```bash
# 1. æåææ?
git pull origin main

# 2. éæ°å®è£ä¾èµ
pip install -e .

# 3. éªè¯
agentteam --version
agentteam board serve --port 8080
```

---

## ð è´è°¢

- **[HKUDS/AgentTeam](https://github.com/HKUDS/AgentTeam)** â?åå§æ¡æ¶ï¼ææä¸æ¸¸è´¡ç®è?
- **[OpenClaw](https://openclaw.ai)** â?é»è®¤ Agent å¼æ
- **æææµè¯è?* â?1790+ æµè¯ç¨ä¾çèå?

---

## ð èç³»æä»¬

- **GitHub Issues**: https://github.com/YOUR_USERNAME/AgentTeam-OpenClaw/issues
- **Discord**: https://discord.com/invite/clawd
- **ææ¡£**: https://docs.openclaw.ai

---

## ð è®¸å¯è¯?

MIT License - è¯¦è§ [LICENSE](LICENSE)

---

_AgentTeam-OpenClaw v0.4.0 â?2026-05-02_
