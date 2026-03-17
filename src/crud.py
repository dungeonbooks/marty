"""
CRUD operations for Marty Bookstore Chatbot.
Provides async database operations for all models.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import (
    Book,
    BookCreate,
    BookUpdate,
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    Customer,
    CustomerCreate,
    CustomerUpdate,
    Inventory,
    InventoryCreate,
    Message,
    MessageCreate,
    RateLimit,
)


class CustomerCRUD:
    """CRUD operations for Customer model."""

    @staticmethod
    async def create(db: AsyncSession, customer: CustomerCreate) -> Customer:
        """Create a new customer."""
        db_customer = Customer(
            phone=customer.phone,
            name=customer.name,
            email=customer.email,
            square_customer_id=customer.square_customer_id,
        )
        db.add(db_customer)
        await db.commit()
        await db.refresh(db_customer)
        return db_customer

    @staticmethod
    async def get_by_id(db: AsyncSession, customer_id: str) -> Customer | None:
        """Get customer by ID."""
        stmt = select(Customer).where(Customer.id == customer_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_phone(db: AsyncSession, phone: str) -> Customer | None:
        """Get customer by phone number."""
        stmt = select(Customer).where(Customer.phone == phone)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_square_id(db: AsyncSession, square_id: str) -> Customer | None:
        """Get customer by Square customer ID."""
        stmt = select(Customer).where(Customer.square_customer_id == square_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession, customer_id: str, customer_update: CustomerUpdate
    ) -> Customer | None:
        """Update customer by ID."""
        stmt = (
            update(Customer)
            .where(Customer.id == customer_id)
            .values(
                **{
                    k: v
                    for k, v in customer_update.model_dump().items()
                    if v is not None
                },
                updated_at=datetime.now(UTC),
            )
            .returning(Customer)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def delete(db: AsyncSession, customer_id: str) -> bool:
        """Delete customer by ID."""
        stmt = delete(Customer).where(Customer.id == customer_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def list_customers(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Customer]:
        """List customers with pagination."""
        stmt = (
            select(Customer)
            .offset(skip)
            .limit(limit)
            .order_by(Customer.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()


class ConversationCRUD:
    """CRUD operations for Conversation model."""

    @staticmethod
    async def create(
        db: AsyncSession, conversation: ConversationCreate
    ) -> Conversation:
        """Create a new conversation."""
        db_conversation = Conversation(
            customer_id=conversation.customer_id,
            phone=conversation.phone,
            status=conversation.status,
            context=conversation.context,
            mentioned_books=conversation.mentioned_books,
        )
        db.add(db_conversation)
        await db.commit()
        await db.refresh(db_conversation)
        return db_conversation

    @staticmethod
    async def get_by_id(db: AsyncSession, conversation_id: str) -> Conversation | None:
        """Get conversation by ID with related messages."""
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_by_phone(db: AsyncSession, phone: str) -> Conversation | None:
        """Get active conversation by phone number."""
        stmt = (
            select(Conversation)
            .where(and_(Conversation.phone == phone, Conversation.status == "active"))
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.last_message_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_recent_messages(
        db: AsyncSession, conversation_id: str, limit: int = 10
    ) -> list[Message]:
        """Get recent messages for a conversation."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession, conversation_id: str, conversation_update: ConversationUpdate
    ) -> Conversation | None:
        """Update conversation by ID."""
        update_data = {
            k: v for k, v in conversation_update.model_dump().items() if v is not None
        }
        update_data["last_message_at"] = datetime.now(UTC)

        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(**update_data)
            .returning(Conversation)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def add_mentioned_book(
        db: AsyncSession, conversation_id: str, book_id: str
    ) -> Conversation | None:
        """Add a book to mentioned books list."""
        # First get the current conversation
        conversation = await ConversationCRUD.get_by_id(db, conversation_id)
        if not conversation:
            return None

        mentioned_books = conversation.mentioned_books or []
        if book_id not in mentioned_books:
            mentioned_books.append(book_id)

        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                mentioned_books=mentioned_books,
                last_message_at=datetime.now(UTC),
            )
            .returning(Conversation)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def end_conversation(
        db: AsyncSession, conversation_id: str
    ) -> Conversation | None:
        """End a conversation by setting status to 'ended'."""
        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(status="ended", last_message_at=datetime.now(UTC))
            .returning(Conversation)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()


class MessageCRUD:
    """CRUD operations for Message model."""

    @staticmethod
    async def create(db: AsyncSession, message: MessageCreate) -> Message:
        """Create a new message."""
        db_message = Message(
            conversation_id=message.conversation_id,
            direction=message.direction,
            content=message.content,
        )
        db.add(db_message)
        await db.commit()
        await db.refresh(db_message)

        # Update conversation last_message_at
        update_stmt = (
            update(Conversation)
            .where(Conversation.id == message.conversation_id)
            .values(last_message_at=datetime.now(UTC))
        )
        await db.execute(update_stmt)

        return db_message

    @staticmethod
    async def get_by_id(db: AsyncSession, message_id: str) -> Message | None:
        """Get message by ID."""
        stmt = select(Message).where(Message.id == message_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_conversation(
        db: AsyncSession, conversation_id: str, skip: int = 0, limit: int = 50
    ) -> list[Message]:
        """Get messages for a conversation."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


class BookCRUD:
    """CRUD operations for Book model."""

    @staticmethod
    async def create(db: AsyncSession, book: BookCreate) -> Book:
        """Create a new book."""
        db_book = Book(
            isbn=book.isbn,
            title=book.title,
            author=book.author,
            description=book.description,
            price=book.price,
            publisher=book.publisher,
            publication_date=book.publication_date,
            hardcover_id=book.hardcover_id,
            bookshop_url=book.bookshop_url,
            genre=book.genre,
            format=book.format,
            page_count=book.page_count,
        )
        db.add(db_book)
        await db.commit()
        await db.refresh(db_book)
        return db_book

    @staticmethod
    async def get_by_id(db: AsyncSession, book_id: str) -> Book | None:
        """Get book by ID with inventory."""
        stmt = (
            select(Book).where(Book.id == book_id).options(selectinload(Book.inventory))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_isbn(db: AsyncSession, isbn: str) -> Book | None:
        """Get book by ISBN."""
        stmt = select(Book).where(Book.isbn == isbn)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_hardcover_id(db: AsyncSession, hardcover_id: str) -> Book | None:
        """Get book by Hardcover API ID."""
        stmt = select(Book).where(Book.hardcover_id == hardcover_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def search_books(
        db: AsyncSession, query: str, skip: int = 0, limit: int = 20
    ) -> list[Book]:
        """Search books by title or author."""
        search_pattern = f"%{query}%"
        stmt = (
            select(Book)
            .where(
                or_(Book.title.ilike(search_pattern), Book.author.ilike(search_pattern))
            )
            .order_by(Book.title)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession, book_id: str, book_update: BookUpdate
    ) -> Book | None:
        """Update book by ID."""
        stmt = (
            update(Book)
            .where(Book.id == book_id)
            .values(
                **{k: v for k, v in book_update.model_dump().items() if v is not None},
                updated_at=datetime.now(UTC),
            )
            .returning(Book)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def delete(db: AsyncSession, book_id: str) -> bool:
        """Delete book by ID."""
        stmt = delete(Book).where(Book.id == book_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0


class InventoryCRUD:
    """CRUD operations for Inventory model."""

    @staticmethod
    async def create(db: AsyncSession, inventory: InventoryCreate) -> Inventory:
        """Create a new inventory record."""
        db_inventory = Inventory(
            book_id=inventory.book_id,
            location=inventory.location,
            quantity=inventory.quantity,
            reserved=inventory.reserved,
            price=inventory.price,
            available=inventory.available,
        )
        db.add(db_inventory)
        await db.commit()
        await db.refresh(db_inventory)
        return db_inventory

    @staticmethod
    async def get_by_book_and_location(
        db: AsyncSession, book_id: str, location: str
    ) -> Inventory | None:
        """Get inventory for a specific book and location."""
        stmt = select(Inventory).where(
            and_(Inventory.book_id == book_id, Inventory.location == location)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_book(db: AsyncSession, book_id: str) -> list[Inventory]:
        """Get all inventory records for a book."""
        stmt = select(Inventory).where(Inventory.book_id == book_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_quantity(
        db: AsyncSession,
        inventory_id: str,
        quantity: int,
        reserved: int | None = None,
    ) -> Inventory | None:
        """Update inventory quantity."""
        update_data = {"quantity": quantity, "last_updated": datetime.now(UTC)}
        if reserved is not None:
            update_data["reserved"] = reserved

        stmt = (
            update(Inventory)
            .where(Inventory.id == inventory_id)
            .values(**update_data)
            .returning(Inventory)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def check_availability(
        db: AsyncSession, book_id: str, location: str, quantity: int = 1
    ) -> bool:
        """Check if book is available in requested quantity."""
        stmt = select(Inventory).where(
            and_(
                Inventory.book_id == book_id,
                Inventory.location == location,
                Inventory.available,
                Inventory.quantity >= (Inventory.reserved + quantity),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def reserve_inventory(
        db: AsyncSession, book_id: str, location: str, quantity: int
    ) -> Inventory | None:
        """Reserve inventory for an order."""
        inventory = await InventoryCRUD.get_by_book_and_location(db, book_id, location)
        if not inventory or inventory.quantity < (inventory.reserved + quantity):
            return None

        stmt = (
            update(Inventory)
            .where(Inventory.id == inventory.id)
            .values(
                reserved=inventory.reserved + quantity,
                last_updated=datetime.now(UTC),
            )
            .returning(Inventory)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()


class RateLimitCRUD:
    """CRUD operations for Rate Limit model."""

    @staticmethod
    async def create(
        db: AsyncSession, identifier: str, limit_type: str, window_minutes: int = 60
    ) -> RateLimit:
        """Create a new rate limit record."""
        now = datetime.now(UTC)
        db_rate_limit = RateLimit(
            identifier=identifier,
            limit_type=limit_type,
            count=1,
            window_start=now,
            expires_at=now + timedelta(minutes=window_minutes),
        )
        db.add(db_rate_limit)
        await db.commit()
        await db.refresh(db_rate_limit)
        return db_rate_limit

    @staticmethod
    async def get_current_limit(
        db: AsyncSession, identifier: str, limit_type: str
    ) -> RateLimit | None:
        """Get current rate limit for identifier and type."""
        now = datetime.now(UTC)
        stmt = select(RateLimit).where(
            and_(
                RateLimit.identifier == identifier,
                RateLimit.limit_type == limit_type,
                RateLimit.expires_at > now,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def increment_count(db: AsyncSession, rate_limit_id: str) -> RateLimit | None:
        """Increment rate limit count."""
        stmt = (
            update(RateLimit)
            .where(RateLimit.id == rate_limit_id)
            .values(count=RateLimit.count + 1)
            .returning(RateLimit)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def cleanup_expired(db: AsyncSession) -> int:
        """Clean up expired rate limit records."""
        now = datetime.now(UTC)
        stmt = delete(RateLimit).where(RateLimit.expires_at <= now)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def check_rate_limit(
        db: AsyncSession,
        identifier: str,
        limit_type: str,
        max_count: int,
        window_minutes: int = 60,
    ) -> tuple[bool, RateLimit | None]:
        """Check if identifier is within rate limit."""
        # First, clean up expired records
        await RateLimitCRUD.cleanup_expired(db)

        # Check current limit
        current_limit = await RateLimitCRUD.get_current_limit(
            db, identifier, limit_type
        )

        if not current_limit:
            # No current limit, create new one
            new_limit = await RateLimitCRUD.create(
                db, identifier, limit_type, window_minutes
            )
            return True, new_limit
        elif current_limit.count >= max_count:
            # Rate limit exceeded
            return False, current_limit
        else:
            # Increment count
            updated_limit = await RateLimitCRUD.increment_count(db, current_limit.id)
            return True, updated_limit
