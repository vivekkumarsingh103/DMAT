# 🔍 Telegram Auto-Filter Bot

A powerful media indexing bot that automatically filters and delivers files from connected channels based on user queries, with support for manual filters, IMDB integration, and admin controls.

## 🌟 Features

- **Auto-File Indexing**: Scans channels and indexes files with metadata
- **Smart Search**: `/search Avengers 1080p` or just type keywords in groups
- **Quality Filters**: Auto-detects 480p/720p/1080p from filenames
- **Manual Filters**: `/filter keyword` + reply to file
- **IMDB Integration**: `/imdb Inception` fetches movie details
- **Admin Tools**: Ban users, broadcast messages, manage channels
- **Custom Thumbnails**: Set per-file thumbnails with `/set_thumb`

## 🚀 Quick Setup

### Prerequisites
- Python 3.8+
- MongoDB Atlas (Free tier)
- Telegram API ID & Hash

### Installation
```bash
# Clone repo
git clone https://github.com/your-repo/autofilter-bot.git
cd autofilter-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp sample.env .env
nano .env  # Fill your credentials
