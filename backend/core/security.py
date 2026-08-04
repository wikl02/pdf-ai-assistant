"""密码哈希与 JWT 访问令牌工具。

本模块只负责安全算法，不查询数据库，也不判断用户角色。
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from backend.core.config import settings


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    # bcrypt 只处理前 72 字节，提前拒绝可避免“不同长密码得到相同结果”。
    if len(password_bytes) > 72:
        raise ValueError("密码的 UTF-8 编码不能超过 72 字节")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def create_access_token(*, user_id: int, username: str, role: str) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        # sub 是 JWT 的标准“主体”字段，这里保存用户 ID，后续会据此重新查库。
        "sub": str(user_id),
        "username": username,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    # 除了验签和过期时间，还要确认令牌用途，防止其他类型令牌被当作访问令牌。
    if payload.get("type") != "access" or not payload.get("sub"):
        raise jwt.InvalidTokenError("invalid access token")
    return payload
