# Discord Bot Context & Progress

## Current Status

The Discord bot implementation is **functionally complete** and ready for testing. The main remaining work is Discord Developer Portal setup and some minor refinements.

## ✅ What's Already Implemented

### 1. Core Discord Bot (`src/discord_bot/bot.py`)
- Full Discord bot client with message processing
- Database integration with Discord user context
- Conversation history and state management
- Error handling with Marty's personality
- Uses existing AI client and conversation logic

### 2. Database Integration
- All Discord fields added to customers and conversations tables
- Migration complete (`65e621b64ab5_add_discord_support_to_customers_and_.py`)
- Platform-agnostic CRUD operations

### 3. AI Integration
- Discord-specific system prompt (`prompts/marty_discord_system_prompt.md`)
- Platform parameter handling in `ai_client.py`
- Uses existing hardcover API tool for book recommendations

### 4. Hardcover API & Affiliate Links
- Hardcover tool automatically generates bookshop.org affiliate links (ID: 108216)
- Two link types:
  - Direct links: `https://bookshop.org/a/108216/EAN` (preferred)
  - Search links: `https://bookshop.org/search?keywords={title}&aid=108216` (fallback)

## 📋 Current Todo List

1. **Discord bot setup** (in progress) - Create Discord application and get bot token
2. **Environment variables** - Add DISCORD_BOT_TOKEN, DISCORD_CLIENT_ID, DISCORD_GUILD_ID
3. **Discord formatters** - Create rich embeds/formatting (optional enhancement)
4. **Test bot functionality** - Full book recommendation flow in private server
5. **Slash commands** - Quick actions (optional)

## 🐛 Known Issues

### Affiliate Link Generation - RESOLVED ✅
**Problem**: Marty was providing search links instead of direct bookshop.org links

**Solution**: Using search links as primary approach since direct ISBN links may be international editions that don't exist on bookshop.org

**Current Format**: `https://bookshop.org/search?keywords=title&aid=108216`

**Root Cause**: Hardcover API provides international editions first, which often result in 404s on US-focused bookshop.org. The `links` field is always empty, and direct ISBN links from international editions don't work on bookshop.org.

**Code Location**: `src/tools/external/hardcover.py` - Simplified to use search links directly
```python
# Use search links as primary approach since direct ISBN links may be international editions
if book.get("title"):
    book["bookshop_link"] = generate_bookshop_search_link(book["title"])
```

## 🎯 Marty's Personality Refinements

### Recent Prompt Updates
- Added explicit guidance to keep responses short (1-3 sentences max)
- Emphasized chill, nonchalant vibe - avoid exclamation points
- Added "like texting a friend, not writing essays"

### System Prompt Location
`prompts/marty_discord_system_prompt.md` - Discord-specific version with rich formatting support

### Key Personality Traits
- Burnt-out tech worker who happens to be magical
- Lowercase, contractions, casual abbreviations (u, ur, bc, tbh)
- Give 1-3 book recs with brief context, don't oversell
- Natural wizard references when relevant
- Stay chill and understated

## 🔧 Technical Architecture

### Platform-Agnostic Design
Both SMS and Discord use the same:
- AI client and conversation logic
- Database models and CRUD operations
- Tool registry (hardcover API, book enricher)
- Customer identification and context management

### Discord-Specific Features
- Rich formatting support (**bold**, *italics*)
- No SMS character limits
- No 10DLC compliance needed
- Discord user context (user_id, username, channel_id, guild_id)

### RSS Feed Digest (`src/discord_bot/feeds.py`)
- Polls 3 RPG industry RSS feeds (Questing Beast, Sabre Games OSR News, Ten Foot Pole)
- Posts weekly digest to `#rpg-news` every Monday at 10am ET
- Custom parsing for Ten Foot Pole metadata (author, publisher, system, levels)
- Highlights "The Best" tagged reviews with ⭐
- Deduplicates via Redis to avoid reposting
- `!digest` command for manual testing (requires manage_channels permission)
- Requires `RPG_NEWS_CHANNEL_ID` env var

### File Structure
```
src/discord_bot/
├── __init__.py
├── bot.py              # Complete Discord bot implementation
├── embeds.py           # Rich embed formatting
├── feeds.py            # RSS feed aggregator for #rpg-news
└── mtg.py              # Magic: The Gathering card lookup

prompts/
└── marty_discord_system_prompt.md  # Discord-specific prompt

alembic/versions/
└── 65e621b64ab5_add_discord_support_to_customers_and_.py  # DB migration
```

## 🚀 Next Steps When Resuming

1. **Investigate affiliate link issue**:
   - Test what Hardcover API returns for book links
   - Debug `extract_and_replace_bookshop_link()` function
   - Ensure direct bookshop links are extracted properly

2. **Discord Developer Setup**:
   - Create Discord application at discord.com/developers/applications
   - Get bot token and client ID
   - Set bot permissions: Send Messages, Read Message History, Use Slash Commands

3. **Environment Configuration**:
   ```bash
   DISCORD_BOT_TOKEN=your_token_here
   DISCORD_CLIENT_ID=your_client_id_here
   DISCORD_GUILD_ID=your_test_server_id  # optional
   ```

4. **Testing**:
   - Create private Discord server
   - Test full book recommendation flow
   - Verify affiliate link generation
   - Test conversation history and state

## 💡 Key Insights

- The Discord bot reuses 95% of existing SMS infrastructure
- Main difference is response formatting (Discord allows rich text vs SMS plain text)
- Affiliate link generation is already built into hardcover tool
- Marty's personality is well-established in Discord prompt

## 🔗 Important Files to Reference

- `src/discord_bot/bot.py` - Main Discord bot implementation
- `prompts/marty_discord_system_prompt.md` - Discord personality/formatting
- `src/tools/external/hardcover.py` - Book search and affiliate links
- `src/ai_client.py` - Platform-specific prompt loading
- `DISCORD_BOT_PLAN.md` - Original implementation plan
