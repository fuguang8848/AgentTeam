"""
A2A Idempotency Module - A2A 协议幂等性增强

参考 SpectrAI/src/main/protocol/a2a/IdempotencyManager.ts 实现
提供 Agent 间消息的事务支持和重复消息去重

功能：
- IdempotencyKey 生成和验证
- Agent 间消息事务支持
- 重复消息去重
- 消息处理状态跟踪

@author AgentTeam
@version 1.0.0
"""

import hashlib
import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MessageStatus(Enum):
    """消息处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


@dataclass
class IdempotencyKey:
    """
    幂等性键

    用于唯一标识一条消息，支持多种生成方式：
    - 自动生成（基于内容hash）
    - 显式指定（业务自定义）
    - 复合生成（agent_id + task_id + 内容hash）
    """
    key: str
    agent_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.now() > expires
        except ValueError:
            return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }


@dataclass
class MessageRecord:
    """消息记录"""
    idempotency_key: str
    message_id: str
    status: MessageStatus
    created_at: str
    processed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    ttl_seconds: int = 3600  # 默认1小时

    def is_expired(self) -> bool:
        """检查是否过期"""
        try:
            created = datetime.fromisoformat(self.created_at)
            expiry_time = created + timedelta(seconds=self.ttl_seconds)
            return datetime.now() > expiry_time
        except ValueError:
            return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idempotency_key": self.idempotency_key,
            "message_id": self.message_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "processed_at": self.processed_at,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "ttl_seconds": self.ttl_seconds,
        }


@dataclass
class TransactionContext:
    """事务上下文"""
    transaction_id: str
    idempotency_keys: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "active"  # active, committed, rolled_back, expired
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "idempotency_keys": self.idempotency_keys,
            "created_at": self.created_at,
            "status": self.status,
            "metadata": self.metadata,
        }


class IdempotencyStore:
    """
    幂等性存储

    内存存储实现，生产环境建议使用 Redis
    """

    def __init__(self, default_ttl: int = 3600):
        """
        初始化存储

        Args:
            default_ttl: 默认 TTL 秒数
        """
        self._default_ttl = default_ttl
        self._records: Dict[str, MessageRecord] = {}
        self._locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._global_lock = threading.RLock()

    def _get_lock(self, key: str) -> threading.Lock:
        """获取指定 key 的锁"""
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def get(self, idempotency_key: str) -> Optional[MessageRecord]:
        """
        获取消息记录

        Args:
            idempotency_key: 幂等性键

        Returns:
            MessageRecord 或 None
        """
        with self._get_lock(idempotency_key):
            record = self._records.get(idempotency_key)
            if record and record.is_expired():
                del self._records[idempotency_key]
                return None
            return record

    def set(self, record: MessageRecord) -> None:
        """
        保存消息记录

        Args:
            record: 消息记录
        """
        with self._get_lock(record.idempotency_key):
            self._records[record.idempotency_key] = record

    def delete(self, idempotency_key: str) -> bool:
        """
        删除消息记录

        Args:
            idempotency_key: 幂等性键

        Returns:
            是否成功删除
        """
        with self._get_lock(idempotency_key):
            if idempotency_key in self._records:
                del self._records[idempotency_key]
                return True
            return False

    def update_status(
        self,
        idempotency_key: str,
        status: MessageStatus,
        result: Any = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        更新消息状态

        Args:
            idempotency_key: 幂等性键
            status: 新状态
            result: 处理结果
            error: 错误信息

        Returns:
            是否成功更新
        """
        with self._get_lock(idempotency_key):
            record = self._records.get(idempotency_key)
            if not record:
                return False

            record.status = status
            record.processed_at = datetime.now().isoformat()
            if result is not None:
                record.result = result
            if error:
                record.error = error

            return True

    def clear_expired(self) -> int:
        """
        清除过期记录

        Returns:
            清除的记录数
        """
        with self._global_lock:
            expired_keys = [
                key for key, record in self._records.items()
                if record.is_expired()
            ]
            for key in expired_keys:
                del self._records[key]
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        with self._global_lock:
            status_counts = defaultdict(int)
            for record in self._records.values():
                status_counts[record.status.value] += 1

            return {
                "total_records": len(self._records),
                "status_counts": dict(status_counts),
                "default_ttl": self._default_ttl,
            }


class IdempotencyManager:
    """
    幂等性管理器

    提供消息幂等性保证和事务支持

    使用示例：
        manager = IdempotencyManager()

        # 检查消息是否已处理
        status, result = manager.check_and_process(
            agent_id="agent-1",
            message_id="msg-123",
            content={"action": "create_user", "data": {...}}
        )

        if status == MessageStatus.DUPLICATE:
            print(f"重复消息，返回缓存结果: {result}")
        elif status == MessageStatus.COMPLETED:
            print(f"处理完成: {result}")
        else:
            print(f"需要处理新消息")

        # 事务支持
        with manager.begin_transaction(agent_id="agent-1") as tx:
            tx.add_message(msg1)
            tx.add_message(msg2)
            tx.add_message(msg3)
            # 提交时所有消息会原子性处理
    """

    def __init__(
        self,
        store: Optional[IdempotencyStore] = None,
        default_ttl: int = 3600,
        auto_cleanup_interval: int = 300,
    ):
        """
        初始化幂等性管理器

        Args:
            store: 幂等性存储，默认创建内存存储
            default_ttl: 默认 TTL 秒数
            auto_cleanup_interval: 自动清理过期记录间隔（秒）
        """
        self._store = store or IdempotencyStore(default_ttl)
        self._default_ttl = default_ttl
        self._transactions: Dict[str, TransactionContext] = {}
        self._tx_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)

        # 消息处理器
        self._handlers: Dict[str, Callable] = {}

        # 锁
        self._global_lock = threading.RLock()

        # 启动自动清理
        self._cleanup_interval = auto_cleanup_interval
        self._last_cleanup = time.time()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        """启动管理器（启动清理线程）"""
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("IdempotencyManager started")

    def stop(self):
        """停止管理器"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("IdempotencyManager stopped")

    def _cleanup_loop(self):
        """清理循环"""
        while self._running:
            try:
                time.sleep(self._cleanup_interval)
                if time.time() - self._last_cleanup >= self._cleanup_interval:
                    count = self._store.clear_expired()
                    if count > 0:
                        logger.debug(f"Cleaned up {count} expired records")
                    self._last_cleanup = time.time()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    def generate_key(
        self,
        agent_id: str,
        message_id: Optional[str] = None,
        content: Optional[Any] = None,
        custom_prefix: Optional[str] = None,
    ) -> IdempotencyKey:
        """
        生成幂等性键

        Args:
            agent_id: 目标 Agent ID
            message_id: 消息 ID（可选）
            content: 消息内容（可选）
            custom_prefix: 自定义前缀

        Returns:
            IdempotencyKey
        """
        # 构建 key
        if custom_prefix:
            key_parts = [custom_prefix, agent_id]
        else:
            key_parts = ["idempotency", agent_id]

        if message_id:
            key_parts.append(message_id)

        # 如果有内容，加入 hash
        content_hash = None
        if content is not None:
            content_str = json.dumps(content, sort_keys=True, default=str)
            content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
            key_parts.append(content_hash)

        key = ":".join(key_parts)

        return IdempotencyKey(
            key=key,
            agent_id=agent_id,
            metadata={
                "message_id": message_id,
                "content_hash": content_hash,
            },
        )

    def check_and_process(
        self,
        agent_id: str,
        message_id: str,
        content: Any,
        handler: Optional[Callable] = None,
        ttl: Optional[int] = None,
    ) -> tuple[MessageStatus, Optional[Any]]:
        """
        检查消息是否已处理，如果是则返回缓存结果

        Args:
            agent_id: Agent ID
            message_id: 消息 ID
            content: 消息内容
            handler: 处理函数 (content) -> result
            ttl: TTL 秒数

        Returns:
            (MessageStatus, result)
        """
        # 生成幂等性键
        idempotency_key = self.generate_key(agent_id, message_id, content)
        key_str = idempotency_key.key

        # 检查是否已存在
        existing = self._store.get(key_str)

        if existing:
            if existing.status == MessageStatus.PROCESSING:
                # 正在处理中，返回进行中状态
                return (MessageStatus.PROCESSING, None)
            elif existing.status == MessageStatus.COMPLETED:
                # 已完成，返回缓存结果
                return (MessageStatus.DUPLICATE, existing.result)
            elif existing.status == MessageStatus.FAILED:
                # 之前失败，可以重试
                # 更新状态为处理中
                self._store.update_status(key_str, MessageStatus.PROCESSING)
                return (MessageStatus.PENDING, None)

        # 新消息，创建记录
        ttl = ttl or self._default_ttl
        record = MessageRecord(
            idempotency_key=key_str,
            message_id=message_id,
            status=MessageStatus.PENDING,
            created_at=datetime.now().isoformat(),
            ttl_seconds=ttl,
        )
        self._store.set(record)

        # 如果没有处理器，返回待处理状态
        if handler is None:
            # 注册默认处理器
            handler = self._handlers.get(agent_id)

        if handler is None:
            return (MessageStatus.PENDING, None)

        # 标记为处理中
        self._store.update_status(key_str, MessageStatus.PROCESSING)

        try:
            # 执行处理
            result = handler(content)

            # 更新为完成
            self._store.update_status(key_str, MessageStatus.COMPLETED, result=result)
            return (MessageStatus.COMPLETED, result)

        except Exception as e:
            # 更新为失败
            self._store.update_status(key_str, MessageStatus.FAILED, error=str(e))
            return (MessageStatus.FAILED, None)

    def register_handler(self, agent_id: str, handler: Callable):
        """
        注册消息处理器

        Args:
            agent_id: Agent ID
            handler: 处理函数
        """
        with self._global_lock:
            self._handlers[agent_id] = handler

    def begin_transaction(
        self,
        agent_id: str,
        transaction_id: Optional[str] = None,
        ttl: int = 300,
    ) -> "TransactionContext":
        """
        开始一个事务

        Args:
            agent_id: Agent ID
            transaction_id: 事务 ID，默认自动生成
            ttl: 事务超时时间（秒）

        Returns:
            TransactionContext
        """
        tx_id = transaction_id or f"tx_{int(time.time() * 1000)}"

        with self._global_lock:
            if tx_id in self._transactions:
                raise ValueError(f"Transaction {tx_id} already exists")

            tx = TransactionContext(
                transaction_id=tx_id,
                metadata={"agent_id": agent_id, "ttl": ttl},
            )
            self._transactions[tx_id] = tx

            logger.debug(f"Transaction {tx_id} started for agent {agent_id}")
            return tx

    def add_to_transaction(
        self,
        transaction_id: str,
        message_id: str,
        content: Any,
    ) -> IdempotencyKey:
        """
        添加消息到事务

        Args:
            transaction_id: 事务 ID
            message_id: 消息 ID
            content: 消息内容

        Returns:
            IdempotencyKey
        """
        with self._global_lock:
            tx = self._transactions.get(transaction_id)
            if not tx:
                raise ValueError(f"Transaction {transaction_id} not found")
            if tx.status != "active":
                raise ValueError(f"Transaction {transaction_id} is not active")

            agent_id = tx.metadata.get("agent_id", "")
            key = self.generate_key(agent_id, message_id, content)
            tx.idempotency_keys.append(key.key)

            return key

    def commit_transaction(
        self,
        transaction_id: str,
        handler: Optional[Callable[[List[Any]], List[Any]]] = None,
    ) -> List[Any]:
        """
        提交事务

        Args:
            transaction_id: 事务 ID
            handler: 批量处理函数，默认顺序处理每个消息

        Returns:
            处理结果列表
        """
        with self._global_lock:
            tx = self._transactions.get(transaction_id)
            if not tx:
                raise ValueError(f"Transaction {transaction_id} not found")

            if tx.status != "active":
                raise ValueError(f"Transaction {transaction_id} is not active (status: {tx.status})")

        # 准备消息列表（按添加顺序）
        messages = []
        for key_str in tx.idempotency_keys:
            record = self._store.get(key_str)
            if record:
                messages.append(record.result)
            else:
                messages.append(None)

        # 执行批量处理
        results: List[Any] = []
        if handler is not None:
            try:
                results = handler(messages)
            except Exception as e:
                logger.error(f"Transaction {transaction_id} handler failed: {e}")
                self._rollback_transaction(transaction_id)
                raise
        else:
            results = messages

        # 更新事务状态
        with self._global_lock:
            tx.status = "committed"

        # 更新所有消息为已完成
        for key_str in tx.idempotency_keys:
            record = self._store.get(key_str)
            if record and record.status == MessageStatus.PROCESSING:
                self._store.update_status(key_str, MessageStatus.COMPLETED)

        logger.info(f"Transaction {transaction_id} committed with {len(results)} results")
        return results

    def rollback_transaction(self, transaction_id: str):
        """
        回滚事务

        Args:
            transaction_id: 事务 ID
        """
        self._rollback_transaction(transaction_id)

    def _rollback_transaction(self, transaction_id: str):
        """内部回滚方法"""
        with self._global_lock:
            tx = self._transactions.get(transaction_id)
            if not tx:
                return

            # 将所有消息标记为失败
            for key_str in tx.idempotency_keys:
                record = self._store.get(key_str)
                if record and record.status == MessageStatus.PROCESSING:
                    self._store.update_status(key_str, MessageStatus.FAILED, error="Transaction rolled back")

            tx.status = "rolled_back"
            logger.info(f"Transaction {transaction_id} rolled back")

    def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        获取事务状态

        Args:
            transaction_id: 事务 ID

        Returns:
            事务信息或 None
        """
        with self._global_lock:
            tx = self._transactions.get(transaction_id)
            if not tx:
                return None
            return tx.to_dict()

    def cleanup_old_transactions(self, max_age_seconds: int = 3600) -> int:
        """
        清理过期事务

        Args:
            max_age_seconds: 最大存活时间

        Returns:
            清理数量
        """
        with self._global_lock:
            now = datetime.now()
            to_delete = []

            for tx_id, tx in self._transactions.items():
                try:
                    created = datetime.fromisoformat(tx.created_at)
                    if (now - created).total_seconds() > max_age_seconds:
                        to_delete.append(tx_id)
                except ValueError:
                    to_delete.append(tx_id)

            for tx_id in to_delete:
                del self._transactions[tx_id]

            return len(to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计"""
        with self._global_lock:
            return {
                "store_stats": self._store.get_stats(),
                "active_transactions": len([
                    tx for tx in self._transactions.values()
                    if tx.status == "active"
                ]),
                "total_transactions": len(self._transactions),
                "registered_handlers": len(self._handlers),
            }

    def deduplicate_messages(
        self,
        agent_id: str,
        messages: List[Dict[str, Any]],
        message_id_field: str = "id",
        content_field: str = "content",
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        对消息列表进行去重

        Args:
            agent_id: Agent ID
            messages: 消息列表
            message_id_field: 消息 ID 字段名
            content_field: 内容字段名

        Returns:
            (unique_messages, duplicate_messages)
        """
        unique = []
        duplicates = []

        for msg in messages:
            msg_id = msg.get(message_id_field, "")
            content = msg.get(content_field)

            status, _ = self.check_and_process(
                agent_id=agent_id,
                message_id=msg_id,
                content=content,
                ttl=3600,
            )

            if status == MessageStatus.DUPLICATE:
                duplicates.append(msg)
            else:
                unique.append(msg)

        return unique, duplicates


# 全局幂等性管理器实例
_default_manager: Optional[IdempotencyManager] = None
_manager_lock = threading.Lock()


def get_idempotency_manager() -> IdempotencyManager:
    """
    获取全局幂等性管理器实例（单例）

    Returns:
        IdempotencyManager
    """
    global _default_manager
    with _manager_lock:
        if _default_manager is None:
            _default_manager = IdempotencyManager()
            _default_manager.start()
        return _default_manager


def generate_idempotency_key(
    agent_id: str,
    message_id: Optional[str] = None,
    content: Optional[Any] = None,
) -> IdempotencyKey:
    """
    快捷函数：生成幂等性键

    Args:
        agent_id: Agent ID
        message_id: 消息 ID
        content: 消息内容

    Returns:
        IdempotencyKey
    """
    manager = get_idempotency_manager()
    return manager.generate_key(agent_id, message_id, content)
