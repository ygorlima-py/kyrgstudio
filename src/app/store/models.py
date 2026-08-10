from sqlalchemy.orm import (
    mapped_column,
    Mapped,
    DeclarativeBase,
    validates,
    )
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    func,
    Index,
    JSON,
    String,
    ForeignKey
)

from datetime import datetime


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"  # Alterado para plural para seguir seu padrão
        
    # Identificador interno do usuario no banco.
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Email usado para login, contato e identificacao unica do usuario.
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
    )
    
    # Hash da senha local; fica vazio quando o usuario entra apenas por OAuth.
    password_hash: Mapped[str | None] = mapped_column(
        String(256),
    )
    
    # Nome exibido no app, vindo do cadastro ou do Google.
    name: Mapped[str | None] = mapped_column(
        String(255),
    )
    
    # URL da imagem de perfil do usuario, geralmente vinda do Google.
    avatar_url: Mapped[str | None] = mapped_column(
        String(2048),
    )
    
    # Provider principal de autenticacao, como password ou google.
    auth_provider: Mapped[str] = mapped_column(
        String(50),
        default="password",
    )

    # Identificador unico do usuario no Google OAuth.
    google_sub: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    
    # Data em que o email do usuario foi verificado.
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    # Data em que o usuario foi criado.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Data da ultima atualizacao do usuario.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Data de desativacao do usuario sem apagar o registro do banco.
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    
    @validates("email")
    def validate_email(self, key, value):
        if not "@" in value:
            raise ValueError("Invalid email address")
        else:
            return value.strip().lower()


class AuthSession(Base):
    """Persisted refresh-token session used for rotation and revocation."""

    __tablename__ = "auth_sessions"

    # Identificador interno da sessao de autenticacao.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Usuario ao qual esta sessao de refresh pertence.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Hash do refresh token; o token original nunca e salvo no banco.
    token_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )

    # Identificador compartilhado pelas rotacoes da mesma sessao.
    family_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    # Data limite para uso desta sessao de refresh.
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Data da ultima utilizacao valida do refresh token.
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Data de revogacao; fica vazia enquanto a sessao estiver ativa.
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Nova sessao que substituiu esta durante a rotacao do refresh token.
    replaced_by_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Data em que a sessao foi criada.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    # Identificador interno da assinatura no banco.
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Usuario dono desta assinatura.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    
    # Identificador do cliente na Stripe.
    stripe_customer_id: Mapped[str] = mapped_column(
        String(255),
        index=True,
    )

    # Identificador da assinatura na Stripe.
    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
    )

    # Identificador do preco/plano contratado na Stripe.
    stripe_price_id: Mapped[str | None] = mapped_column(
        String(255),
    )

    # Status atual da assinatura, como active, canceled ou past_due.
    status: Mapped[str] = mapped_column(
        String(50),
    )

    # Nome interno do plano usado pelo app.
    plan: Mapped[str | None] = mapped_column(
        String(50),
    )

    # Inicio do periodo atual da assinatura.
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    # Fim do periodo atual da assinatura.
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    # Indica se a assinatura sera cancelada ao fim do periodo atual.
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )

    # Data em que a assinatura foi criada no banco local.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Data da ultima atualizacao local da assinatura.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
class BillingEvent(Base):
    __tablename__ = "billing_events"
    
    # Identificador interno do evento de billing no banco.
    id: Mapped[int] = mapped_column(primary_key=True)

    # ID unico do evento recebido da Stripe; usado para idempotencia.
    stripe_event_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
    )

    # Tipo do evento da Stripe, como customer.subscription.updated.
    event_type: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )

    # Payload bruto ou normalizado do webhook recebido da Stripe.
    payload_json: Mapped[dict] = mapped_column(
        JSON,
    )

    # Data em que o evento foi processado pelo app.
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    # Data em que o evento foi registrado no banco.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_user_created_id", "user_id", "created_at", "id"),
        Index(
            "ix_jobs_user_status_created_id",
            "user_id",
            "status",
            "created_at",
            "id",
        ),
        Index(
            "ix_jobs_user_pipeline_created_id",
            "user_id",
            "pipeline_type",
            "created_at",
            "id",
        ),
    )

    # Identificador interno do job no banco.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Usuario dono desta execucao.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Chave de idempotencia da execucao enviada pelo cliente.
    run_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
    )

    # Status geral do job, como pending, running, completed ou failed.
    status: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    # Etapa atual do processamento, usada para progresso e debug.
    current_step: Mapped[str] = mapped_column(
        String(100),
    )

    # Tipo de pipeline executado, como copy_analysis ou copy_adaptation.
    pipeline_type: Mapped[str] = mapped_column(
        String(50),
    )

    # Input normalizado usado para iniciar o pipeline.
    input_json: Mapped[dict] = mapped_column(
        JSON,
    )

    # Backend onde os arquivos do job foram armazenados.
    storage_backend: Mapped[str | None] = mapped_column(
        String(50),
    )

    # Chave do arquivo original no storage.
    input_file_key: Mapped[str | None] = mapped_column(
        String(1024),
    )

    # URI do arquivo original no storage.
    input_file_uri: Mapped[str | None] = mapped_column(
        String(2048),
    )

    # Chave do audio extraido no storage.
    audio_file_key: Mapped[str | None] = mapped_column(
        String(1024),
    )

    # URI do audio extraido no storage.
    audio_file_uri: Mapped[str | None] = mapped_column(
        String(2048),
    )

    # Resultado final estruturado do pipeline.
    output_json: Mapped[dict | None] = mapped_column(
        JSON,
    )

    # Erro final controlado, caso o job falhe.
    error_json: Mapped[dict | None] = mapped_column(
        JSON,
    )

    # Uso de tokens consolidado da execucao.
    token_usage_json: Mapped[dict | None] = mapped_column(
        JSON,
    )

    # Tempo total de execucao do job em segundos.
    execution_time_seconds: Mapped[float | None] = mapped_column(
        Float,
    )

    # Data em que o job foi criado.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # Data da ultima atualizacao do job.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Data em que o processamento realmente comecou.
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    # Data em que o processamento terminou com sucesso, falha ou cancelamento.
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )


class JobEvent(Base):
    __tablename__ = "job_events"
    __table_args__ = (
        Index("ix_job_events_job_id_created_at", "job_id", "created_at"),
    )
    
    # Identificador interno do evento do job no banco.
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Job ao qual este evento pertence.
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False,
    )

    # Etapa do job relacionada ao evento.
    step: Mapped[str] = mapped_column(
        String(100),
    )

    # Tipo do evento, como step_completed, warning ou checkpoint.
    event_type: Mapped[str] = mapped_column(
        String(100),
    )

    # Dados adicionais do evento, sem payloads grandes ou sensiveis.
    payload_json: Mapped[dict | None] = mapped_column(
        JSON,
    )

    # Data em que o evento foi registrado.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

class BillingCustomer(Base):
    __tablename__ = "billing_customers"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Usuario dono deste customer na Stripe.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Identificador do customer na Stripe, exemplo: cus_123.
    stripe_customer_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    # Data em que o customer foi registrado localmente.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Data da ultima atualizacao local do customer.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

class EmailVerificationToken(Base):
    """One-time token used to confirm ownership of a user's email address.

    The raw token is never persisted. Only ``token_hash`` is stored so a leaked
    database cannot be used to verify accounts.
    """

    __tablename__ = "email_verification_tokens"

    # Identificador interno do token de verificacao.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Usuario que precisa confirmar o email.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Hash deterministico do token enviado por email.
    token_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )

    # Email que este token confirma.
    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    # Momento em que o token deixa de ser aceito.
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Momento em que o token foi consumido; vazio enquanto estiver pendente.
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Data de criacao do pedido de verificacao.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )