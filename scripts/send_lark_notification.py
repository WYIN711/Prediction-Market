#!/usr/bin/env python3
"""Send Kalshi notifications to Lark/Feishu bot."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError


def send_lark_card(webhook_url: str, payload: dict) -> bool:
    """Send a card message to Lark webhook."""
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


def send_failure_notification(
    webhook_url: str,
    workflow_name: str,
    run_id: str,
    error_message: str = "",
) -> bool:
    """Send a failure notification to Lark."""
    github_repo = os.environ.get("GITHUB_REPOSITORY", "WYIN711/Prediction-Market")
    run_url = f"https://github.com/{github_repo}/actions/runs/{run_id}"
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"❌ GitHub Action 失败: {workflow_name}"
                },
                "template": "red"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"""**工作流**: {workflow_name}
**时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Run ID**: {run_id}

{f"**错误信息**: {error_message}" if error_message else ""}

请检查 GitHub Actions 日志以了解详情。"""
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "🔍 查看日志"
                            },
                            "type": "primary",
                            "url": run_url
                        }
                    ]
                }
            ]
        }
    }
    
    return send_lark_card(webhook_url, payload)


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
    
    return send_lark_card(webhook_url, payload)


def main():
    parser = argparse.ArgumentParser(description="Send Lark notifications")
    subparsers = parser.add_subparsers(dest="command", help="Notification type")
    
    # Report notification (default behavior for backward compatibility)
    report_parser = subparsers.add_parser("report", help="Send weekly report notification")
    report_parser.add_argument("report_date", nargs="?", help="Report date (YYYY-MM-DD)")
    report_parser.add_argument("release_tag", nargs="?", help="Release tag")
    
    # Failure notification
    failure_parser = subparsers.add_parser("failure", help="Send failure notification")
    failure_parser.add_argument("--workflow", required=True, help="Workflow name")
    failure_parser.add_argument("--run-id", required=True, help="GitHub Actions run ID")
    failure_parser.add_argument("--error", default="", help="Error message")
    
    args = parser.parse_args()
    
    webhook_url = os.environ.get("LARK_WEBHOOK_URL")
    if not webhook_url:
        print("❌ LARK_WEBHOOK_URL environment variable not set")
        sys.exit(1)
    
    # Handle backward compatibility: if no command, treat as report
    if args.command is None or args.command == "report":
        # Backward compatible: support old-style positional args
        if args.command is None and len(sys.argv) > 1:
            report_date = sys.argv[1]
            release_tag = sys.argv[2] if len(sys.argv) > 2 else f"report-{report_date}"
        else:
            report_date = args.report_date or datetime.now().strftime("%Y-%m-%d")
            release_tag = args.release_tag or f"report-{report_date}"
        
        success = send_lark_message(webhook_url, report_date, release_tag)
    
    elif args.command == "failure":
        success = send_failure_notification(
            webhook_url,
            workflow_name=args.workflow,
            run_id=args.run_id,
            error_message=args.error,
        )
    
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
