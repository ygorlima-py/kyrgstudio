from __future__ import annotations

from typing import cast
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import CursorResult

from app.errors import StoreError
from app.store.base import EmailVerificationStoreBase
from app.store.models import EmailVerificationToken

class SQLAlchemyEmailVerificationStore(EmailVerificationStoreBase):
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def create_token(
        self,
        *,
        user_id: int,
        email: str,
        token_hash: str,
        expires_at: datetime,) -> EmailVerificationToken:
        
        """Persist one email verification token hash."""

        token = EmailVerificationToken(
            user_id=user_id,
            email=email.strip().lower(),
            token_hash=token_hash,
            expires_at=expires_at,
        )

        self.session.add(token)

        try:
            await self.session.flush()
        
        except Exception as error:
            raise StoreError(
                technical_message="Email verification token insert failed.",
                details={"operation": "create_email_verification_token"},
            ) from error
            
        return token
            
    async def get_token_by_hash(
        self,
        token_hash: str,
    ) -> EmailVerificationToken | None:
        """Return one verification token by deterministic hash."""

        statement = select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash
        )
        
        try:
            result = await self.session.execute(statement)
        
        except Exception as error:
            raise StoreError(
                technical_message="Email verification token lookup failed.",
                details={"operation": "get_email_verification_token_by_hash"},
            ) from error

        return result.scalar_one_or_none()
        
    async def mark_token_used(
            self,
            token_id: int,
        ) -> EmailVerificationToken:
        
        """Mark a verification token as consumed."""

        statement = (
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.id == token_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .values(used_at=func.now())
            .returning(EmailVerificationToken)
        )
        
        try:
            result = await self.session.execute(statement)   
        
        except Exception as error:
            raise StoreError(
                technical_message="Email verification token update failed.",
                details={"operation": "mark_email_verification_token_used"},
            ) from error
            
        token = result.scalar_one_or_none()
        
        if token is None:
            raise StoreError(
                technical_message=(
                    "Email verification token was missing or already used."
                ),
                details={"operation": "mark_email_verification_token_used"},
            )
            
        return token
    
    async def revoke_pending_tokens_for_user(
            self,
            user_id: int,
        ) -> int:
        """Consume all pending verification tokens for one user."""
        
        statement = (
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .values(used_at=func.now())
        )
        
        try:
            result = await self.session.execute(statement)
            
        except Exception as error:
            raise StoreError(
            technical_message="Email verification token bulk update failed.",
            details={"operation": "revoke_pending_email_verification_tokens"},
        ) from error
        
        cursor_result = cast(CursorResult, result)

        return cursor_result.rowcount or 0
    
    

        
        

        