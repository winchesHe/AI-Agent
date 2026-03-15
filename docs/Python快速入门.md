# Python 快速入门

面向有编程基础读者的精简语法与概念速查。

---

## 1. 运行方式

```bash
# 直接运行脚本
python script.py

# 交互式（REPL）
python
```

---

## 2. 基础语法

- **缩进**：用 4 个空格表示代码块，不用大括号。
- **注释**：`# 单行注释`
- **多行字符串/文档**：`""" 多行 """` 或 `''' 多行 '''`

```python
if True:
    print("缩进属于 if 块")
print("这里已经跳出 if")
```

---

## 3. 变量与类型

无需声明类型，直接赋值。

```python
name = "小明"
age = 18
height = 1.75
is_student = True
nothing = None
```

| 类型     | 示例                    |
|----------|-------------------------|
| 整型 int | `42`, `-3`              |
| 浮点 float | `3.14`, `1e-2`        |
| 字符串 str | `"双引号"`, `'单引号'` |
| 布尔 bool | `True`, `False`        |
| 空值     | `None`                  |

---

## 4. 字符串

```python
s = "Hello"
len(s)           # 5
s + " World"     # "Hello World"
s * 2            # "HelloHello"
s[0]             # "H"
s[1:4]           # "ell"（切片：从 1 到 4 不包含 4）
s.upper()        # "HELLO"
"a,b,c".split(",")   # ["a", "b", "c"]
" ".join(["a", "b"]) # "a b"

# 格式化
f"名字: {name}, 年龄: {age}"           # f-string（推荐）
"名字: {}, 年龄: {}".format(name, age)
"名字: %s" % name
```

---

## 5. 列表 list（可变有序）

```python
nums = [1, 2, 3]
nums.append(4)
nums[0]          # 1
nums[-1]         # 最后一个
nums[1:3]        # [2, 3]
len(nums)
for x in nums:
    print(x)
```

---

## 6. 字典 dict（键值对）

```python
d = {"name": "小明", "age": 18}
d["name"]        # "小明"
d.get("key", "默认值")
d["new"] = 1
for k, v in d.items():
    print(k, v)
```

---

## 7. 条件与循环

```python
# if / elif / else
if x > 0:
    print("正")
elif x < 0:
    print("负")
else:
    print("零")

# for
for i in range(5):      # 0,1,2,3,4
    print(i)
for item in my_list:
    print(item)

# while
while n > 0:
    n -= 1
```

---

## 8. 函数 def

```python
def greet(name, greeting="你好"):
    return f"{greeting}, {name}!"

greet("小明")              # "你好, 小明!"
greet("小明", "Hi")        # "Hi, 小明!"
```

- 无 `return` 时返回 `None`。
- 参数可带默认值；传参可用位置或关键字：`func(1, b=2)`。

---

## 9. 类 class

```python
class Dog:
    def __init__(self, name):
        self.name = name

    def bark(self):
        print(f"{self.name}: 汪!")

dog = Dog("旺财")
dog.bark()
```

- `__init__`：构造方法，创建实例时自动调用。
- `self`：代表当前实例，第一个参数必须是 `self`（名字可改但不建议）。

---

## 10. 导入 import

```python
import os
from os import getenv
from os import path as p
from tools.web_search import ToolExecutor, search
```

- 包：含 `__init__.py` 的目录。
- 模块文件名用下划线：`web_search.py`，不要用连字符。

---

## 11. 文件与异常

```python
# 读文件（推荐 with，自动关文件）
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()

# 写文件
with open("out.txt", "w", encoding="utf-8") as f:
    f.write("内容")

# 异常
try:
    risky()
except ValueError as e:
    print(e)
except Exception as e:
    print("其他错误", e)
finally:
    print("总会执行")
```

---

## 12. 常用内置

```python
len([1,2,3])       # 3
range(5)           # 0,1,2,3,4
range(1, 6, 2)     # 1,3,5
list("abc")        # ["a","b","c"]
dict(a=1, b=2)     # {"a":1, "b":2}
str(42)            # "42"
int("42")          # 42
float("3.14")      # 3.14
sorted([3,1,2])    # [1,2,3]
max([1,2,3])       # 3
sum([1,2,3])       # 6
```

---

## 13. 环境变量（.env）

```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")
api_key = os.getenv("API_KEY", "默认值")
```

---

## 14. 速记表

| 概念     | 写法示例 |
|----------|----------|
| 定义函数 | `def f(x):` |
| 定义类   | `class C:` |
| 条件     | `if / elif / else` |
| 循环     | `for x in ...`、`while ...` |
| 列表     | `[1, 2, 3]` |
| 字典     | `{"a": 1}` |
| 字符串格式化 | `f"{x}"`、`"{}".format(x)` |
| 空值     | `None` |
| 布尔     | `True`、`False` |

---

按此文档即可快速上手本项目中的 Python 代码；遇到具体 API 可再查官方文档或 IDE 提示。
