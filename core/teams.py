import json
from collections import defaultdict
from datetime import datetime
import requests


def build_adaptive_card(title: str, summary: str, updated_items: list = None, total_count: int = 0, is_test: bool = False) -> dict:
    """建構 Microsoft Teams Adaptive Card 訊息格式 (相容 Teams Workflows 及現代 Webhook)"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    card_body = [
        {
            "type": "TextBlock",
            "text": title,
            "weight": "Bolder",
            "size": "Large",
            "color": "Accent"
        },
        {
            "type": "TextBlock",
            "text": summary,
            "wrap": True,
            "spacing": "Small"
        }
    ]

    if is_test:
        card_body.append({
            "type": "FactSet",
            "facts": [
                {"title": "連線狀態", "value": "連線測試成功 ✅"},
                {"title": "發送時間", "value": now_str},
                {"title": "系統名稱", "value": "規範自動檢查系統"}
            ],
            "spacing": "Medium"
        })
    elif updated_items:
        items_to_show = updated_items[:25]
        card_body.append({
            "type": "TextBlock",
            "text": f"📋 **異動項目清單 (共 {len(updated_items)} 項更新)**：",
            "weight": "Bolder",
            "spacing": "Medium"
        })

        # 依類別分組，不同類別換行呈現，同一項目內同一行顯示
        category_map = defaultdict(list)
        for item in items_to_show:
            platform = item.get("source", "").strip() or "其他"
            category_map[platform].append(item)

        for platform, items in category_map.items():
            card_body.append({
                "type": "TextBlock",
                "text": f"**【{platform}】**",
                "weight": "Bolder",
                "color": "Accent",
                "spacing": "Small"
            })
            for item in items:
                std_id = item.get("name", "未命名標準")
                prev_ver = item.get("previousDocumentName", "") or "無資料"
                curr_ver = item.get("latestDocumentName", "") or "無資料"

                item_text = f"• **{std_id}**：前次版本 `{prev_ver}` ➔ 最新版本 **`{curr_ver}`**"
                card_body.append({
                    "type": "TextBlock",
                    "text": item_text,
                    "wrap": True,
                    "spacing": "None"
                })

        if len(updated_items) > 25:
            card_body.append({
                "type": "TextBlock",
                "text": f"*...另有 {len(updated_items) - 25} 項未列出，請開啟系統查看完整清單。*",
                "isSubtle": True,
                "spacing": "Small"
            })
    else:
        card_body.append({
            "type": "TextBlock",
            "text": "✅ **檢查結果：** 本次檢查全部追蹤項目皆為最新版本，未檢測到法規更新。",
            "wrap": True,
            "color": "Good",
            "spacing": "Medium"
        })
        facts = [{"title": "檢查時間", "value": now_str}]
        if total_count > 0:
            facts.append({"title": "檢查項目總數", "value": f"{total_count} 項"})
        card_body.append({
            "type": "FactSet",
            "facts": facts,
            "spacing": "Small"
        })

    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": card_body
                }
            }
        ]
    }
    return payload


def build_message_card(title: str, summary: str, updated_items: list = None, total_count: int = 0, is_test: bool = False) -> dict:
    """建構傳統 Office 365 Connector (MessageCard) 格式作為後備降級"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    facts = []

    if is_test:
        facts.append({"name": "連線狀態", "value": "連線測試成功 ✅"})
        facts.append({"name": "發送時間", "value": now_str})
        facts.append({"name": "系統名稱", "value": "規範自動檢查系統"})
    elif updated_items:
        category_map = defaultdict(list)
        for item in updated_items[:25]:
            platform = item.get("source", "").strip() or "其他"
            category_map[platform].append(item)

        for platform, items in category_map.items():
            lines = []
            for item in items:
                std_id = item.get("name", "")
                prev_ver = item.get("previousDocumentName", "") or "無資料"
                curr_ver = item.get("latestDocumentName", "") or "無資料"
                lines.append(f"• **{std_id}**：前次版本 `{prev_ver}` ➔ 最新版本 **`{curr_ver}`**")

            facts.append({
                "name": f"【{platform}】",
                "value": "  \n".join(lines)
            })

        if len(updated_items) > 25:
            facts.append({"name": "提示", "value": f"另有 {len(updated_items) - 25} 項未列出"})
    else:
        facts.append({"name": "檢查結果", "value": "所有追蹤項目皆為最新版本，未檢測到法規更新。"})
        if total_count > 0:
            facts.append({"name": "檢查項目總數", "value": f"{total_count} 項"})
        facts.append({"name": "檢查時間", "value": now_str})

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0076D7",
        "summary": title,
        "sections": [{
            "activityTitle": title,
            "activitySubtitle": summary,
            "facts": facts,
            "markdown": True
        }]
    }
    return payload


def send_teams_notification(
    webhook_url: str,
    title: str,
    summary: str,
    updated_items: list = None,
    total_count: int = 0,
    is_test: bool = False
) -> tuple[bool, str]:
    """
    發送 Microsoft Teams 通知
    優先使用 Adaptive Card 格式，若遇到 400 錯誤則自動降級嘗試 MessageCard 格式
    回傳 (成功: bool, 說明訊息: str)
    """
    if not webhook_url or not webhook_url.strip():
        return False, "Webhook 網址不得為空"

    url = webhook_url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, "Webhook 網址格式不正確（需以 http:// 或 https:// 開頭）"

    headers = {"Content-Type": "application/json"}

    # 1. 嘗試 Adaptive Card (適用於 Teams Workflows 與現代 Webhook)
    payload_adaptive = build_adaptive_card(title, summary, updated_items, total_count=total_count, is_test=is_test)
    try:
        resp = requests.post(url, json=payload_adaptive, headers=headers, timeout=12)
        if resp.status_code in (200, 202):
            return True, "發送成功"

        # 若回傳 400 Bad Request，嘗試使用傳統 MessageCard 降級
        if resp.status_code == 400:
            payload_legacy = build_message_card(title, summary, updated_items, total_count=total_count, is_test=is_test)
            resp_legacy = requests.post(url, json=payload_legacy, headers=headers, timeout=12)
            if resp_legacy.status_code in (200, 202):
                return True, "發送成功 (MessageCard相容模式)"
            return False, f"伺服器回應錯誤 (HTTP {resp_legacy.status_code}): {resp_legacy.text[:150]}"

        return False, f"伺服器回應錯誤 (HTTP {resp.status_code}): {resp.text[:150]}"
    except requests.exceptions.Timeout:
        return False, "連線逾時，請檢查網路連線或 Webhook 網址"
    except requests.exceptions.RequestException as e:
        return False, f"連線錯誤: {str(e)}"
    except Exception as e:
        return False, f"未預期錯誤: {str(e)}"
