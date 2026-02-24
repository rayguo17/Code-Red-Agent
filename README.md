# API Configuration Guide

## Setup Instructions

### 1. Create `.env` file
Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
```

Then edit `.env` and add your OpenRouter API key:

```
OPENROUTER_API_KEY=your_api_key_here
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

Or using conda:
```bash
conda env create -f environment.yml
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python main.py
```

## Security Notes
- **Never commit `.env` file** - It's already in `.gitignore`
- **Always use `.env.example`** as a template for other developers
- **Keep API keys private** - Only share through secure channels
- Use `os.getenv()` for all sensitive configuration

## Environment Variables
- `OPENROUTER_API_KEY` - Your OpenRouter API key for GPT-4o access
