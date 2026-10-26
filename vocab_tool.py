import csv

with open("data/生词表.csv", encoding="utf-8") as f, open("练习.txt", "w", encoding="utf-8") as out:
    for line in f:
        line = line.strip()
        if not line:
            continue
        if line.startswith("词汇"):
            continue
        clean_line = line.replace(" ", "")
        if "HSK4" in clean_line:
            parts = line.split(",")
            out.write(f"单词：{parts[0]}，词性：{parts[2]}，释义：{parts[3]}\n")
            import csv

with open("data/生词表.csv", encoding="utf-8") as f:
    print("======= 开始读取csv内容 =======")
    for line in f:
        print(repr(line))
    