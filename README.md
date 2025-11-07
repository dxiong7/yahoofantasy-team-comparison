# Yahoo Fantasy Sports Tool

A minimal, read-only Python application that authenticates with the Yahoo Fantasy Sports API and compares your team's current week performance across all 9 categories against other teams in your league.

## Setup

1. **Register a Yahoo Developer Application:**
   - Visit [Yahoo Developer Network](https://developer.yahoo.com/) and sign in
   - Create a new app and note your Client ID and Client Secret
   - Set Redirect URI to `https://localhost:8080`
   - Grant "Fantasy Sports" API permissions with "Read" access

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables:**
   ```bash
   export YAHOO_CLIENT_ID="your_client_id"
   export YAHOO_CLIENT_SECRET="your_client_secret"
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```

## Usage

1. The app will prompt you to authenticate via your browser
2. Select your league from the list
3. Select your team from the league
4. View how your team's current week stats compare to all other teams across 9 categories

## Features

- OAuth2 authentication with Yahoo Fantasy Sports API
- League metadata retrieval
- Current week matchup information
- Team selection
- Category-by-category comparison against all league teams

