"""对 CSV 文件中缺失的发布日期进行插值估算"""

from datetime import datetime, timedelta
import csv
from pathlib import Path


def interpolate_dates(dates: list[str | None]) -> list[str | None]:
    """
    对缺失的发布日期进行插值估算。

    假设列表按发布时间倒序排列（最新的在前），对于缺失日期的项目，
    根据其前后有日期的项目进行线性插值。

    Args:
        dates: 日期列表（ISO 格式或 None），按列表顺序

    Returns:
        插值后的日期列表
    """
    n = len(dates)
    result: list[str | None] = list(dates)

    # 找出有日期的位置索引
    dated_indices = [i for i, d in enumerate(dates) if d is not None]

    if not dated_indices:
        # 全部没有日期，无法插值
        return result

    # 对每个缺失日期的位置进行插值
    for i in range(n):
        if result[i] is not None:
            continue

        # 找到前一个和后一个有日期的位置
        prev_idx = None
        next_idx = None
        for di in dated_indices:
            if di < i:
                prev_idx = di
            elif di > i and next_idx is None:
                next_idx = di
                break

        if prev_idx is not None and next_idx is not None:
            # 在两个有日期之间，线性插值
            prev_date = datetime.fromisoformat(dates[prev_idx])
            next_date = datetime.fromisoformat(dates[next_idx])
            total_days = (prev_date - next_date).days
            pos_ratio = (i - prev_idx) / (next_idx - prev_idx)
            estimated = prev_date - timedelta(days=int(total_days * pos_ratio))
            result[i] = estimated.strftime("%Y-%m-%d")
        elif prev_idx is not None:
            # 只有前一个日期，往后递减（假设每天发布 1 部）
            prev_date = datetime.fromisoformat(dates[prev_idx])
            days_diff = i - prev_idx
            estimated = prev_date - timedelta(days=days_diff)
            result[i] = estimated.strftime("%Y-%m-%d")
        elif next_idx is not None:
            # 只有后一个日期，往前递增
            next_date = datetime.fromisoformat(dates[next_idx])
            days_diff = next_idx - i
            estimated = next_date + timedelta(days=days_diff)
            result[i] = estimated.strftime("%Y-%m-%d")

    return result


def interpolate_csv_file(csv_path: Path) -> int:
    """
    对 CSV 文件中的 publish_date_std 列进行插值估算。

    Args:
        csv_path: CSV 文件路径

    Returns:
        插值的记录数量
    """
    # 读取 CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not fieldnames or "publish_date_std" not in fieldnames:
        return 0

    # 提取日期列
    original_dates = [row.get("publish_date_std") or None for row in rows]
    empty_count = sum(1 for d in original_dates if not d)

    if empty_count == 0:
        # 没有缺失值，不需要插值
        return 0

    # 插值
    interpolated_dates = interpolate_dates(original_dates)

    # 更新 CSV
    for i, row in enumerate(rows):
        row["publish_date_std"] = interpolated_dates[i] or ""

    # 写回 CSV
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return empty_count
