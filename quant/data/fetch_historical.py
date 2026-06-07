"""
fetch_historical.py
────────────────────
用 BaoStock 拉取主流 ETF 历史日线数据，存为 Parquet 格式。
BaoStock 使用证券宝数据源，无需付费，覆盖全量 A 股 ETF。

用法：
    python -m quant.data.fetch_historical                   # 拉全部，默认近 3 年
    python -m quant.data.fetch_historical --years 5         # 近 5 年
    python -m quant.data.fetch_historical --code 510300     # 只拉单只
    python -m quant.data.fetch_historical --skip-existing   # 跳过已有数据

输出：quant/data/historical/<code>.parquet
"""

import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta

import baostock as bs
import pandas as pd

from quant.utils.etf_list import ETF_CODES, CODE_TO_NAME

SAVE_DIR = Path(__file__).parent / "historical"
SAVE_DIR.mkdir(parents=True, exist_ok=True)


def _bs_code(code: str) -> str:
    """将纯数字代码转换为 BaoStock 格式（sh.510300 / sz.159915）。"""
    if code.startswith(("5", "11")):
        return f"sh.{code}"
    else:
        return f"sz.{code}"


def fetch_one(code: str, start: str, end: str) -> pd.DataFrame:
    """拉取单只 ETF 日线数据。code 为纯数字格式如 '510300'。"""
    bs_code = _bs_code(code)
    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,open,high,low,close,volume",
        start_date=start,
        end_date=end,
        frequency="d",
        adjustflag="2",  # 前复权
    )

    if rs.error_code != "0":
        raise ValueError(f"{code} 查询失败：{rs.error_msg}")

    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())

    if not data_list:
        raise ValueError(f"{code}（{bs_code}）无数据")

    df = pd.DataFrame(data_list, columns=rs.fields)
    df = df.rename(columns={"date": "date"})

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["date"] = pd.to_datetime(df["date"])
    df["pct_chg"] = df["close"].pct_change() * 100
    df["code"] = code
    df["name"] = CODE_TO_NAME.get(code, "")
    df = df.sort_values("date").reset_index(drop=True)
    return df


def fetch_all(codes: list, years: int = 3, skip_existing: bool = False):
    end   = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=365 * years)).strftime("%Y-%m-%d")

    print(f"数据源：BaoStock（证券宝）  |  区间：{start} ~ {end}\n")

    lg = bs.login()
    if lg.error_code != "0":
        print(f"BaoStock 登录失败：{lg.error_msg}")
        return []

    success, failed = [], []
    for code in codes:
        name = CODE_TO_NAME.get(code, code)
        path = SAVE_DIR / f"{code}.parquet"

        if skip_existing and path.exists():
            print(f"  跳过 {code} {name}（已存在）")
            success.append(code)
            continue

        try:
            print(f"  拉取 {code} {name} ...", end=" ", flush=True)
            df = fetch_one(code, start, end)
            df.to_parquet(path, index=False)
            print(f"✓  {len(df)} 条")
            success.append(code)
        except Exception as e:
            print(f"✗  {e}")
            failed.append((code, str(e)))

        time.sleep(0.1)

    bs.logout()

    print(f"\n完成：成功 {len(success)} 只，失败 {len(failed)} 只")
    if failed:
        print("\n失败列表：")
        for code, err in failed:
            print(f"  {code} {CODE_TO_NAME.get(code,'')}: {err}")
    return failed


def load(code: str) -> pd.DataFrame:
    """读取本地已存储的历史数据。"""
    path = SAVE_DIR / f"{code}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"本地无数据：{path}，请先运行 fetch_all()")
    return pd.read_parquet(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--years",         type=int,  default=3,    help="拉取近几年数据")
    parser.add_argument("--code",          type=str,  default=None, help="只拉取单只 ETF")
    parser.add_argument("--skip-existing", action="store_true",     help="跳过已有数据的 ETF")
    args = parser.parse_args()

    codes = [args.code] if args.code else ETF_CODES
    print(f"开始拉取 {len(codes)} 只 ETF，近 {args.years} 年数据...\n")
    fetch_all(codes, years=args.years, skip_existing=args.skip_existing)
