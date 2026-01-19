# Candidate Bot - AI Coding Instructions

## Project Overview
Candidate Bot is a Telegram notification service that monitors Google Sheets for new job candidates and sends daily reminders to recruiters about upcoming start dates. The bot runs as a background service with hourly checks using APScheduler.

## Architecture

### Component Structure
- **`main.py`**: Core `CandidateBot` class orchestrating the workflow (async check loop, scheduler integration)
- **`google_sheets.py`**: `GoogleSheetsAPI` class handling Sheets API authentication (OAuth2 + Service Account fallback) and data extraction with flexible date parsing
- **`telegram_bot.py`**: `TelegramBot` class managing async message delivery via python-telegram-bot
- **`database.py`**: `Database` class providing SQLite persistence for candidates and reminder tracking
- **`config.py`**: Environment-based configuration loader with column indices mapping

### Data Flow
1. **Ingestion**: `GoogleSheetsAPI.get_candidates()` reads from all sheets, parses flexible date formats, and generates unique IDs per row
2. **Deduplication**: `Database.candidate_exists()` checks by candidate ID (`{sheet_name}_{row_number}`)
3. **Reminder Logic**: `CandidateBot._should_send_reminder()` identifies candidates with start dates tomorrow
4. **Dispatch**: `TelegramBot.send_reminder()` sends HTML-formatted messages to recruiter (custom chat ID or default)
5. **Tracking**: `Database.mark_reminder_sent()` prevents duplicate reminders

## Critical Patterns & Conventions

### Async/Scheduling
- **Blocking main loop**: `main.py` runs `asyncio.run()` in a blocking while loop; scheduler runs in background thread
- **Wrapper pattern**: `_run_async_job()` bridges APScheduler's sync interface with async code
- **First check**: Immediate check on startup before scheduler interval begins

### Date Handling
- **Multi-format parsing** in `GoogleSheetsAPI._parse_date()`: supports `дд.мм.гггг`, `дд.гг`, `YYYY-MM-DD`, `DD/MM/YYYY`
- **Reminder window**: Exactly 24 hours before (tomorrow check), not "day before" range
- **Column mapping**: Uses 0-indexed positions (A=0, L=11, M=12, Q=16) defined in `config.COLUMNS`

### Error Handling & Logging
- Logs include emoji prefixes for status visibility (✅, ❌, 🔍, ⏰, ⚠️, 📱)
- Exceptions logged but don't crash: continue processing next candidate
- Missing/invalid dates skip rows gracefully with debug logs

### Google Sheets Integration
- **Multi-sheet support**: Iterates all sheet names; unique IDs include sheet name to avoid collisions
- **Row validation**: Pads short rows to 17 columns; skips rows missing name/object/date
- **OAuth2 flow**: Saves token locally (`token.json`); falls back to Service Account if missing
- **Read-only scope**: Only `spreadsheets.readonly` permission required

### Telegram Messaging
- **HTML formatting** in reminder template (bold, line breaks)
- **Per-recruiter routing**: Uses candidate's `recruiter_id` column if present, otherwise default chat ID
- **Async send**: Non-blocking message dispatch

## Development Workflow

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Copy template
cp .env.example .env

# Populate .env with credentials:
# - GOOGLE_SHEETS_ID: from URL (docs.google.com/spreadsheets/d/{ID}/...)
# - TELEGRAM_BOT_TOKEN: from @BotFather
# - TELEGRAM_RECRUITER_CHAT_ID: from getUpdates API call
# - Credentials: Download from Google Cloud Console > Service Account

# Run service
python main.py
```

### Debugging
- Check logs for emoji markers (❌ indicates failures)
- Validate Google Sheets column indices in `config.COLUMNS`—misalignment silently skips rows
- Test date parsing: `GoogleSheetsAPI._parse_date()` handles edge cases (2-digit years, missing leading zeros)
- Verify database file exists (`candidates.db` created on first run)
- Monitor reminder trigger logic in `_should_send_reminder()`: only fires when `today + 1 day == start_date`

### Common Pitfalls
- **Row indexing**: Google Sheets API starts at row 1 (headers); data fetched from row 2 onward
- **Timezone**: Date comparison uses local `datetime.now()`, not UTC
- **OAuth credentials**: Must run initial auth flow locally to generate `token.json`
- **Column overflow**: Empty cells in trailing columns are omitted; code pads rows defensively

## Key Files by Role

| File | Responsibility |
|------|---|
| [main.py](main.py) | Scheduler setup, async orchestration, reminder window logic |
| [google_sheets.py](google_sheets.py) | Date parsing robustness, multi-sheet iteration, OAuth flow |
| [telegram_bot.py](telegram_bot.py) | Message templates, async dispatch, error recovery |
| [database.py](database.py) | Deduplication, state persistence, query optimization |
| [config.py](config.py) | Column mapping, env loading, constants |

## When Adding Features
1. **New Google Sheets columns**: Add to `COLUMNS` dict in config; update column range in `get_candidates()` range parameter
2. **New reminder types**: Extend `TelegramBot` with additional message methods; add logic branch in `check_reminders()`
3. **Database schema changes**: Update `init_db()` migration; handle backward compatibility for existing `candidates.db`
4. **Scheduling changes**: Modify scheduler job parameters in `CandidateBot.start()` (interval, cron, etc.)
