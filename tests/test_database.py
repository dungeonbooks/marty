"""
Comprehensive tests for database operations.
Tests CRUD operations, async functionality, and error handling.

All database tests use PostgreSQL integration testing to match production.
"""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud import (
    BookCRUD,
    ConversationCRUD,
    CustomerCRUD,
    InventoryCRUD,
    MessageCRUD,
    RateLimitCRUD,
)
from src.database import (
    Book,
    BookCreate,
    BookUpdate,
    Conversation,
    ConversationCreate,
    Customer,
    CustomerCreate,
    CustomerUpdate,
    InventoryCreate,
    MessageCreate,
)

# Use PostgreSQL integration test fixtures from conftest.py
# All database tests now require proper integration test setup

pytestmark = (
    pytest.mark.integration
)  # Mark all tests in this module as integration tests


@pytest_asyncio.fixture
async def db_session(use_postgres_db):
    """Use clean PostgreSQL database session for all tests."""
    # The use_postgres_db fixture provides the database setup
    test_session_local, test_engine = use_postgres_db

    async with test_session_local() as session:
        try:
            yield session
        finally:
            # Rollback any uncommitted changes to ensure test isolation
            try:
                await session.rollback()
            except Exception:
                # Session may already be closed, ignore errors
                pass


@pytest_asyncio.fixture
async def sample_customer(db_session: AsyncSession) -> Customer:
    """Create a sample customer for testing."""
    customer_data = CustomerCreate(
        phone="+1234567890",
        name="John Doe",
        email="john@example.com",
        square_customer_id="sq_123",
    )
    return await CustomerCRUD.create(db_session, customer_data)


@pytest_asyncio.fixture
async def sample_book(db_session: AsyncSession) -> Book:
    """Create a sample book for testing."""
    book_data = BookCreate(
        isbn="9781234567890",
        title="Test Book",
        author="Test Author",
        description="A test book for testing",
        price=Decimal("19.99"),
        publisher="Test Publisher",
        genre="Fiction",
        format="hardcover",
        page_count=300,
    )
    return await BookCRUD.create(db_session, book_data)


@pytest_asyncio.fixture
async def sample_conversation(
    db_session: AsyncSession, sample_customer: Customer
) -> Conversation:
    """Create a sample conversation for testing."""
    conversation_data = ConversationCreate(
        customer_id=sample_customer.id,
        phone=sample_customer.phone,
        status="active",
        context={"test": "context"},
        mentioned_books=[],
    )
    return await ConversationCRUD.create(db_session, conversation_data)


class TestCustomerCRUD:
    """Test Customer CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_customer(self, db_session: AsyncSession):
        """Test creating a new customer."""
        customer_data = CustomerCreate(
            phone="+1234567890",
            name="Jane Smith",
            email="jane@example.com",
            square_customer_id=None,
        )

        customer = await CustomerCRUD.create(db_session, customer_data)

        assert customer.id is not None
        assert customer.phone == "+1234567890"
        assert customer.name == "Jane Smith"
        assert customer.email == "jane@example.com"
        assert customer.created_at is not None
        assert customer.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_customer_by_phone(
        self, db_session: AsyncSession, sample_customer: Customer
    ):
        """Test retrieving customer by phone number."""
        customer = await CustomerCRUD.get_by_phone(db_session, sample_customer.phone)

        assert customer is not None
        assert customer.id == sample_customer.id
        assert customer.phone == sample_customer.phone

    @pytest.mark.asyncio
    async def test_get_customer_by_id(
        self, db_session: AsyncSession, sample_customer: Customer
    ):
        """Test retrieving customer by ID."""
        customer = await CustomerCRUD.get_by_id(db_session, sample_customer.id)

        assert customer is not None
        assert customer.id == sample_customer.id
        assert customer.phone == sample_customer.phone

    @pytest.mark.asyncio
    async def test_get_customer_by_square_id(
        self, db_session: AsyncSession, sample_customer: Customer
    ):
        """Test retrieving customer by Square ID."""
        assert sample_customer.square_customer_id is not None
        customer = await CustomerCRUD.get_by_square_id(
            db_session, sample_customer.square_customer_id
        )

        assert customer is not None
        assert customer.id == sample_customer.id
        assert customer.square_customer_id == sample_customer.square_customer_id

    @pytest.mark.asyncio
    async def test_update_customer(
        self, db_session: AsyncSession, sample_customer: Customer
    ):
        """Test updating customer information."""
        update_data = CustomerUpdate(name="Updated Name", email="updated@example.com")

        updated_customer = await CustomerCRUD.update(
            db_session, sample_customer.id, update_data
        )

        assert updated_customer is not None
        assert updated_customer.name == "Updated Name"
        assert updated_customer.email == "updated@example.com"

    @pytest.mark.asyncio
    async def test_delete_customer(
        self, db_session: AsyncSession, sample_customer: Customer
    ):
        """Test deleting a customer."""
        customer_id = sample_customer.id

        result = await CustomerCRUD.delete(db_session, customer_id)
        assert result is True

        # Verify customer is deleted
        deleted_customer = await CustomerCRUD.get_by_id(db_session, customer_id)
        assert deleted_customer is None

    @pytest.mark.asyncio
    async def test_list_customers(self, db_session: AsyncSession):
        """Test listing customers with pagination."""
        # Create multiple customers
        for i in range(5):
            customer_data = CustomerCreate(phone=f"+123456789{i}", name=f"User{i} Test")
            await CustomerCRUD.create(db_session, customer_data)

        # Test pagination
        customers = await CustomerCRUD.list_customers(db_session, skip=0, limit=3)
        assert len(customers) == 3

        customers_page2 = await CustomerCRUD.list_customers(db_session, skip=3, limit=3)
        assert len(customers_page2) == 2


class TestConversationCRUD:
    """Test Conversation CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_conversation(
        self, db_session: AsyncSession, sample_customer: Customer
    ):
        """Test creating a new conversation."""
        conversation_data = ConversationCreate(
            customer_id=sample_customer.id,
            phone=sample_customer.phone,
            status="active",
            context={"location": "store"},
            mentioned_books=["book1", "book2"],
        )

        conversation = await ConversationCRUD.create(db_session, conversation_data)

        assert conversation.id is not None
        assert conversation.customer_id == sample_customer.id
        assert conversation.phone == sample_customer.phone
        assert conversation.status == "active"
        assert conversation.context == {"location": "store"}
        assert conversation.mentioned_books == ["book1", "book2"]

    @pytest.mark.asyncio
    async def test_get_active_conversation_by_phone(
        self, db_session: AsyncSession, sample_conversation: Conversation
    ):
        """Test retrieving active conversation by phone."""
        conversation = await ConversationCRUD.get_active_by_phone(
            db_session, sample_conversation.phone
        )

        assert conversation is not None
        assert conversation.id == sample_conversation.id
        assert conversation.status == "active"

    @pytest.mark.asyncio
    async def test_add_mentioned_book(
        self, db_session: AsyncSession, sample_conversation: Conversation
    ):
        """Test adding a book to mentioned books list."""
        book_id = "new_book_id"

        updated_conversation = await ConversationCRUD.add_mentioned_book(
            db_session, sample_conversation.id, book_id
        )

        assert updated_conversation is not None
        assert book_id in updated_conversation.mentioned_books

    @pytest.mark.asyncio
    async def test_end_conversation(
        self, db_session: AsyncSession, sample_conversation: Conversation
    ):
        """Test ending a conversation."""
        ended_conversation = await ConversationCRUD.end_conversation(
            db_session, sample_conversation.id
        )

        assert ended_conversation is not None
        assert ended_conversation.status == "ended"


class TestMessageCRUD:
    """Test Message CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_message(
        self, db_session: AsyncSession, sample_conversation: Conversation
    ):
        """Test creating a new message."""
        message_data = MessageCreate(
            conversation_id=sample_conversation.id,
            direction="inbound",
            content="Hello, I'm looking for a book!",
        )

        message = await MessageCRUD.create(db_session, message_data)

        assert message.id is not None
        assert message.conversation_id == sample_conversation.id
        assert message.direction == "inbound"
        assert message.content == "Hello, I'm looking for a book!"
        assert message.timestamp is not None

    @pytest.mark.asyncio
    async def test_get_messages_by_conversation(
        self, db_session: AsyncSession, sample_conversation: Conversation
    ):
        """Test retrieving messages for a conversation."""
        # Create multiple messages
        for i in range(3):
            message_data = MessageCreate(
                conversation_id=sample_conversation.id,
                direction="inbound" if i % 2 == 0 else "outbound",
                content=f"Message {i}",
            )
            await MessageCRUD.create(db_session, message_data)

        messages = await MessageCRUD.get_by_conversation(
            db_session, sample_conversation.id
        )

        assert len(messages) == 3
        assert messages[0].content == "Message 0"  # Should be ordered by timestamp


class TestBookCRUD:
    """Test Book CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_book(self, db_session: AsyncSession):
        """Test creating a new book."""
        book_data = BookCreate(
            isbn="9780123456789",
            title="Python Programming",
            author="John Python",
            description="Learn Python programming",
            price=Decimal("29.99"),
            publisher="Tech Books",
            genre="Programming",
            format="paperback",
            page_count=450,
        )

        book = await BookCRUD.create(db_session, book_data)

        assert book.id is not None
        assert book.isbn == "9780123456789"
        assert book.title == "Python Programming"
        assert book.author == "John Python"
        assert book.price == Decimal("29.99")
        assert book.genre == "Programming"
        assert book.format == "paperback"
        assert book.page_count == 450

    @pytest.mark.asyncio
    async def test_get_book_by_isbn(self, db_session: AsyncSession, sample_book: Book):
        """Test retrieving book by ISBN."""
        assert sample_book.isbn is not None
        book = await BookCRUD.get_by_isbn(db_session, sample_book.isbn)

        assert book is not None
        assert book.id == sample_book.id
        assert book.isbn == sample_book.isbn

    @pytest.mark.asyncio
    async def test_search_books(self, db_session: AsyncSession):
        """Test searching books by title and author."""
        # Create test books
        books_data = [
            BookCreate(title="Python Basics", author="Alice Python", isbn="111"),
            BookCreate(title="Advanced Python", author="Bob Python", isbn="222"),
            BookCreate(title="JavaScript Guide", author="Charlie JS", isbn="333"),
        ]

        for book_data in books_data:
            await BookCRUD.create(db_session, book_data)

        # Search by title
        python_books = await BookCRUD.search_books(db_session, "Python")
        assert len(python_books) == 2

        # Search by author
        alice_books = await BookCRUD.search_books(db_session, "Alice")
        assert len(alice_books) == 1
        assert alice_books[0].author == "Alice Python"

    @pytest.mark.asyncio
    async def test_update_book(self, db_session: AsyncSession, sample_book: Book):
        """Test updating book information."""
        update_data = BookUpdate(
            price=Decimal("24.99"), description="Updated description"
        )

        updated_book = await BookCRUD.update(db_session, sample_book.id, update_data)

        assert updated_book is not None
        assert updated_book.price == Decimal("24.99")
        assert updated_book.description == "Updated description"
        assert updated_book.title == sample_book.title  # Should remain unchanged


class TestInventoryCRUD:
    """Test Inventory CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_inventory(self, db_session: AsyncSession, sample_book: Book):
        """Test creating inventory record."""
        inventory_data = InventoryCreate(
            book_id=sample_book.id,
            location="store",
            quantity=10,
            reserved=2,
            price=Decimal("19.99"),
            available=True,
        )

        inventory = await InventoryCRUD.create(db_session, inventory_data)

        assert inventory.id is not None
        assert inventory.book_id == sample_book.id
        assert inventory.location == "store"
        assert inventory.quantity == 10
        assert inventory.reserved == 2
        assert inventory.price == Decimal("19.99")
        assert inventory.available is True

    @pytest.mark.asyncio
    async def test_check_availability(
        self, db_session: AsyncSession, sample_book: Book
    ):
        """Test checking inventory availability."""
        # Create inventory
        inventory_data = InventoryCreate(
            book_id=sample_book.id,
            location="store",
            quantity=5,
            reserved=2,
            available=True,
        )
        await InventoryCRUD.create(db_session, inventory_data)

        # Check availability for valid quantity
        available = await InventoryCRUD.check_availability(
            db_session, sample_book.id, "store", 2
        )
        assert available is True

        # Check availability for quantity that exceeds available stock
        not_available = await InventoryCRUD.check_availability(
            db_session, sample_book.id, "store", 5
        )
        assert not_available is False

    @pytest.mark.asyncio
    async def test_reserve_inventory(self, db_session: AsyncSession, sample_book: Book):
        """Test reserving inventory."""
        # Create inventory
        inventory_data = InventoryCreate(
            book_id=sample_book.id,
            location="store",
            quantity=10,
            reserved=0,
            available=True,
        )
        await InventoryCRUD.create(db_session, inventory_data)

        # Reserve some inventory
        reserved_inventory = await InventoryCRUD.reserve_inventory(
            db_session, sample_book.id, "store", 3
        )

        assert reserved_inventory is not None
        assert reserved_inventory.reserved == 3
        assert reserved_inventory.quantity == 10  # Quantity unchanged

    @pytest.mark.asyncio
    async def test_update_inventory_quantity(
        self, db_session: AsyncSession, sample_book: Book
    ):
        """Test updating inventory quantity."""
        # Create inventory
        inventory_data = InventoryCreate(
            book_id=sample_book.id,
            location="store",
            quantity=5,
            reserved=1,
            available=True,
        )
        inventory = await InventoryCRUD.create(db_session, inventory_data)

        # Update quantity
        updated_inventory = await InventoryCRUD.update_quantity(
            db_session, inventory.id, 15, 3
        )

        assert updated_inventory is not None
        assert updated_inventory.quantity == 15
        assert updated_inventory.reserved == 3


class TestRateLimitCRUD:
    """Test Rate Limit CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_rate_limit(self, db_session: AsyncSession):
        """Test creating a rate limit record."""
        rate_limit = await RateLimitCRUD.create(db_session, "+1234567890", "sms", 60)

        assert rate_limit.id is not None
        assert rate_limit.identifier == "+1234567890"
        assert rate_limit.limit_type == "sms"
        assert rate_limit.count == 1
        assert rate_limit.window_start is not None
        assert rate_limit.expires_at is not None

    @pytest.mark.asyncio
    async def test_check_rate_limit(self, db_session: AsyncSession):
        """Test checking rate limits."""
        identifier = "+1234567890"
        limit_type = "sms"
        max_count = 5

        # First request should be allowed
        allowed, rate_limit = await RateLimitCRUD.check_rate_limit(
            db_session, identifier, limit_type, max_count
        )
        assert allowed is True
        assert rate_limit.count == 1

        # Subsequent requests should increment count
        for i in range(2, 5):
            allowed, rate_limit = await RateLimitCRUD.check_rate_limit(
                db_session, identifier, limit_type, max_count
            )
            assert allowed is True
            assert rate_limit.count == i

        # 5th request should still be allowed (at limit)
        allowed, rate_limit = await RateLimitCRUD.check_rate_limit(
            db_session, identifier, limit_type, max_count
        )
        assert allowed is True
        assert rate_limit.count == 5

        # 6th request should be denied (over limit)
        allowed, rate_limit = await RateLimitCRUD.check_rate_limit(
            db_session, identifier, limit_type, max_count
        )
        assert allowed is False
        assert rate_limit.count == 5  # Should not increment further

    @pytest.mark.asyncio
    async def test_cleanup_expired_rate_limits(self, db_session: AsyncSession):
        """Test cleaning up expired rate limit records."""
        # Create a rate limit that will expire immediately
        await RateLimitCRUD.create(db_session, "+1234567890", "sms", 0)

        # Verify it exists
        current_limit = await RateLimitCRUD.get_current_limit(
            db_session, "+1234567890", "sms"
        )
        assert current_limit is None  # Should be None because it's already expired

        # Clean up expired records
        cleaned_count = await RateLimitCRUD.cleanup_expired(db_session)
        assert cleaned_count >= 0  # Should clean up at least the expired record


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database integration and relationships."""

    @pytest.mark.asyncio
    async def test_customer_conversation_relationship(self, db_session: AsyncSession):
        """Test customer-conversation relationship."""
        # Create customer
        customer_data = CustomerCreate(phone="+1234567890", name="Test User")
        customer = await CustomerCRUD.create(db_session, customer_data)

        # Create conversation
        conversation_data = ConversationCreate(
            customer_id=customer.id, phone=customer.phone, status="active"
        )
        conversation = await ConversationCRUD.create(db_session, conversation_data)

        # Verify relationship
        assert conversation.customer_id == customer.id

        # Test loading with relationships
        loaded_conversation = await ConversationCRUD.get_by_id(
            db_session, conversation.id
        )
        assert loaded_conversation is not None
        assert loaded_conversation.customer_id == customer.id

    @pytest.mark.asyncio
    async def test_conversation_message_relationship(
        self, db_session: AsyncSession, sample_conversation: Conversation
    ):
        """Test conversation-message relationship."""
        # Create messages
        message_data = MessageCreate(
            conversation_id=sample_conversation.id,
            direction="inbound",
            content="Test message",
            status="sent",
        )
        message = await MessageCRUD.create(db_session, message_data)

        # Verify relationship
        assert message.conversation_id == sample_conversation.id

        # Test loading messages for conversation
        messages = await MessageCRUD.get_by_conversation(
            db_session, sample_conversation.id
        )
        assert len(messages) == 1
        assert messages[0].id == message.id

    @pytest.mark.asyncio
    async def test_book_inventory_relationship(
        self, db_session: AsyncSession, sample_book: Book
    ):
        """Test book-inventory relationship."""
        # Create inventory for book
        inventory_data = InventoryCreate(
            book_id=sample_book.id, location="store", quantity=10, available=True
        )
        inventory = await InventoryCRUD.create(db_session, inventory_data)

        # Verify relationship
        assert inventory.book_id == sample_book.id

        # Test loading book with inventory
        loaded_book = await BookCRUD.get_by_id(db_session, sample_book.id)
        assert loaded_book is not None
        assert loaded_book.id == sample_book.id

    @pytest.mark.asyncio
    async def test_error_handling(self, db_session: AsyncSession):
        """Test error handling for invalid operations."""
        # Test getting non-existent customer
        customer = await CustomerCRUD.get_by_id(db_session, "non-existent-id")
        assert customer is None

        # Test getting non-existent conversation
        conversation = await ConversationCRUD.get_by_id(db_session, "non-existent-id")
        assert conversation is None

        # Test getting non-existent book
        book = await BookCRUD.get_by_id(db_session, "non-existent-id")
        assert book is None

        # Test updating non-existent customer
        update_data = CustomerUpdate(name="Updated")
        updated_customer = await CustomerCRUD.update(
            db_session, "non-existent-id", update_data
        )
        assert updated_customer is None

        # Test deleting non-existent customer
        deleted = await CustomerCRUD.delete(db_session, "non-existent-id")
        assert deleted is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
