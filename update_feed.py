import os
import base64
import pickle
import re
from email.utils import formatdate, parseaddr
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
import xml.etree.ElementTree as ET

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if not elem.tail or not elem.tail.strip():
            elem.tail = i

def main():
    #  Config 
    FEED_FILE = "feed.xml"
    PATREON_LABEL_NAME = "PATREON-POSTS"

    #  Load credentials 
    if os.path.exists("token.pkl"):
        with open("token.pkl", "rb") as f:
            creds = pickle.load(f)
    else:
        token_b64 = os.environ['GMAIL_TOKEN']
        creds = pickle.loads(base64.b64decode(token_b64))

    # Connect to Gmail API 
    service = build('gmail', 'v1', credentials=creds)

    # Get label ID dynamically 
    labels = service.users().labels().list(userId='me').execute()
    label_id = None
    for label in labels.get('labels', []):
        if label['name'] == PATREON_LABEL_NAME:
            label_id = label['id']
            break

    if not label_id:
        raise ValueError(f"Label '{PATREON_LABEL_NAME}' not found in Gmail account")

    # Regex for Patreon URL 
    patreon_url_re = re.compile(r"(https://www\.patreon\.com/posts/[\w\-]+)")

    # Load feed.xml and get latest post time 
    tree = ET.parse(FEED_FILE)
    root = tree.getroot()
    channel = root.find('channel')

    # Get the latest email timestamp from existing feed items
    latest_timestamp = 0
    for item in channel.findall('item'):
        pub_date = item.find('pubDate').text
        try:
            dt = parsedate_to_datetime(pub_date)  # correctly handles +0200 etc
            ts = int(dt.timestamp())
            if ts > latest_timestamp:
                latest_timestamp = ts
        except Exception:
            continue

    new_posts = []

    #  Fetch messages with the label 
    results = service.users().messages().list(
        userId='me',
        labelIds=[label_id],
        maxResults=50
    ).execute()
    messages = results.get('messages', [])

    for msg in messages:
        m = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = m.get('payload', {}).get('headers', [])
        
        from_header = next((h['value'] for h in headers if h['name'] == 'From'), None)
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), None)
        
        if not from_header or not subject:
            continue

        sender_name, sender_email = parseaddr(from_header)
        
        if sender_email.lower() == 'bingo@patreon.com' and sender_name.strip() == 'MrEliptik':
            # Use internalDate to check if this is a new post
            email_ts = int(m.get('internalDate', 0)) // 1000  # Gmail returns milliseconds
            if email_ts <= latest_timestamp:
                continue  # already in feed

            # Get HTML body
            body_html = ""
            payload = m.get('payload', {})
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/html':
                        body_html = base64.urlsafe_b64decode(part['body']['data']).decode()
                        break
            else:
                if payload.get('mimeType') == 'text/html':
                    body_html = base64.urlsafe_b64decode(payload.get('body', {}).get('data', b"")).decode()

            soup = BeautifulSoup(body_html, 'html.parser')

            # Find Patreon post link (clean)
            patreon_link = None
            for a in soup.find_all('a', href=True):
                match = patreon_url_re.search(a['href'])
                if match:
                    patreon_link = match.group(1)
                    break

            # Find first image from a Patreon post (ignore campaigns)
            image_link = None
            for img in soup.find_all('img', src=True):
                src = img['src']
                if "/post/" in src:
                    if "#" in src:
                        # Patreon image is after the '#'
                        image_link = src.split("#", 1)[1]
                    else:
                        image_link = src
                    break

            #  Extract first two lines of text for description 
            text_content = soup.get_text(separator="\n").strip()
            lines = [line.strip() for line in text_content.splitlines() if line.strip()]
            snippet = " ".join(lines[:2]) + "…" if lines else "New Patreon post…"

            new_posts.append({
                "title": subject,
                "link": patreon_link,
                "image": image_link,
                "snippet": snippet,
                "timestamp": email_ts
            })

    #  Update feed.xml 
    if new_posts:
        # Update lastBuildDate
        last_build = channel.find('lastBuildDate')
        if last_build is not None:
            last_build.text = formatdate(localtime=True)

        # Sort new posts by timestamp ascending (oldest first)
        new_posts.sort(key=lambda x: x['timestamp'])

        # Prepend new posts
        for post in new_posts:
            item = ET.Element('item')

            title = ET.SubElement(item, 'title')
            title.text = post['title']

            link = ET.SubElement(item, 'link')
            link.text = post['link']

            pubDate = ET.SubElement(item, 'pubDate')
            pubDate.text = formatdate(post['timestamp'], localtime=True)

            description = ET.SubElement(item, 'description')
            description.text = f"<![CDATA][<img src='{post['image']}'/><br>{post['snippet']}]>"

            # Insert after <lastBuildDate>
            channel.insert(4, item)

        # Apply to the root element
        indent(tree.getroot())

        # Save to file
        tree.write(FEED_FILE, encoding='utf-8', xml_declaration=True)

        print(f"Added {len(new_posts)} new post(s) to feed.xml")
    else:
        print("No new posts to add.")

if __name__ == '__main__':
    main()