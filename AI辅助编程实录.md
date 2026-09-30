# 1. 任务与提示词
要做什么：读取生词表CSV→筛HSK4→造练习题
我写的提示词：
> 写一个Python脚本，读取csv生词表文件，筛选出HSK4等级的词语，生成中文练习题，输出到练习.txt。需要可以读取本地csv，处理中文，代码尽量简单，注释清晰。

## 2. AI初版代码
```python
import csv

def make_exercise():
    file = "vocab.csv"
    out_file = "练习.txt"
    with open(file) as f:
        reader = csv.DictReader(f)
        res = []
        for row in reader:
            if row["HSK等级"] == "HSK4":
                res.append(row["词语"])
    with open(out_file,"w") as f2:
        for word in res:
            f2.write(f"请解释词语：{word}\n")

if __name__ == "__main__":
    make_exercise()
