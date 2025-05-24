
import pandas as pd
from sqlalchemy import create_engine

# 連接到 SQLite
engine = create_engine("sqlite:///survey.db")

# 讀取 responses 表
df = pd.read_sql("SELECT * FROM responses", engine)

# 分析年齡分佈
if not df["age"].empty:
    avg_age = df["age"].mean()
    min_age = df["age"].min()
    max_age = df["age"].max()
    print(f"年齡分析：平均年齡 = {avg_age:.1f} 歲，最小年齡 = {min_age} 歲，最大年齡 = {max_age} 歲")
else:
    print("無年齡數據")

# 分析職業分佈
if not df["occupation"].empty:
    occupation_counts = df["occupation"].value_counts()
    print("\n職業分佈：")
    for occupation, count in occupation_counts.items():
        print(f"{occupation}: {count} 人")
else:
    print("無職業數據")

# 分析政治傾向分佈
if not df["political_leaning"].empty:
    political_counts = df["political_leaning"].value_counts()
    print("\n政治傾向分佈：")
    for leaning, count in political_counts.items():
        print(f"{leaning}: {count} 人")
else:
    print("無政治傾向數據")

# 保存分析報告
with open("analysis_report.txt", "w", encoding="utf-8") as f:
    f.write("對話數據分析報告\n")
    f.write("=" * 20 + "\n")
    if not df["age"].empty:
        f.write(f"年齡分析：平均年齡 = {avg_age:.1f} 歲，最小年齡 = {min_age} 歲，最大年齡 = {max_age} 歲\n")
    else:
        f.write("無年齡數據\n")
    f.write("\n職業分佈：\n")
    if not df["occupation"].empty:
        for occupation, count in occupation_counts.items():
            f.write(f"{occupation}: {count} 人\n")
    else:
        f.write("無職業數據\n")
    f.write("\n政治傾向分佈：\n")
    if not df["political_leaning"].empty:
        for leaning, count in political_counts.items():
            f.write(f"{leaning}: {count} 人\n")
    else:
        f.write("無政治傾向數據\n")
print("分析報告已保存至 analysis_report.txt")
