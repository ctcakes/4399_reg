import subprocess
import random
import string
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import os

INPUT_FILE = "1.txt"
OUTPUT_FILE = "accs.txt"

lock = threading.Lock()


def random_username():
    chars = string.ascii_letters + string.digits
    length = random.randint(6, 10)
    return ''.join(random.choice(chars) for _ in range(length))


def random_password():
    chars = (
        string.ascii_uppercase +
        string.ascii_lowercase +
        string.digits +
        "!@#$%^&*"
    )

    while True:
        pwd = ''.join(random.choice(chars) for _ in range(13))

        if (
            re.search("[A-Z]", pwd)
            and re.search("[a-z]", pwd)
            and re.search("[0-9]", pwd)
            and re.search("[!@#$%^&*]", pwd)
        ):
            return pwd


def save_account(username, password, demo):
    with lock:
        with open(
            OUTPUT_FILE,
            "a",
            encoding="utf-8"
        ) as f:
            f.write(
                f"{username}----{password}----{demo}\n"
            )


def parse_result(output):
    """
    从:
    [*] 注册结果: {...json...}

    提取JSON
    """

    match = re.search(
        r'\{.*\}',
        output,
        re.S
    )

    if not match:
        return None

    try:
        return json.loads(match.group())
    except:
        return None


def register(demo):

    username = random_username()
    password = random_password()

    cmd = [
        "python",
        "register_4399.py",
        "--username",
        username,
        "--password",
        password,
        "--realname",
        "\u674e\u8273\u5a1f",
        "--idcard",
        demo
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            env={
                **os.environ,
                "PYTHONUTF8": "1"
            }
        )

        output = (
            result.stdout +
            result.stderr
        )

        print(
            f"[{username}] {output.strip()}"
        )

        data = parse_result(output)

        if not data:
            return

        if (
            data.get("ok") is True
            and data.get("status_code") == 200
        ):
            print(
                f"[成功] {username}"
            )

            save_account(
                username,
                password,
                demo
            )

        else:
            print(
                f"[失败] {username}"
            )

    except Exception as e:
        print(
            f"[异常] {username}: {e}"
        )


def load_demo():

    demos = []

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            demos.append(line)

    return demos



def main():

    count = int(
        input(
            "请输入注册数量: "
        )
    )

    threads = int(
        input(
            "请输入线程数量: "
        )
    )

    demos = load_demo()

    if not demos:
        print("1.txt 没有有效内容")
        return

    print(
        f"读取 {len(demos)} 条demo数据"
    )

    with ThreadPoolExecutor(
        max_workers=threads
    ) as pool:

        for _ in range(count):

            demo = random.choice(demos)

            pool.submit(
                register,
                demo
            )


if __name__ == "__main__":
    main()