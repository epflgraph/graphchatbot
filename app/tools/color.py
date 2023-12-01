import random
import hashlib
import requests


def find_color(name: str) -> str:
    print("[COLOR]", f"Called find color tool with input `{name}`")

    md5_hash = hashlib.md5(name.encode('utf-8')).hexdigest()
    seed = int(md5_hash, 16)

    random.seed(seed)
    number = random.randint(0, 256 ** 3 - 1)
    color_hex_code = str(hex(number))[2:].rjust(6, "0")

    print("[COLOR]", f"Found color hex code `{color_hex_code}`")

    url = f'https://www.thecolorapi.com/id?hex={color_hex_code}'
    color_name = requests.get(url).json()['name']['value']

    print("[COLOR]", f"Found color name `{color_name}`")

    return color_name
