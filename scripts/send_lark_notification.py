#!/usr/bin/env python3
"""Send Kalshi weekly report notification to Lark/Feishu bot."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError


def send_lark_message(webhook_url: str, report_date: str, release_tag: str) -> bool:
    """Send a rich card message to Lark webhook."""
    
    github_repo = os.environ.get("GITHUB_REPOSITORY", "WYIN711/Prediction-Market")
    release_url = f"https://github.com/{github_repo}/releases/tag/{release_tag}"
    actions_url = f"https://github.com/{github_repo}/actions"
    
    img1_url = f"https://github.com/{github_repo}/releases/download/{release_tag}/7d_rolling_total_volume.png"
    img2_url = f"https://github.com/{github_repo}/releases/download/{release_tag}/top_10_market_types_7d_ma.png"
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 Kalshi 周报 - {report_date}"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**报告日期**: {report_date}

**📈 7日滚动交易量**
[点击查看图表]({img1_url})

**📊 Top 10 市场类型趋势**  
[点击查看图表]({img2_url})

---
*完整报告下载*: [GitHub Release]({release_url})"""
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "📥 下载完整报告"
                            },
                            "type": "primary",
                            "url": release_url
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "🔍 查看 Actions"
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
                print(f"✅ Lark notification sent successfully")
                return True
            else:
                print(f"❌ Lark API error: {result}")
                return False
    except URLError as e:
        print(f"❌ Failed to send Lark notification: {e}")
        return False


def main():
    webhook_url = os.environ.get("LARK_WEBHOOK_URL")
    if not webhook_url:
        print("❌ LARK_WEBHOOK_URL environment variable not set")
        sys.exit(1)
    
    # Get report date from argument or use today
    if len(sys.argv) > 1:
        report_date = sys.argv[1]
    else:
        report_date = datetime.now().strftime("%Y-%m-%d")
    
    # Get release tag from argument or construct from date
    if len(sys.argv) > 2:
        release_tag = sys.argv[2]
    else:
        release_tag = f"report-{report_date}"
    
    success = send_lark_message(webhook_url, report_date, release_tag)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
