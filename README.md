# Papiermache

Papiermache is a command-line tool for academic publication management built on top of Zotero. It extends Zotero's functionality with
- automated PDF downloading
- DOI-based reference linking
- consistent author name normalization
- database backup

## Installation

### Prerequisites
- Python 3.8+
- local Zotero database (optional: API access)
- Environment variables configured (see Configuration)

### Quick Install
```bash
# Clone the repository
git clone https://github.com/yourusername/papiermache.git
cd papiermache

# Create and activate conda environment
conda create -n papiermache python=3.8 pip
conda activate papiermache

# Install dependencies
pip install -r requirements.txt
```

### Dependencies
```
prompt-toolkit    # Interactive CLI interface
pyzotero         # Zotero API client
beautifulsoup4   # HTML parsing for web scraping
requests         # HTTP requests
retrying         # Retry mechanisms for network operations
pysocks          # SOCKS proxy support
```

## Configuration

Create a `.env` file with required environment variables:
```bash
ZOTERO_USER_ID=your_user_id
ZOTERO_API_KEY=your_api_key
ZOTERO_DB_PATH=/path/to/zotero.sqlite
PAPER_PATH=/path/to/pdf/storage
```

## Usage Guide

### Interactive Mode
```bash
# Start interactive CLI
bash papiermache.sh

# Or directly with Python
conda activate papiermache
source .env
python cli.py
```

### Basic Commands

The CLI offers autocomplete for all commands, incl. paper names, collections and tags.
- `select [paper]|all|none|collection [coll] |tags [tags]` - select specific papers of groups of papers for further tasks
- `find [paper]` - find and select paper by name
- `add pdf|relations|link [paper]` - functions to perform, if executed without optional paper, executes function for `select`ed papers
- `fix path|names [paper]` as above

## Project Structure

```
papiermache/
├── cli.py                  # Main CLI entry point
├── papiermache.sh          # Shell script launcher
├── src/
│   ├── db.py              # Zotero database operations
│   ├── dispatcher.py      # Command dispatcher and core logic
│   ├── scihub.py          # PDF downloading functionality
│   ├── utils.py           # Utility functions
│   └── cermine-impl-*.jar # PDF text extraction tool
├── nubia/                 # Experimenting w/ alternative CLI interface
│   ├── cli_nubia.py       # Nubia-based CLI
│   └── commands/          # Command definitions
├── data/
│   └── blacklist.json     # Skip these in `fix names`
├── tests/
│   ├── test_db.py         # Database tests
│   ├── test_dispatcher.py # Dispatcher tests
│   └── test_utils.py      # Utility tests
└── requirements.txt       # Python dependencies
```

## Testing

```bash
# Run tests
python -m pytest
```
