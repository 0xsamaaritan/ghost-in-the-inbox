# Ghost in the Inbox

A small Python script that scans your Gmail for account-related emails (welcome, verify, subscription, ...) and shows which services you have signed up for, grouped by category.

Use it to find forgotten accounts, clean up old signups, and see how big your online footprint is.

## Features

- Read-only: the mailbox is opened read-only and messages are never marked as read, moved or deleted
- Fetches only the `From` and `Date` headers, never email bodies
- Groups senders into 19 categories (AI tools, crypto, education, dev tools, shopping, and more)
- Shows email count and first/last seen dates per service, sorted by count
- Optional CSV export
- Credentials come from environment variables or a hidden prompt and are never stored

## Requirements

- Python 3.8+
- A Gmail account with 2-Step Verification enabled and IMAP turned on
- A Gmail [App Password](https://myaccount.google.com/apppasswords) (your normal password will not work)
- Optional: `tldextract` for accurate domain parsing

## Setup

```bash
git clone https://github.com/0xsamaaritan/ghost-in-the-inbox.git
cd ghost-in-the-inbox
pip install -r requirements.txt
```

## Usage

```bash
python footprint_scanner.py                       # Inbox, all matches
python footprint_scanner.py --all-mail            # search All Mail (includes archived)
python footprint_scanner.py --limit 500           # only the newest 500 matches
python footprint_scanner.py --csv footprint.csv   # also export to CSV
```

You will be prompted for your Gmail address and App Password. To skip the prompts, set environment variables first.

**Windows (Command Prompt)**
```
set GMAIL_USER=you@gmail.com
set GMAIL_APP_PASSWORD=yourapppassword
```

**macOS / Linux**
```bash
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="yourapppassword"
```

## Example output

```
📂 Crypto & Web3 (3):
  • binance.com  (15 emails, 2021-06 → 2025-02)
  • bscscan.com  (1 email, 2022-03 → 2022-03)

📂 Education & Learning (2):
  • cambly.com  (10 emails, 2023-01 → 2025-08)
  • alison.com  (2 emails, 2020-11 → 2021-01)
```

## How to read the results

The number next to each service is how many emails from that sender matched the search keywords. It is not the number of accounts, and not the total emails they sent.

- 1 email is usually a one-time signup, so it may be an old or forgotten account
- Many emails usually means an active account (or heavy marketing)
- A sender is not always an account: newsletters and promotions can match too

## Viewing results in the interactive dashboard

`index.html` turns the CSV export into a browsable dashboard — colorful category cards with counts, summary stats, and a sortable, searchable table. Click a category card to list every domain in it. It runs entirely in your browser; nothing is uploaded anywhere, so it's safe to open even on the hosted version.

**Live dashboard:** https://ghost-in-the-inbox.vercel.app
**Want to see it first?** Drop the included `sample_footprint.csv` (fake data) onto the page to preview how it looks.

**Locally, right after scanning:**

1. Run the scanner with `--csv` to produce the file:
   ```bash
   python footprint_scanner.py --csv footprint.csv
   ```
2. Double-click `index.html` (or right-click → Open with → your browser) to open it.
3. Drag `footprint.csv` onto the page, or click the drop area and pick the file from the file browser.
4. The dashboard renders immediately. Click a category card and use the search box to filter, and click any column header in the table to sort by it.
5. Click **LOAD DIFFERENT FILE** to load another CSV without refreshing the page.

**Using the hosted version instead of opening the file locally:**

If you've deployed `index.html` to GitHub Pages, Vercel, or Netlify (see below), you can open that live link instead and drop your `footprint.csv` into it the same way. The file never leaves your browser — it's not sent to any server — so this is safe to do even though the page is public.

### Hosting the dashboard for free

- **GitHub Pages:** in this repo, go to Settings → Pages → Source: "Deploy from a branch" → branch `main`, folder `/ (root)` → Save. Your dashboard appears at `https://0xsamaaritan.github.io/ghost-in-the-inbox/`.
- **Vercel:** sign in with GitHub → "Add New → Project" → select this repo → Deploy (no build settings needed).
- **Netlify:** sign in with GitHub → "Add new site → Import an existing project" → select this repo → Deploy.

## Customizing

Edit these at the top of `footprint_scanner.py`:

- `SUBJECT_KEYWORDS` controls which emails are searched
- `CATEGORY_KEYWORDS` controls categories. Keywords match a domain's main name exactly (`zoom` matches `zoom.us`), or as a substring if 6+ characters long. Categories are checked top to bottom and the first match wins.

## Privacy and security

- Never commit your App Password. Use environment variables or the prompt.
- CSV exports list your personal accounts. `.gitignore` excludes `*.csv` so they aren't uploaded by accident.
- You can revoke the App Password at any time from your Google Account, and it is a good idea to do so when you are done.
- This tool is not affiliated with Google.

## Limitations

- Gmail only (IMAP). Other providers need a different server address and folder names.
- Detection is keyword-based, so some accounts will be missed and some senders will not be accounts.
- Emails sent through third-party services (SendGrid, Amazon SES, ...) appear under those service domains.

## License

MIT, see [LICENSE](LICENSE).
