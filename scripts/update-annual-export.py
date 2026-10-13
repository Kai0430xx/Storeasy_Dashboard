from pathlib import Path
import base64, gzip

root = Path(__file__).resolve().parents[1]
files = {}

payload = """
H4sIAAAAAAACA51Z63PTVhb/zl/hzLBIKkKxE6a0dhXPQmGm+5jtQDv7westsnQdq5Elr66UxzqeSYCQhFey20AgZAtsoZuFQmhL
2Wwe8L8skRx/4l/Ycx+SZcd0WToUS1fnnHuev3PuxazWHNdL1XXHspDumY4tG44uDyPv4/gHN1Jl16mmhLLpopKGUT95wJ7jIiF3
wOQSNN+ryEYpolX6I+oEje5Ua5qLjruarVcQbtOW6MoRxzWQq3yJEyyeZtaQ+bHmoTa14VQ102Z03kQNpU47Y+pppAP7R9hzTXtY
1uyJodwBNE6FlH2bmpbSbNvXrJN0FXiwWOKaZOGtUJRdKoO+yRNIc7NcmucY2gR/keoHUmZZ7Ov/40D6D0Z9oHGwX/HAGyJhkCSv
4jpjKRuNpU66ruOKQvDvZ8Hmt7sbV4PFufDH64KUO5DSHRt7Kcf3ar7HtlYLxXgdFNJHVNHTXPB/FiyRNd0Dvelj2fd8F2VLjmMh
zZarJsagVKSbOsS4VNX2LSsvhKsP99YeB09WhCxjzAvB0xVYDeaehqtzu1s7QpYJ5xyRPLY4pDJxeaE1vRSu3RKyRCJ/Bn3LYCDT
uZRyyqmCoiiRR4sKBieLXRGXJMJiIS9lqpmc+ZGaGciZhw8Tn3Ljq47tVdSzB+vEnY0jB+tnqGWiKSk1zTgD+njigCykBalxVnZV
HrFCSTGN4uRkvSEPO2CMqzDFcV4pm7YhiqPEzeCeUaBTVZXuIskjNRNI6cs+SpGQTk6Oss9SxHTo0ChY5rs6ghWBZakgQeaUQRL8
jVxXs95WmMTDyd6GaJop2DJ1JKblYyRTolTRdb8GLpxQQeW8An/9FoFfdNgo/pTPi/Sj53gQufShQ6Q0ICqwCIrZHiKGC7ZfLSFX
yLdX+8kjZXovk05nSRpIcg25EKkqyEX7t0x8zOcJfVtR7GmejxFWCzSLRRKNhI5y+4lZLgvBi5ngynow8yD1608/AU8m+RIbJTV6
K944FiQ2eUV3fNuLGfd25ne3LpM6uPdIkIpt/V30Jx9wy1AjQyCQlodcEatDuA/8166oZHhGEexkqX0Ru2Ihe9irvF0BxkzYqSK6
EQlUp22Tk3SxU++8sPfjbHjjFqnJnUsJQQj0mYgl8XqV3lTFHIiUmo8rYp0V8CdGlpSUbGtVABuF/Mg0SdsR/IzhU1eEWULIPSJ+
GmHf8rKRYwvpYjKmHdL2JZj8hkzolpkhGM7i3iGwXZhMXPyebSdH16du0QNFmYdZLjm2n+QcGoRIPJ9pTV9LDaaajy++Or8FqN/8
6Vxw6W44twj+FgjUnDItlKXFxACEvE9OkliwQAsNklKNA5CEkCk2D0vuQCPqYxqesPV2N9NdBG3xl7Sn/d5xR6AnjLxrR2N5fHJc
R9avzqiiNqaZgNEU3UQBkWXotpKkGKisgVviXkX2VGm3Y6xKrIiUIz8KVdJxoXCWngf3V8KbX+29/Nfuzt1gaj7YfCTEgqBrYvWN
/Tmyg9rAlG/3UexXq5o7odL9NMMgKuAKQqB5MLMWfrXS2vqadeHmxs7evbVEC64gDSYOQCuBkQnFXO8GxQlZjUB3MhtQvayEmj8t
hl+vnpWjVV6j1zdaswtnyVZcP6IaGCVyUdK79c92pxzVLB/iDEMBGR9YjRZz3CWITHMAY8StEYS56pCrROUNwEAKXMq1dXCJDhGn
xMQzg10lSv1kj6PoRoEoF8dQ7TKWSaFQGUlWYMeTml4RRVc2oTfWYZoCvUhNSXU+ASEAU5CmQAWfgGfRfG/g8CBsA8/AbntqveRY
RtZzfSTD6Oq42TqUeykrnDp1/MPMicwJodFg1LbjIZWLzzWiCmPbGAimSwv3SpxwfQFC2bz9BAIc3rzWfPaUZg3ngLK3/KoNeVNn
0cxG+SOPoImsQEIhyGOm4VWyA+mG3KZikM+oKJ5GZJnBBFkwu9n8x53mtVmmAKfvQt6Y8/0k5/q3rZXbMX83Z2+eeDeayd08DAhj
zg+S5jx43Nx4ETy5AijXre0+bO/pEKZvl5z9Eno7k3J1KL2vNfRUm1Voh7adXSPmOrqPi9V1Fxf+GYYO/TqbS2+fXn/WerQUJ19n
TFgV9vQG2411nHBhsXl/kzPR1I9ZkoGHwSK1++JiuLkYPlwK781xBt6qIpaj6UaxA6soThBgicqVFrlaB/RyGwk8AWEU1fYnbjIh
eyVKR+iLDIoKIK6ouuyHH2/+M7UEUw9d6ofZNUcJlc5YJsZytpBPTmVdLFjtCXAJfIsQIIlvUi4BYW37TWp9Ji1nBotSB5pJbw9i
jaTnGexQsYPyUfl9+VhRihQiwulnkVFJCoz6p6qeKqSVdPoXQqIRcfRqA7HOgFhXaMRVE5pDOj+QzmaO5RqdfYrCI1WAC5P5/kWp
Tr8poyYaI8BIBieUFeDM/mdkC/L4mZpletmMPMEfIKkYg+Z7zinaodQ6OeFn6+ArIGRaAiH0e7bG6OHpBB3mOQFbZS/0A3iNrYFL
SIwyklJB5nDFUwc+2PcFgQNoUHTqgP8RF/YfbS6kq1pqnRyyAHc0D/QHM/lDVsCOZRqCXB4+0Skh8+HgqWMDNLJSLu5EpEv17EN7
Dx9C+4HeQyl41mGxUBCCu9/DLMPmGoHORUUZVmGSnN0Mlx+Eq3deb88FC0+b09+83p4X2NBESJrrF4LVq1Bk4fxUuDpP/nx3qXVr
MbzzoLl6eXdjiST90+ng8c3mygXW1l5vXyEXGAvLzeuPWn/7e3Djye7GFPvUXP9na3oj2Pm+deelQMSzoWjv24VgfpZsEnfR1XlW
cyA1WLzQujsTXpmFdRjRWufXGBfsw+Fv/mowt9w8txmt3wb25vZmMLXN1pMHn1dT5+jObI0BGuwct7W9udmuBrO787K5tNY+XoF8
Bp/8w+IFUDucvwy1z5o/Q/1oI6YINY7jCDPx1dR0PMwTsfz93iMmnOiROPiFq+eDuYvB3AOC8vc3mY+b15+Diql0bBNrOhzPBfIZ
JszEWWN360Hz2UzweJlJSZ47iDdBwdmHe/eu7K3NNZ8sN69ea83+JZLNZ2LeBsGY71hOhetLe9vnkxMQ0w22SrLsbn0T3n7ZdsHK
hZie7lCMkraNTFBvDGEGju77NhB9I0Aen4FISbz5BMRW2QmIgTsWE6ec9sHGNw2VXFAquu+SW4/PMXLzCqwS5O6D3/33dnuPLgcz
c81bW+RkFk24mk7OMvx4xG5HRYP8X5IFOCW60GeJMHJQ0jxNpI2hjzJNTvYVBM2omgASAvahwY2aMOHDC3Q5bRiRJ1StWc4Egpan
mLZu+QbCImUGzLNQr7tFdpWwcCN4sczKkZUynVXJIabzNMguGUGlnpq8YVPe47Gt1XDF8dSk7Vhs3xtTH0T7wVExFz2rEasCnsJK
VauJhjok1k0ja5ArBhgbDO6uhkQxEVkYpbr2xXzjT6FDmBgpMAaJ5LxEvHEGefzed4irHp1y8ORkoSgV6aaQAkNdIYvVlWnQeujc
cf+joHETQ4pBeIlAzK3A3ArcaUUsK3qIRJXUob6Sorl6xRyFgxbNkZiGXRztD3X4w18BAoOFdYbwMTQnDrOJs75aTw5i9HAZ7SDV
O+5MOyl1NrDxy1OSnPRuFB7ao27xHVNCphdKOjinQ4GCXvx/M6TRcfvAdv/Zy5Cu64P4nxQgkrywS34Z7OOyaB8et/C4MuaaHjpO
v4kxqeWU6JXHcXgQC4yzKPNJQKvBeKNrxPz+UdtQnBqyx6sWnWY9fMQpl00dgZl+FWBIwTVQ26C9vmop9JfcAnHQci3189O/YVco
6HelL8Gr8C4SBSIay7RH1FgcozxpIfImChokByFQKuR6GsSxN8MZsy1HM9Sz8Z3MF/y+/Yv4wiTGcuharAlRj5zNxZuVHAOO+TWw
zxCJXL6XDuaT2x/64qIqnFngDSPvM7OKHN8TRRg1iVkuGnVGEmaBfpIM4J9OSwTx/wuaOGpnmhoAAA==
"""

files["src/annual-export.ts"] = gzip.decompress(
    base64.b64decode(payload)
).decode("utf-8")

p = root / "src/GoalsOverview.tsx"
s = p.read_text(encoding="utf-8")

if '匯出 {year} 年度目標與轉介 Excel' not in s:
    old = '<div className="panel-heading"><h2>目標與轉介概況</h2>'
    if s.count(old) != 1:
        raise RuntimeError("找不到目標概況標題")

    button = '''<button disabled={busy} onClick={async()=>{
      setBusy(true);
      setMessage("");
      try {
        const {exportAnnualTargets}=await import("./annual-export");
        await exportAnnualTargets(year);
        setMessage(`${year} 年度 Excel 已匯出`);
      } catch(e) {
        setMessage(e instanceof Error?e.message:String(e));
      } finally {
        setBusy(false);
      }
    }}>匯出 {year} 年度目標與轉介 Excel</button>'''

    s = s.replace(old, old + button, 1)

files["src/GoalsOverview.tsx"] = s

for name, content in files.items():
    (root / name).write_text(content, encoding="utf-8")
    print("已更新 " + name)
