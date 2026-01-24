#!/usr/bin/env python3
"""Send Polymarket weekly report notification to Lark/Feishu bot."""

import json
import os
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError


def send_lark_message(webhook_url: str, report_date: str, match_count: int, filename: str) -> bool:
    """Send a rich card message to Lark webhook."""

    github_repo = os.environ.get("GITHUB_REPOSITORY", "WYIN711/Prediction-Market")

    # GitHub Pages URL
    # Format: https://<username>.github.io/<repo>/polymarket/docs/<filename>
    repo_parts = github_repo.split("/")
    if len(repo_parts) == 2:
        username, repo_name = repo_parts
        pages_url = f"https://{username}.github.io/{repo_name}/polymarket/docs/{filename}"
    else:
        pages_url = f"https://github.com/{github_repo}"

    actions_url = f"https://github.com/{github_repo}/actions"

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"Polymarket Weekly Report - {report_date}"
                },
                "template": "green"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**Report Date**: {report_date}

**Markets Found**: {match_count}

Criteria: Volume > $1M, Probability 95-99% or 1-5%, Ending within 6 months

---
*Download Excel*: [Click here]({pages_url})"""
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "Download Report"
                            },
                            "type": "primary",
                            "url": pages_url
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "View Actions"
                            },
                            "url": actions_url
                        }
                    ]
                }
            ]
        }
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("code") == 0 or result.get("StatusCode") == 0:
                print(f"Lark notification sent successfully")
                return True
            else:
                print(f"Lark API error: {result}")
                return False
    except URLError as e:
        print(f"Failed to send Lark notification: {e}")
        return False


def main():
    webhook_url = os.environ.get("LARK_WEBHOOK_URL")
    if not webhook_url:
        print("LARK_WEBHOOK_URL environment variable not set")
        sys.exit(1)

    # Get arguments
    if len(sys.argv) < 4:
        print("Usage: send_lark_notification.py <report_date> <match_count> <filename>")
        sys.exit(1)

    report_date = sys.argv[1]
    match_count = int(sys.argv[2])
    filename = sys.argv[3]

    success = send_lark_message(webhook_url, report_date, match_count, filename)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
