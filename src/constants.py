"""Shared database values and Traditional Chinese UI labels."""

CATEGORY_LABELS = {
    "vegetable": "蔬菜",
    "fruit": "水果",
    "meat": "肉類",
    "seafood": "海鮮",
    "egg_dairy": "蛋／乳製品",
    "staple": "主食／澱粉",
    "beverage": "飲品",
    "condiment": "調味料",
    "prepared_food": "熟食／即食食品",
    "other": "其他",
}
CATEGORY_OPTIONS = tuple(CATEGORY_LABELS)
UNIT_LABELS = {
    "g": "公克 g",
    "kg": "公斤 kg",
    "ml": "毫升 mL",
    "l": "公升 L",
    "piece": "個",
    "pack": "包",
    "box": "盒",
    "bottle": "瓶",
    "can": "罐",
    "bag": "袋",
    "other": "其他",
}
UNIT_OPTIONS = tuple(UNIT_LABELS)
STORAGE_LABELS = {
    "refrigerator": "冷藏",
    "freezer": "冷凍",
    "pantry": "常溫／儲藏櫃",
}
STORAGE_OPTIONS = tuple(STORAGE_LABELS)
DATE_LABEL_LABELS = {"use_by": "Use By", "best_before": "Best Before"}
DATE_LABEL_OPTIONS = tuple(DATE_LABEL_LABELS)
STATUS_LABELS = {"active": "使用中", "consumed": "已使用", "wasted": "已丟棄"}
STATUS_OPTIONS = tuple(STATUS_LABELS)
WARNING_THRESHOLD_OPTIONS = (1, 3, 5, 7)
DEFAULT_WARNING_THRESHOLD_DAYS = 3
NO_DATE_LABEL = "未設定日期"
DATE_DISCLAIMER = "日期提醒僅供食材管理輔助，不能取代實際食品安全判斷。"
PASSED_DATE_MESSAGES = {
    "use_by": "已超過輸入的 Use By 日期，請依產品標示及實際狀況進一步確認。",
    "best_before": "已超過 Best Before 日期；此日期主要與品質資訊相關，仍請依產品標示及實際食品狀況確認。",
}

# UI suggestions only; InventoryService continues accepting an optional text reason.
WASTE_REASON_LABELS = {
    None: "不填寫原因",
    "expired": "過期",
    "spoiled": "變質",
    "over-purchased": "購買過量",
    "over-prepared": "料理過量",
    "other": "其他",
}
