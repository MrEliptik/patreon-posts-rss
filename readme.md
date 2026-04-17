Script to generate and host an RSS feed for my Patreon. This script runs in a github action regularly to parse my gmail for new Patreon emails. 

https://mreliptik.dev/patreon-posts-rss/feed.xml

### How to renew google oauth

1. Go to https://console.cloud.google.com/ > project **Gmail** > Google Auth Platform > Clients and choose the corresponding OAuth 2.0 Client created for this (Desktop client python in my case).
2. Add a secret and download it as .json
3. Rename it to credentials.json and place it at the root of the project.
4. Run `python oauth_google.py` to generate a token.b64
5. Copy the content and update the secrets on github
    1. **Settings > Secrets and variables > Actions**
    2. Create or edit `GMAIL_TOKEN`, paste the token content and hit save