# FoxCode Skill

Manage FoxCode Claude API proxy platform: check server status and query usage statistics.

## Setup

Create `config.json` with your credentials:
```json
{
  "email": "your@email.com",
  "password": "yourpassword"
}
```

The skill will automatically handle JWT token caching in `data/token.json`.

## Commands

### Server Status

Check the public server status from https://status.rjj.cc/status/foxcode

```bash
python3 scripts/check_status.py
```

Output includes:
- Overall server status (正常/部分服务降级/异常)
- Per-group status (Claude Code, Codex, Gemini)
- 24h uptime percentage for each monitor
- Link to the full status page

**Options:**
- `--json` - Output raw JSON format

### Usage & Quota

#### `quota` - Quick Quota Check
Shows remaining quota in one line format.

```bash
python3 scripts/usage.py quota
# Output: 剩余: 170.59M / 520.00M  (已用 67.2%)
```

#### `status` - Complete Status Overview
Shows comprehensive status including packages, multiplier, and model usage.

```bash
python3 scripts/usage.py status
```

Output includes:
- Quota overview (remaining/total/used percentage)
- Package details
- Current rate multiplier
- Model usage summary

#### `models` - Usage by Model
Detailed breakdown of usage statistics per model.

```bash
python3 scripts/usage.py models
```

Shows for each model:
- Request count
- Total tokens consumed
- Total cost

#### `trend` - 24h Usage Trend
Hourly usage trend for the last 24 hours.

```bash
python3 scripts/usage.py trend
python3 scripts/usage.py trend --model claude-3-sonnet
```

Options:
- `--model MODEL` - Filter by specific model

#### `records` - Usage Records
Paginated list of individual usage records.

```bash
python3 scripts/usage.py records
python3 scripts/usage.py records --page 2 --size 20
python3 scripts/usage.py records --model claude-3-opus
```

Options:
- `--page N` - Page number (default: 1)
- `--size N` - Records per page (default: 10)
- `--model MODEL` - Filter by specific model

#### `login` - Manual Token Refresh
Force refresh the authentication token.

```bash
python3 scripts/usage.py login
```

### Global Options

All commands support:
- `--json` - Output raw JSON instead of formatted text

## Authentication

The skill uses JWT token authentication:

1. Reads credentials from `config.json`
2. Caches JWT token in `data/token.json` with expiration
3. Automatically refreshes expired tokens
4. Handles authentication errors gracefully

## API Endpoints Used

### Status API
- `GET https://status.rjj.cc/status/foxcode` - Status page HTML (parses preloadData)
- `GET https://status.rjj.cc/api/status-page/heartbeat/foxcode` - Heartbeat data

### Usage API
- `POST /api/auth/login` - Authentication
- `GET /api/user/dashboard` - Quota overview
- `GET /api/user/quota/usage-statistics` - Model usage stats
- `GET /api/user/quota/usage-chart` - 24h trend data
- `GET /api/user/quota/usage` - Usage records (paginated)
- `GET /api/user/quota/multiplier` - Current rate multiplier

## Error Handling

- Missing config file: Clear error message with setup instructions
- Invalid credentials: Specific 401 error handling
- Network errors: Graceful failure with error details
- Token expiration: Automatic re-authentication
- JS-rendered status page: Parses embedded JSON from HTML

## Dependencies

Pure Python standard library only:
- `urllib.request` - HTTP requests
- `json` - JSON parsing
- `os`, `sys` - System utilities
- `time`, `datetime` - Time handling
- `argparse` - Command line parsing
- `re` - Regular expressions

No external dependencies required.
