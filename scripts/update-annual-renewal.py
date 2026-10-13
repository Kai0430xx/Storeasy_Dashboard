from pathlib import Path
import base64, gzip, json, re

root = Path(__file__).resolve().parents[1]
marker = 'storeasy-annual-renew-backfill-v2'
payload = (
    "H4sIAAAAAAACA806a3PURrZ/RZ7ieqQgy8ZJ7tYdj2Yg2eRWKtkkBeytuuWZlDWjtq14JM1KGmPvjKocEoIBO1A3QAKGkOyGrPPg"
    "sYEsBgyp2p+y8Tz8yX/hnu7TrcfMmDzqfrgUMFL36dOnz/ucVjPj1v1MTmpmfK86HhjeHAn8MaNuaQEdnp7OeKReM6oko0oZSaq6"
    "jh9IDlkK9KamaXOuUVPrxLNcE+etWRlftRpx5oJ5XddfUCiU5pFZ4nlGzdedRq02VXKeiaxcBnSUIsuuu17ga+8Oowb/GLbbcAI/"
    "Jy3UrSP4LHvuCV9NAnnEISdeWj5OPDsnvVV5l1QDbdZz7VecwLOIL0+XMrbrBPO15VJGLWX+1DC8gHj8bd6ozf43MTz2sgwPdLys"
    "2UZdlhfIsmo5JllS9MI0fWE7/ZdRaxB/mk2Uy4qi0vP+HLnRoW3DcoD/SwNHJosEwPUm/oZSw7Hoa801TGKG0nghzI+/Yfx5+Y90"
    "vBD+giVAxB/ouWGo4hlOdZ742qxVg7PLFb0wUtEMrzFvLRJzdFRGgNdMEGrWqNWyrVZFs+ibmFAUbbZmBH8AvsDiJsrX1mXTCIxp"
    "ClsuaozLfqs1XQZg4I8se7mj7gngnuzhZKvlAagCeG3XBM1hg8qUR4KG50h2UfPdhlcllArUjmxxmuqPrQo6cnQiv/vamYRN4d+An"
    "LOemy1OhMoRRwPkUo3NSKYPIX69bpQwO1Y1lyjatYlQXgEe1t5zaslQESDFwlIoeVLyUkfoR9G8A9HJ0TEhLlh9YzhyKIicxhuHp"
    "xZki1kmtljQN6BIY+pGXMr17pzuXr7TX7rRP3WzfXuusXsBD7HuE7qO17v0Pun+70bl2o7364e7np9oPvu/99druk7N726vdja32"
    "hTUc39la3z293r7z7d72GX7QobtxoubIEt1Ynm041cByHek1xpVXXc8ulcDsSn6pdKz8XFGRpehPvtIIAtcpxUZD/1Rrhu9Tceql"
    "TN2zbMNblvxGxbaCUkahexw+fOjw4Ri+uQDqJYGaAIULVAjS6KiUL+TrBThI57ML7Wub33vfdb6/Ob7xoPfF2k8rJXvnbrbPf7N7"
    "baX31Xtw9p2ts73Vs9Lrb78mda9+gBzqXH7Y+WJ1b3ut9+257sXNn1bWYAXADvLvp5X1ve2NoZyDrfLj9QI/ZupgPgGrMeFoQK5p"
    "+UalRkwwzYa/TOU+UvfIokVOcFXgTjaUXOflmlVd0Jsy2JHrHGNckalR8AVqUuC5wGsQMIPCfqTnx5GyQh4MpeQcPjx5+HDsnf4T"
    "/LT/1iLxGCUJN8VFDfKbf75QKjWppyyVQqn98H770VfdjdudzSv5cZiLpS4XdUkCUHAno6MKX33EcRpGjW1znDJAEp4p9lEhOPSq"
    "65kwxB9CZjR6k/4fSnRrnREQSnM1t2LU9Cb+Uma9YloQcvA3HC+UHFRW4FWdOMwgS080X2mAGho2pKw23j+RnRKIEqaYD+YLvSdn"
    "dh6f61za2j19Pj8OA83+GPk7Cjo4Ojo6dHk4ZH3/vk0IRT6LUAt6IR+Y8Rj37jA8gKXVWhgBrxqF6qySxBApwHHMEoZGqHzNqJBa"
    "imYueMupNyDao5pHW4CaB8t1OuQ07AqBECvZlgOvE/DkB6QOj4eoLZBZo1ELWFyFYAaCA3epLbIwG+cWxWI2CwLNjyMV7NACdhh3"
    "/z8RG/Z5TObDwDTASxpM00qlYqkULx9hiVSp1IK/dc+d84jvR/PELEyUSgpVIK+gPVcEvfHAJFlG8Cxlbwr0GInCSNnF+Bj3PO/6"
    "Q9Wdee96yqPNWw446AI6gc7NW92tp52PvoiBOful56XurQ93Ht8Er9u5trrz+AkIZG/7ah9FMrVpNYDQSDOtWV+tKCH1pRgqftnW"
    "kSKn01wRqYq28o48DawPys8pLJvLSbLdwjSEcRiG1CjgcAjmJPkcdZliRuScIH0LfBNhOcLLmPYlVSCYmhhRqMNPJwYamB1fhNQU"
    "k4spPFUJ9ZkCHkJHUsosgRmDcPksCVcNn6TzG1pApCcHcyKAEQEdM8NmP0yoGycMK5AQsQwECYgxThm4pCmBhCeE/UhYthmlTSp7"
    "Q6XF5zRLcQzO+6pVIwJ3iD/Dj8m0Z9YCcwtcj2heo0YGaxPbCKrz0jGuO95kvyHyaJ8p3DLKkpiY2JGoaOFQSsS9GgmkRd1kypBN"
    "yD+rUulH/OHsWYQMiKkFVQ/Z5MkzHRTZM02LFiXLl8DXC97SIY2GC1nR5gTZK0mT2d5gZRVs1F5BM+iOIJHLI2yZWUfNDT5+K14"
    "3Drli1FjKisvqhEWZehsjHn4fLTb8GlOQZIAeVHjWyY5uqhFO6WHxQbpUcSbHBvhMsxKliOZzOhNtGoBFWXBDIOg4WBq64PJHQ+m"
    "NuLYlEi5B0waDrdASN0X1agydJAJs08rPfInCGkB7IBqpVFrUsBEQsAAUFFjT9X4rlD5JXI7CxU5FBn9scdoxrAQhFvBDgGxLd5"
    "1Iuhef+iD/rXxTSxKjCsOrF+D64yXmG6rDRHQJoKSFC66kdZBpr3Aw/cimo4ywWYRRdXrwa67ORgDBJzR2chG8J+buZA802WQsiO"
    "ogXuq9YSMeVJJfy3GVhKlhgFPIuIfUI/E+UoHVZ5Esy8mcpCJGa7Kk9ycxEoLbahCuYL6NsUXcQe6MIcHmMK1+cqrlsjhjOFeIo5"
    "eZFX64uuZYYK9Ul4UhaS9ZhpMtM37oSg6oK0n+fjA+VA3rQWU3E7oKcbO+GBP8pA6smybsOzjDGWKQFAEkXnzsXe9vsMcJ4YZoFm"
    "PDRt7nx8dffxZyxhZq8s/OOSve3zUN12f7jQuX4Dc432w3vt66cj4PaZr3e//DQ5BUVhNPuMhAXTe+Td6CgyjWfxm7fas69i/s6y"
    "MfqI9FZcc7kQt19s3j6JW2SezsWFTZRWqxmqc7qncXUv8kZKJBrsylBuKyxJAtAobaSdl0T3ra6nbSmZX/UZ5T5tHNXTuJGypg5m"
    "ZXOQl7FdhAIEHriTZSjgYHlIywk4MDZlgA8mDswVaZI+63oPBkkQzG9BeAU8NKkJxiTPJUEUqIQ0AypRYy4B/tPKCp4ZroggaKJY"
    "4P9+jiTgDdxAuAwQ5kQx275ztbP5zd7lc+0Hl7K5ukadH6QBJq4qIi0xqDAA6i3AmPh6prSR4oETaD85Rdsll+7RHgNts+w8lA4A"
    "advyfVgWSqBXT3fOzIR534YKeYiN+I0KaH6a28JEcaa3tdq99QlD5oOWBGwmfPr4s0OTiHStfervbDqxEExz5RzMzuSgMMmPM5qF"
    "tLx+STLO5DpgAebQdkdAloIx3u3J9Lcx6FKZdXFyWdoczvKWXq7C28Q5Rh/rqtwcNQva1UBLA2kLFxM1M4AJtD2qmiHjldke/FJp"
    "wi94IrpjmIccMMPLhME4kQxdLvBixAllHCyiiXR84d498urPFCnaLN+33gx5Fsjz58TR6n1sIB5cl7JEmlgcg8wxQi4aAh53OQI7"
    "Y1pP9WRbrWyWZxEJbEfJ3CtLdXnmnQPo4MfkielDY/9Rbh2anhibLCsHZiDEQZYg8woqTql4CGTjmg9HT+QX1d8pSkGPd0bhGEBe"
    "Z1LhcBMAN4BJs/xXweAg+HhalaYtLGnhzwX9ecZ7iE0N2G6636xovvVn0n/yyXooeeowA3bzewIBr5Y4c4iVPhkDcdrp0+Z+XGRO"
    "r0NKrP+KRHiI2gyrJ5klqMyiUVGsWRzDxEMRh8YvYGCW5jDurMSAaOvHZTcj2VbrCOjGMsiT/SISpdXiFycso8cx3k+BtS8MnfZd"
    "m9AG0khq75rlVGsNk/jygqIowbznnpBe8TzXk7Os2zrQkdzdXm9fWO3cvYT1H4qTHauvD7nNSRPjPayE5Tg6Y296oTwFQnBGdO74"
    "5ZFIkV5zAjLH8rNWy8lP/BYuhZFML6hOGV2OIuROz0iEmzS3BKLVMuUXtwc8IpzSDwhRpgGWIDvqAk0uD0bw6oQCO0I12Idr5Le3"
    "erq7/RiyGMhcgPfud19lk1kbIkSLGPRaVP+PNWzahpfxcklld0sq1SmVqbYa3y5BZiDFySJaETF11k5jLUdaAhUjeOGUbL1gD973"
    "wEHZwnbt6K6IOpccJjeciunrwt0JikwZGNb40ipeARkQZNx6yrj55gRHBHQZENNyViYJJAObZ2hprc6j+et1S58Ff0tdjAQZh8zd"
    "rAT2J7hTEjrq12tWoA8zczvVMuJvqHGgWiNsodJMkKX9/qmY5AIlmdIlBTeuRSqEl7SpUa3hLDjuCeegzim2WhNTgBBiDmBnLZNn"
    "kmgCb4w1ih41eoDH4WyEBKRGt9Y/PSLcWnr4oC7oMLbCWKPpjQhCqzHpMO3zjyYPv69OPUog1UVnT9vC8FLKJErGtFVIoYDsb6yx"
    "RaJ8lHQpXUBKvILcrwxMMSg3WUtaxRipStwS8ZpXlZgTUKWkHUohb8TRdTmJl3u4Pn5FPDkJq0VEF70xrDkJm+ASdh2nYiJFAQhy"
    "TSUsKHrY8FDvEfGc3E+EVEkULfS6nNNgyNjx08EETJXfsqOEUyqS/PgA0tAIqEnTmVwp07l8p3PmR3DsJdAJbO+KC1I6QpasAAb2"
    "VlYYiBSmCh3RiZ6fLDQZ9mm6n3LY+fSj7r070j/vS7zlB6XvZNS2LnR/+DvN2YU3po1vJmWpyG5nP/gC71hLmfDpzkb7/O3O9RuI"
    "kbXIYevRXSAg4PeLiLzJFG2EXYNS1vk9aH/NzS8Kx1BE/ISgvmBHBDWGSLaaPNwSHmqbPImhcttc7T64CyKKshkYbN/8Kw6KtIaO"
    "rZ+l6TkbxhQnx2p6HHGhLmZQp/6x++gyxlcY5u6HHgUbglqst/Xp3hqcCU/pZPb9BesRQLTRC1LerxsO1p3wX1hosrlQylfoxwno"
    "LchyWbRloBzbO70Op4832bQoY52aBCgTL9Rj4xUoEyj2gsKbxVg7hM+6h9h9cq33w/3e1uXOJzd4zvDFZ3B+h/618vEkr726Jx+i"
    "GKFEex7GX4zHUZIw/u8wfuhQYkKIE+YOCUTYmKCzfGoDInzvH3clsbC9+gmdTQgZ1GZ4XkNr1nvrIBLUUiCz+/hDkH/n/IXdJxvt"
    "lTO7j9eFNm70Vs92L91pn7sUHRA/rysngYPdxz92L251zz/p3H2v89EWFKmdm/fb579HYaQVlxtt7KmhjqyD8dfYRXlgBA3wpIW9"
    "97dgsbioxyJ998dr7ZufJreAN/bJ421/dL3zzUUQk/jKgQqos/k+53DjVvvMOt9ags9IUpRPcdq/oH+V7E4JU2JtKaYKceOJEXy6"
    "c76ve9W+87B9eztuZl270P16PX4FNfhbjAR5xFYUM3693/hhBt0XCKG98TnvSlE6J6/0th7FnS7mdODk9i5/zAaFrg/pXzEnxCor"
    "6kwLccsHLAiGolQpHMd3ywxnwoQsTIaCdpCTPSE6VHVN8rMtkJjEm9hVEu0LwDJIhEd307KJ40NQZV/VlDL/WrkI3iRNXcAuurWG"
    "TdAfJ+D2xV33LLxnYZ3+aJWUk2bePH5AihrAA2toQ/gNt2rUyDEWjGUlnBlCSx482iKNjPjJh9vw36C1aFFjJenbrF8CtJPUEjMK"
    "7j/pU1MU99MjM3UgdGYM0iKfdnMK4uDp6MtwqnOutxyRQXtn4exqDHaUrR3khe8/HBCy4wZk/6Obt+gdnVU1UP7cLV05yT9bQi8E"
    "xkZd1r2VgW0zNR/sEjVHEvGWiaFe6Nz8kveAv/+fzuYZDNC9r//SvfoBmjSnzZyk8B4YMiitgZbTwL0n3lNH7QfTraonPCsgL9Hb"
    "RNUnHlSNx0GbwS3addGPoLeUFTjj8ei6MnWJ0oAEy6zEzQsBnr47SeTw6q+8PP4/ukrhibDhLzvVOA0euPeNvv7jq7Hrhvcdqrj1"
    "5a+wkNDsjMMm7jEalqlTyWjVhkeToD+CbIsajPLKfQQe01U1xJX2qdXulUcQVLKiwB8R3LRa4iluemTHs0qrNZLusSC7dDz1cVer"
    "lXotTL4wMbBUbI4uFjsrarAzW4YhMRJhePHF9AZSLQHm8Ye2W2quu9Cos4qafuEpiIqKejpVkqt2OVlY+4Q4ohbnp1uQFbU6bzhz"
    "4k5Kx9q9rzTmYmmK6nb8ncmJUslsTg72Gcd5m5F/HEEZYU+F1LVUooHYalG+WCkvFqUlQz+Qe/8xJgj49V7vy9O72xexiU+TAmb0"
    "vN3DkBmmGSFLFBq+sUhMHUXIbu5TMKxspxDAEf3hLY+RuOWR4gscK18eStzh3P8esxpwOHiZQNΜdTGV2t1d6q9/h9ExED+kwmwUy"
    "oomwHxWeE4rypLd6mn/z+fBbpitrSBDsoPP5dvsOZDBr3b887H2z3vvqvc7GPUi6orU0D9yPr1Rf7ze0PnDl/rISKetgijvTdxBJ"
    "Oq1WuvEmepoDgKwloUd9CEXh+q3VG/48r5RynBsVwUJGN0SnIcDRUJPNoAp183rs8WWT36/1WQvHoDB4rVGn8pMhWAC8mhU3jNno"
    "Q2n+FQWMCHVUm8mvlmxeMauRAI4xxaQfy+Qiv4KORkVq5kvLOXCR4u1IkOsLTpDOIOv4rQ9yWnVt+sVqJAzRr+FYcmnJQC2IA2Yu"
    "5RzH0mCisUM/RnCBBSY++qnOPn2ecvi/+WDd8A4xAAA="
)

data = json.loads(gzip.decompress(base64.b64decode(payload)))
files = {}

for name, steps in data['ops'].items():
    s = (root / name).read_text(encoding='utf-8')
    if marker in s:
        continue

    for kind, old, new in steps:
        if kind == 'prepend':
            s = new + s
        elif kind == 'replace':
            if s.count(old) != 1:
                raise RuntimeError(
                    '版本不符，未寫入：' + name + '；' + old[:60]
                )
            s = s.replace(old, new, 1)
        elif kind == 'regex':
            def replacement(match):
                value = new
                for i, group in enumerate(match.groups(), 1):
                    value = value.replace(
                        '@@' + str(i) + '@@', group or ''
                    )
                return value

            s, count = re.subn(old, replacement, s)
            if count != 1:
                raise RuntimeError('找不到唯一更新位置：' + name)
        else:
            raise RuntimeError('未知更新種類')

    files[name] = s + '\n// ' + marker + '\n'

for name, content in data['new'].items():
    p = root / name
    if (
        name not in data['overwrite']
        and p.exists()
        and p.read_text(encoding='utf-8') != content
    ):
        raise RuntimeError('請先核對現有檔案：' + name)
    files[name] = content

for name, content in files.items():
    (root / name).write_text(content, encoding='utf-8')
    print('已更新 ' + name)

print('完成：請發布更新後的 Firebase 規則；補舊分項請選「只補續約租期分項」。')
