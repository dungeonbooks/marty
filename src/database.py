"""
Database module for Marty SMS Bookstore Chatbot.
Provides SQLAlchemy models, Pydantic schemas, and async database operations.
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./marty.db")

# Setup logger
logger = structlog.get_logger(__name__)

# SQLAlchemy setup
Base = declarative_base()

# Create engine and session factory (will be initialized when needed)
engine = None
AsyncSessionLocal = None


def init_database():
    """Initialize database engine and session factory."""
    global engine, AsyncSessionLocal
    if engine is None:
        # Determine if we're using PostgreSQL
        is_postgres = DATABASE_URL.startswith(
            ("postgresql://", "postgresql+asyncpg://")
        )

        if is_postgres:
            # Convert postgresql:// to postgresql+asyncpg:// for async driver
            async_db_url = DATABASE_URL
            if async_db_url.startswith("postgresql://"):
                async_db_url = async_db_url.replace(
                    "postgresql://", "postgresql+asyncpg://", 1
                )

            # PostgreSQL configuration (Railway/Supabase)
            engine = create_async_engine(
                async_db_url,
                echo=False,  # Set to True for debugging
                pool_size=10,
                max_overflow=5,
                pool_pre_ping=True,
                pool_recycle=300,  # 5 minutes
                connect_args={
                    "server_settings": {
                        "jit": "off",  # Disable JIT for better connection stability
                    }
                },
            )
        else:
            # SQLite configuration (for development)
            engine = create_async_engine(
                DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
            )

        AsyncSessionLocal = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )


# SQLAlchemy Models
class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    square_customer_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Discord fields
    discord_user_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    discord_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform: Mapped[str] = mapped_column(String(50), default="discord", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=func.now()
    )

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="customer"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=False
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # Discord fields
    discord_user_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    discord_channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discord_guild_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform: Mapped[str] = mapped_column(String(50), default="discord", nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active, ended, timeout
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Store conversation context and metadata
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    mentioned_books: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="conversations"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # inbound, outbound
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    # Index for efficient queries
    __table_args__ = (
        Index("idx_conversation_timestamp", "conversation_id", "timestamp"),
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    isbn: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # External IDs
    hardcover_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    bookshop_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    format: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # hardcover, paperback, ebook
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=func.now()
    )

    # Relationships
    inventory: Mapped[list["Inventory"]] = relationship(
        "Inventory", back_populates="book"
    )


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("books.id"), nullable=False
    )
    location: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # store, warehouse, bookshop
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Availability
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", back_populates="inventory")

    # Ensure one inventory record per book per location
    __table_args__ = (UniqueConstraint("book_id", "location", name="uq_book_location"),)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=False
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=True
    )

    # Order details
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending, confirmed, shipped, delivered, cancelled
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Square integration
    square_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, paid, failed

    # Fulfillment
    fulfillment_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # pickup, shipping, digital
    shipping_address: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=func.now()
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    conversation: Mapped["Conversation | None"] = relationship("Conversation")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False
    )
    book_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("books.id"), nullable=False
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    book: Mapped["Book"] = relationship("Book")


class RateLimit(Base):
    __tablename__ = "rate_limits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    identifier: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # phone number or IP
    limit_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # sms, api, etc.
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Efficient lookups
    __table_args__ = (
        Index("idx_identifier_type", "identifier", "limit_type"),
        Index("idx_expires_at", "expires_at"),
    )


# Pydantic Schemas
class CustomerCreate(BaseModel):
    phone: str | None = Field(None, min_length=10, max_length=20)
    name: str | None = None
    email: str | None = None
    square_customer_id: str | None = Field(None, max_length=100)
    discord_user_id: str | None = Field(None, max_length=255)
    discord_username: str | None = Field(None, max_length=255)
    platform: str = Field("discord", max_length=50)


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    square_customer_id: str | None = Field(None, max_length=100)
    discord_user_id: str | None = Field(None, max_length=255)
    discord_username: str | None = Field(None, max_length=255)
    platform: str | None = Field(None, max_length=50)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone: str | None = None
    name: str | None = None
    email: str | None = None
    square_customer_id: str | None = None
    discord_user_id: str | None = None
    discord_username: str | None = None
    platform: str
    created_at: datetime
    updated_at: datetime


class ConversationCreate(BaseModel):
    customer_id: str
    phone: str | None = None
    discord_user_id: str | None = None
    discord_channel_id: str | None = None
    discord_guild_id: str | None = None
    platform: str = "discord"
    status: str = "active"
    context: dict[str, Any] | None = None
    mentioned_books: list[str] | None = None


class ConversationUpdate(BaseModel):
    status: str | None = None
    context: dict[str, Any] | None = None
    mentioned_books: list[str] | None = None
    discord_channel_id: str | None = None
    discord_guild_id: str | None = None
    platform: str | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    phone: str | None = None
    discord_user_id: str | None = None
    discord_channel_id: str | None = None
    discord_guild_id: str | None = None
    platform: str
    status: str
    last_message_at: datetime
    created_at: datetime
    context: dict[str, Any] | None = None
    mentioned_books: list[str] | None = None


class MessageCreate(BaseModel):
    conversation_id: str
    direction: str = Field(..., pattern="^(inbound|outbound)$")
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    direction: str
    content: str
    timestamp: datetime


class BookCreate(BaseModel):
    isbn: str | None = Field(None, max_length=20)
    title: str = Field(..., min_length=1)
    author: str | None = None
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)
    publisher: str | None = None
    publication_date: datetime | None = None
    hardcover_id: str | None = Field(None, max_length=100)
    bookshop_url: str | None = None
    genre: str | None = Field(None, max_length=100)
    format: str | None = Field(None, max_length=50)
    page_count: int | None = Field(None, ge=0)


class BookUpdate(BaseModel):
    title: str | None = Field(None, min_length=1)
    author: str | None = None
    description: str | None = None
    price: Decimal | None = Field(None, ge=0)
    publisher: str | None = None
    publication_date: datetime | None = None
    hardcover_id: str | None = Field(None, max_length=100)
    bookshop_url: str | None = None
    genre: str | None = Field(None, max_length=100)
    format: str | None = Field(None, max_length=50)
    page_count: int | None = Field(None, ge=0)


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    isbn: str | None = None
    title: str
    author: str | None = None
    description: str | None = None
    price: Decimal | None = None
    publisher: str | None = None
    publication_date: datetime | None = None
    hardcover_id: str | None = None
    bookshop_url: str | None = None
    genre: str | None = None
    format: str | None = None
    page_count: int | None = None
    created_at: datetime
    updated_at: datetime


class InventoryCreate(BaseModel):
    book_id: str
    location: str = Field(..., max_length=100)
    quantity: int = Field(..., ge=0)
    reserved: int = Field(0, ge=0)
    price: Decimal | None = Field(None, ge=0)
    available: bool = True


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(None, ge=0)
    reserved: int | None = Field(None, ge=0)
    price: Decimal | None = Field(None, ge=0)
    available: bool | None = None


class InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    book_id: str
    location: str
    quantity: int
    reserved: int
    price: Decimal | None = None
    available: bool
    last_updated: datetime


# Database Session Management
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    init_database()  # Ensure database is initialized
    if AsyncSessionLocal is None:
        logger.error("Database not initialized: AsyncSessionLocal is None")
        raise RuntimeError("Database not initialized")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session():
    """Get database session as a context manager for background tasks."""
    init_database()  # Ensure database is initialized
    if AsyncSessionLocal is None:
        logger.error("Database not initialized: AsyncSessionLocal is None")
        raise RuntimeError("Database not initialized")

    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    init_database()  # Ensure database is initialized
    if engine is None:
        logger.error("Database engine not initialized: engine is None")
        raise RuntimeError("Database engine not initialized")

    # Test connection first
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def test_db_connection():
    """Test database connection and return status."""
    try:
        init_database()
        if engine is None:
            logger.error("Database engine not initialized: engine is None")
            raise RuntimeError("Database engine not initialized")

        async with engine.begin() as conn:
            result = await conn.execute(func.now())
            timestamp = result.scalar()
            logger.info(f"Database connection successful. Server time: {timestamp}")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def close_db():
    """Close database connections."""
    if engine is not None:
        await engine.dispose()
        logger.info("Database connections closed")


# Supabase-specific utilities
def is_supabase_url(url: str) -> bool:
    """Check if the database URL is for Supabase."""
    return "supabase.co" in url


def get_supabase_project_ref(url: str) -> str | None:
    """Extract Supabase project reference from URL."""
    if not is_supabase_url(url):
        return None

    # Extract project ref from URL like: db.abcdefgh12345678.supabase.co
    try:
        parts = url.split("@")[1].split(".supabase.co")[0]
        return parts.split("db.")[1]
    except (IndexError, AttributeError):
        return None


# Enhanced CRUD Operations with better error handling
async def create_customer(db: AsyncSession, customer: CustomerCreate) -> Customer:
    """Create a new customer."""
    try:
        db_customer = Customer(**customer.model_dump())
        db.add(db_customer)
        await db.commit()
        await db.refresh(db_customer)
        return db_customer
    except Exception as e:
        await db.rollback()
        raise e


async def get_customer_by_phone(db: AsyncSession, phone: str) -> Customer | None:
    """Get customer by phone number."""
    try:
        from sqlalchemy import select

        result = await db.execute(select(Customer).where(Customer.phone == phone))
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching customer by phone {phone}: {e}")
        return None


async def get_customer_by_discord_id(
    db: AsyncSession, discord_user_id: str
) -> Customer | None:
    """Get customer by Discord user ID."""
    try:
        from sqlalchemy import select

        result = await db.execute(
            select(Customer).where(Customer.discord_user_id == discord_user_id)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching customer by Discord ID {discord_user_id}: {e}")
        return None


async def create_conversation(
    db: AsyncSession, conversation: ConversationCreate
) -> Conversation:
    """Create a new conversation."""
    try:
        db_conversation = Conversation(**conversation.model_dump())
        db.add(db_conversation)
        await db.commit()
        await db.refresh(db_conversation)
        return db_conversation
    except Exception as e:
        await db.rollback()
        raise e


async def get_active_conversation(
    db: AsyncSession,
    identifier: str,
    platform: str = "sms",
    channel_id: str | None = None,
) -> Conversation | None:
    """Get active conversation for a phone number or Discord user ID."""
    try:
        from sqlalchemy import select

        if platform == "discord":
            # For Discord, filter by both user ID and channel ID to ensure conversation isolation
            query = (
                select(Conversation)
                .where(Conversation.discord_user_id == identifier)
                .where(Conversation.status == "active")
            )

            if channel_id:
                query = query.where(Conversation.discord_channel_id == channel_id)

            query = query.order_by(Conversation.created_at.desc())
            result = await db.execute(query)
        else:
            result = await db.execute(
                select(Conversation)
                .where(Conversation.phone == identifier)
                .where(Conversation.status == "active")
                .order_by(Conversation.created_at.desc())
            )
        return result.scalars().first()
    except Exception as e:
        logger.error(
            f"Error fetching active conversation for {platform} identifier {identifier}: {e}"
        )
        return None


async def add_message(db: AsyncSession, message: MessageCreate) -> Message:
    """Add a message to a conversation."""
    try:
        db_message = Message(**message.model_dump())
        db.add(db_message)

        # Update conversation's last_message_at
        from sqlalchemy import update

        await db.execute(
            update(Conversation)
            .where(Conversation.id == message.conversation_id)
            .values(last_message_at=datetime.now(UTC))
        )

        await db.commit()
        await db.refresh(db_message)
        return db_message
    except Exception as e:
        await db.rollback()
        raise e


async def get_conversation_messages(
    db: AsyncSession, conversation_id: str, limit: int = 10
) -> list[Message]:
    """Get recent messages from a conversation."""
    try:
        from sqlalchemy import select

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error fetching messages for conversation {conversation_id}: {e}")
        return []


async def search_books(db: AsyncSession, query: str, limit: int = 10) -> list[Book]:
    """Search books by title or author."""
    try:
        from sqlalchemy import or_, select

        result = await db.execute(
            select(Book)
            .where(or_(Book.title.ilike(f"%{query}%"), Book.author.ilike(f"%{query}%")))
            .limit(limit)
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error searching books with query '{query}': {e}")
        return []


# Database Cleanup Functions
async def cleanup_old_conversations(
    db: AsyncSession,
    days_old: int = 30,
    keep_recent_messages: int = 5,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Clean up old conversations and messages to prevent database clutter.

    Args:
        db: Database session
        days_old: Delete conversations older than this many days
        keep_recent_messages: Keep this many recent messages per conversation
        dry_run: Run the deletes to get exact counts, then roll back

    Returns:
        Tuple of (conversations_deleted, messages_deleted)
    """
    try:
        from datetime import timedelta

        from sqlalchemy import delete, select

        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

        old_conversation_ids_query = select(Conversation.id).where(
            Conversation.created_at < cutoff_date
        )

        # Messages go first so the conversation delete doesn't hit the FK.
        result = await db.execute(
            delete(Message).where(
                Message.conversation_id.in_(old_conversation_ids_query)
            )
        )
        messages_deleted = result.rowcount

        result = await db.execute(
            delete(Conversation).where(Conversation.id.in_(old_conversation_ids_query))
        )
        conversations_deleted = result.rowcount

        # Conversations we're keeping still get trimmed to their N newest
        # messages. Ranking in one window query avoids a round trip per
        # conversation; id breaks ties so identical timestamps are stable.
        if keep_recent_messages > 0:
            ranked_messages = (
                select(
                    Message.id.label("id"),
                    func.row_number()
                    .over(
                        partition_by=Message.conversation_id,
                        order_by=(Message.timestamp.desc(), Message.id.desc()),
                    )
                    .label("rank"),
                )
                .where(
                    Message.conversation_id.in_(
                        select(Conversation.id).where(
                            Conversation.created_at >= cutoff_date
                        )
                    )
                )
                .subquery()
            )
            stale_message_ids = select(ranked_messages.c.id).where(
                ranked_messages.c.rank > keep_recent_messages
            )
            result = await db.execute(
                delete(Message).where(Message.id.in_(stale_message_ids))
            )
            messages_deleted += result.rowcount

        if dry_run:
            await db.rollback()
            logger.info(
                f"Cleanup dry run: would delete {conversations_deleted} "
                f"conversations and {messages_deleted} messages "
                f"(older than {days_old} days)"
            )
            return conversations_deleted, messages_deleted

        await db.commit()

        logger.info(
            f"Cleanup completed: {conversations_deleted} conversations and "
            f"{messages_deleted} messages deleted (older than {days_old} days)"
        )

        return conversations_deleted, messages_deleted

    except Exception as e:
        await db.rollback()
        logger.error(f"Error during conversation cleanup: {e}")
        raise e


async def cleanup_expired_rate_limits(db: AsyncSession, dry_run: bool = False) -> int:
    """Clean up expired rate limit records."""
    try:
        from sqlalchemy import delete

        # Delete expired rate limits
        delete_query = delete(RateLimit).where(RateLimit.expires_at < datetime.now(UTC))
        result = await db.execute(delete_query)
        deleted_count = result.rowcount

        if dry_run:
            await db.rollback()
            logger.info(
                f"Rate limit dry run: would delete {deleted_count} expired records"
            )
            return deleted_count

        await db.commit()

        logger.info(f"Cleaned up {deleted_count} expired rate limit records")
        return deleted_count

    except Exception as e:
        await db.rollback()
        logger.error(f"Error during rate limit cleanup: {e}")
        raise e


async def cleanup_database(
    db: AsyncSession,
    conversation_days_old: int = 30,
    keep_recent_messages: int = 5,
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Perform comprehensive database cleanup.

    Args:
        db: Database session
        conversation_days_old: Delete conversations older than this many days
        keep_recent_messages: Keep this many recent messages per conversation
        dry_run: Report what would be deleted without persisting anything.
            Counts come from real deletes that are then rolled back, so they
            match an immediate real run exactly. The rollback expires any ORM
            instances already loaded in this session.

    Returns:
        Dict with cleanup statistics
    """
    try:
        # Cleanup conversations and messages
        conversations_deleted, messages_deleted = await cleanup_old_conversations(
            db, conversation_days_old, keep_recent_messages, dry_run=dry_run
        )

        # Cleanup expired rate limits
        rate_limits_deleted = await cleanup_expired_rate_limits(db, dry_run=dry_run)

        stats = {
            "conversations_deleted": conversations_deleted,
            "messages_deleted": messages_deleted,
            "rate_limits_deleted": rate_limits_deleted,
        }

        logger.info(f"Database cleanup completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")
        raise e


# Main function for testing
async def main():
    """Test database connection and setup."""
    print("🔍 Testing Marty Database Connection...")

    # Show current database URL (masked for security)
    db_url = DATABASE_URL
    if "supabase.co" in db_url:
        # Mask the password
        masked_url = db_url.split("://")[0] + "://postgres:***@" + db_url.split("@")[1]
        print(f"📋 Database URL: {masked_url}")
        print(f"🏗️  Supabase Project: {get_supabase_project_ref(db_url)}")
    else:
        print(f"📋 Database URL: {db_url}")

    # Test connection
    success = await test_db_connection()

    if success:
        print("🚀 Initializing database tables...")
        await init_db()
        print("✅ Database setup complete!")
    else:
        print("❌ Database setup failed!")
        return False

    return True


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
