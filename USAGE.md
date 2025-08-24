# Podcast Downloader - Usage Guide

## Installation

```bash
pip install -r requirements.txt
```

## Basic Usage

### 1. Download from RSS Feed
```bash
python podcast_downloader.py "https://example.com/podcast.rss"
```

### 2. Download from Apple Podcasts
```bash
python podcast_downloader.py "https://podcasts.apple.com/us/podcast/podcast-name/id123456789"
```

### 3. Download Multiple Episodes
```bash
python podcast_downloader.py -n 5 "https://podcasts.apple.com/us/podcast/podcast-name/id123456789"
```

### 4. Specify Output Directory
```bash
python podcast_downloader.py -o my_podcasts "https://example.com/podcast.rss"
```

## Authentication for Apple Podcasts

Some Apple Podcasts content may require authentication. Here are the options:

### Option 1: Use Browser Cookies (Recommended)

1. **Extract cookies from your browser:**
   ```bash
   python extract_cookies.py -d podcasts.apple.com -o apple_cookies.txt
   ```

2. **Use cookies with downloader:**
   ```bash
   python podcast_downloader.py --cookies apple_cookies.txt "https://podcasts.apple.com/us/podcast/podcast-name/id123456789"
   ```

### Option 2: Manual Cookie Export

1. Install a browser extension like "cookies.txt" 
2. Navigate to podcasts.apple.com and login
3. Export cookies to a file
4. Use the cookies file as shown above

### Option 3: Custom Headers

For advanced users, you can add custom headers:

```bash
python podcast_downloader.py --headers '{"Authorization": "Bearer your-token"}' "https://example.com/podcast.rss"
```

## Examples with Apple Podcasts

### Public Podcast (No Auth Required)
```bash
python podcast_downloader.py "https://podcasts.apple.com/us/podcast/the-daily/id1200361736"
```

### Subscription-Required Podcast (With Auth)
```bash
# First, extract cookies
python extract_cookies.py -o apple_cookies.txt

# Then download with cookies
python podcast_downloader.py --cookies apple_cookies.txt -n 3 "https://podcasts.apple.com/us/podcast/premium-podcast/id987654321"
```

## Important Notes

- **Respect Copyright**: Only download content you have the right to access
- **Rate Limiting**: The script includes delays between downloads to be respectful
- **Subscription Content**: Some podcasts require active subscriptions
- **Geographic Restrictions**: Some content may be region-locked
- **Terms of Service**: Always comply with Apple's terms of service

## Troubleshooting

### "Authentication required" Error
- Use browser cookies as shown above
- Ensure you're logged into Apple Podcasts in your browser
- Check if the podcast requires a subscription

### "Access forbidden" Error
- Content may be region-locked
- May require premium subscription
- Try accessing the podcast in your browser first

### "No RSS feed found" Error
- The podcast URL might be incorrect
- Some podcasts may not have public RSS feeds
- Try copying the URL directly from Apple Podcasts

### "Could not extract podcast ID" Error
- Make sure the URL contains 'id' followed by numbers
- Example correct format: `id1234567890`
- Copy URL directly from the podcast page

## Legal Disclaimer

This tool is for personal use only. Users are responsible for complying with:
- Copyright laws
- Terms of service of podcast platforms
- Content licensing agreements

Only download content you have legal access to.