from pathlib import Path
import base64, gzip, hashlib, json, re

root = Path(__file__).resolve().parents[1]
marker = 'storeasy-text-work-v1'
payload = (
    'H4sIAAAAAAACA819bXccxZnoXxkZ4u5eWiPJtjCM1KN1AjnhLoQczG7OubLO0prpsToeTU+6eyQrozlHBLwYjGPfJTGBeAPJCcQx'
    '4SUkJzhgyDn3/pPFI8mf+Av3eamqruruGY1fIPvBVnd11VNVTz3v9VRN/1ArbAfJoVr/UBI3Zn4YxWee9ZMzSTVNzh6qHQrXu1Gc'
    'Vp4J/Ebq9ntJ8HirFcAjPD0TtPDPydRPg0GlFUfrFSvGetbCqY5o129E7TbUD6OO24wa7ukgfUz9Sdx2uB6mbtQ52fG7yVoEj3Ez'
    'iL+95f64F8RbbpL6cXqilQaxhN8K42DVT4IZfEjSKA70zvxeuuY2V2Xl6oysrlfCGT4TbboNGGsaqPm6m/B0gke67sdnqFrgN91e'
    'Byo2n13D/xMc0no36wAbTafYXuvCKK82EvrWiDpJWmn7q0E7qT0TNGCmi0kah53TLv+pe30eUs3avfLR8Le/vvXphdtvn7PcoBmm'
    'NevW3z/Y/fnfhud+P/zgb5bbiNa77QDr7n/wyu6v/jL84NXd85f3LuzsnrtguX6z+UQarEtAw/cvA6C9X31guc2AW+39/rP9l/48'
    '/PULw6tf7P7mr5YrsFmzbv/0xeHP3pJ9hwDmMdFmeP767Td+pwHDj8+Y7bSv60GS+Kex3U//fHvn+f1rr+w+/6EqfpwmtffJtf2b'
    'H+Y+mf2JjwOFwkY7apzx7DRcD2p+Z8vx6rQmVOAsdYLNyhOdtF19DDD5LBR9N4rX/dS2frI2/ewPLbeP1f531AH4J5LQn3nWD7tB'
    'aLlbgR/XrE5vPYjDBgwl6qRrNevIdDM8HaaAN39Le1uLerH2uh52ejhgWTBwqi3uFUeDA7G1IToOTO3Fj4fv//LWjfczyoAePBsm'
    'M3ICQWf6OyfuzwRKBug42Uii1FtMun4HUO0nyff99cA7dYgoGj6dOlTx49CfJkqG8t2rL+9evb7/wQ4Q4vDCL04dmqkrSMF6N93y'
    'YMRpG4aL1Jc04rCLPIavADw83Qn4U4/+dOMwisMUxtrBAbZp3Vu9DvFl5bHQb0enbQYIYuM77SgJ3MZa2G7GQWdA5NDnruOg5bGM'
    'Wvzes089+Vi48Xg7WA86ad3u9Nptx21gW1HFFqCcBSqtNnoxwEs9UbygxJ6NKyR6iNpND0RaD4FWQeqFG4HoouInFexUvC5w/dWo'
    'uZU1wLdqkm61g2q0EcStdrS5MO6jZ62FzWbQsRZgZnKAS1WSkycDFLFRvKh1WretsNPtpW4anAUpGvjuai9No47lLMHaN3qJ7Yhx'
    'nQmA8ILavwRbq5EfNx/fgNY4y7BlB1X86HnW40nD7waWY6AHIOh1nvVXLYl9kHHeiTj2t6ooKO3RQz7RbudGzcN0c4NPqL67nPqr'
    'YacZnAXCmz11aMVytreXV4CawzYoCfusV586W13zkxMpiFSAFNhWM0z81XbQtBwa7hQMrdoOOqfTNScO0l7c4Ukka2ErBRwcPly+'
    'pjBDaLk8u+L0g2o3DhBLjwUtv9dGPCBQ4KbpOQ27AygMKtTlhNAFiFE9QOcZ8MEgIxcQ97RqT4ZJGnQADxYsSTPa7FguPDgLPE8i'
    '3bEkhmUZ1DhYhy9jAQMLaPNdGLiwFqK3ymIz3DAEyHrU9NvTq37jTDOOuqcO1ctrVDbDZlBhaUPsDgIHmbkP/w0qcdTGmuoLiSJq'
    'B6Vp3AtM8cSSYlDsivVzFLVX/RiHsnakLuouzsDzIlNhJd3qYm1+A9AoEELQPn0hGQamLLz9+tXbV14GeP/v9cUZblRfnIG+QWZI'
    'IcXv/P/CQBNu3w2DdjOx+xt+u0fCbc3vnA6EUJNIrS9SX/Xda2/c/s2ri8QlgJ4f98DQaVbW/bNPEml7/bkjs4MKgfIYYpWnV5GA'
    'vX7g1eWL3a9Wq9wxC2uo7sdgpXHhwBnMwJC5azECtkT2r1/f/eXPFiWfwvpsJl7/6EAfyvzsbH4smiI4eES61hg3rtI1bhFWcYm5'
    '1v7Hb+9//Mdbn3761c3zt5+/MfzNe1/dfFngURvzI/kRS1118HCVVjsYh7ffvrx/7Tzbbruvv1MyJEGATVDRQH4mDnsTDAbV6gRr'
    '+eL14bnze9cuDD99d5FFrdmXVMsHd6gUeKHX+mJEayggnzrEGh6W5taNnf3zf1yc4e+Fej0A0wG7o773ySu7O+9k9WZ4qNlsBGsR'
    'XwVnyRZvsgStKDZTBr/d78YR+j7uaux3GmtBIh6eaLpkubts8QdxHMW1duQ3H8cnwZCnwDoiVXe6Ha2C9Fm2/CbYgZZrJb1uEG+E'
    'SRRbK9Ww02j3gIBt0VcVBZjj9sKmh86K1Ir/mgTxUhVKFxTcZZ5c0ATdl54UzyuedLhsy3JAHZJXgjXYP9G/r/swHKiDVnqCVdAl'
    'SLIai8IRWl6p2yC33WVhflPdp8TzwdWfJBcua0Lv2jjmZ7EuuAhUB/5q31o+qEj43Iz9FsF4DB/ykwTxLho39cZW1A1ogglYvo01'
    'RhM+5dvDciRgUcD3H9BT/nvUaW89DToQeAUrPZ29lgwVK/9rR2L9afVWUpUIB2sR3eR77URp2KAOv09P+e+rvWQLv34b/pahjDQg'
    '4Yyeigu1jXautHaX0d7H2uhNFOvWbTLVod5aiP4c9fw9fhxDAoClJGTU/hs/jh9GRt2im+/0YEFiaagDY8mKggdEtacE+Xwvey2g'
    'RDQJOs2xdn82BORxj130FtiUtp3WxJDBUEqrwKGeJ3lQawacHYI9qVqS4Wm0taUYQavYb7et7W2wt0RZkokEWeQ4hw/bSORYP439'
    'ZM1aYqly+HBaZY+9WZtSj1rtJviB1hJ8QX9wiv8SuClmiu3t5x7sp1L146OueZ/LxsLVuSnzy/a2nSqtt70NNKkJM6rBtTOG2N42'
    'QiV2ygJ0GXEJNjob3fVZ1UowGXQkRk7T7ck/i+CyglvqOFUgEfC8fIlid1VD9vd766uwAGbPq6Ln1VzP06W1fVHbz9Xe3hbVV5X+'
    'Q5yzOrIUML/06/Y2u/yr1V4XtXfzROpMc5GvFWmEhXLaY4GOgEh8LyGV1UiCM5GmijS5ptaeJ0V0uZRbCCiSawGPNM3a8orWdYe9'
    'EW8KvwO5Yi1Bbdvb2P2SfMVGOXcYXBxsAMsqKXpKEP7hwwRwPPE7fU3BoexbUOpMKjFwd0Ag6sp5iSZRMhip51BAkb8nWXh7u2Ry'
    'MEDmNOkLCjs7i0jaWQDTbq661qY0HyxXKWiLFgiEduLVVf8JkHQjqa77XbsJMqEfNmtNGLQLllKzCsvv284AJu8G1IZUBLihQqkC'
    'XQzczALgGYsxuzzi0tlDSUXT3oQEqVYlanU9jdp5QehlKUcBhtE3GxajepscxVBMoKYkcaMcQMwxhRWXRK4JdlNcFwojTLQ63C0U'
    'CWvJkoYOrJiIN9sWh16BJcGCQxkJ3yg4betmjkNL3NcxPNkyV9GdjxMKs0l0i5YsboChjY5g+UcRRun65Ejk2+DZBn7HRsQ6rsHA'
    'rt7PiiY/onQtiJ8EJCQpC5GnfDBQwSeyZ3E2T6/+CDqsgnCLw4BlShWVAxDNUlUYoivb2/2BisbYyz6GeFaAVOgBFh4sXIdwZS+7'
    'GysqdLuBQdHZcaJliu0dLX5Cejhsg9glKwBFplDNQFg4YyQvnRBB77BYzISQkKGOHu9naSm+VBt+2lizJ+JRXgcNi2oVeOywDkLM'
    'ljITLwIFU7wRc/+mZjUuspShvUGun+XSkJ2FTVBP0WZJC/quqpXFokojTQd1VNrI7IsiUtrEXWE0y3VgnVi6GmBGZhFLsJhAzDzR'
    'SaN/C4NNu7+KOxA1qwM2EyyzNSglBClkVFxQKixeaDCh0CT3/GSr07BbnRp2+4M4Wg+TgAxhN+k1GgDDA7HN1IAegZSJwjGwMeRF'
    'IoWXUYh49ijoLY23+v6mHwJpdThgK+A6WT1ZsjAQhMEubpE4ljIis2ACMFa0+S1nydp97eKtz6/efv793Qv/+dXNN/ffu7D320/3'
    'r1/cvbqze+Wjynflbl1l/91Lw5dfGn7y8d4bN4c3Xvjq5qu3bvz81udv3/rsIu4kvP+73dfevP3Zr3f/+MrtNy5/ufNTq5aR5sIA'
    'bCCwK7b6cvpCZQ0GGWJ90gae3fHXg5rYYEM5LG1Grz9wOTIhTSivLhaDlj7bBpQ+e6ZKEKZoTDB1862xFuGGgg0KQPRKIT+h64Rp'
    'oswckIOamUM1xy6jNkHcDvTsM8AFoiMBGz07KkZRiJWsJQzLkGOHAhylhxuc7dIAakKcY3j+cSHSRdGZYCsR7iCJ6jNeffkM6ZDl'
    'MysrjjOoKbADti7Ergz2PTCGKty3JyOwS5nQ/W4XPTReNyX1un6cJkh0yyveslLJfkEXg7WygiTMUA4fNrxIya8OQat2e8manW0g'
    '2+V1pduYeMwkYmP6DqwLARfGCFihrgFoaWee0PgsEBZMf7ZgDgjLTFSxcUMA9ChNfGkZu4IC7HIyA2SlNqE9yssnw80Jz74YVsVg'
    '76lDdTTN+jYFOra3VYgMdFIhGOu3gxhoFz9jQJ/D+FQIYPp5CCJKPuhzlGQkPCG5Moiw4GkPw72ipQI02l3X/Oqx/msm+pijhSGj'
    'gyofJYwOt8j6CGeAai8dfLnzqnLLv9y5iOLw958Nz3+kNuQrcgdCbl95fRT/g2wHws7JLVPbu3KQgzoA3/9gJ7cf4Qxw6Q7cFin/'
    '7q8ShpeXOQTnWrtXr3MQ21pxlzko4VrQryoEIrPZql+CVhzjgBoq/WBlBfxRZ0WYhiFLWrQPJRoIgYA+bTR9EQQJm0uWZEerZlk5'
    'HPVF5FCK3AM9TSAdAC8pJonWg/sQ3iGXXQZ3sqAOF3MURw/waBEd5RWJ6M4BVErjFVGEetZeOl8qsoCjQkpUdOHInSmB8SLLN5v6'
    'Dpitq51M0eCi1KwE1BIY4iqgntTySFtahiWXhStFRVITHhlZV4P6VzcvVPSsmBw5jyZm5njaAOIdFTN54fLV4UcXGCRMrtv2G8Fa'
    '1AYFpD7yTtvu+Su84ZXtwnDILLcjooLQtrn/QZsuJQPY+/APt5+/oTalCmPQv4h+OfhW7JeD22X9it0RY0epsRY0zqxGZwEuPaKE'
    '0YJyRfBaWDzrQzTFXoaXru9dvXB754vdq2/ltpcm65mDiOUd87cx/XIKirkRNJoo2v5W1EPFs+gnuNtcrABaN5/owlSyf/4lleMk'
    'FGClPyU8T6G9QV11izCJP3AX61cfDF++uPvxf4K9u/fHd4eXz+/+9r9uffbXvTdf5C7A6l2c6dYHDFuCLigblejS9MZJhJH78SzL'
    '4yAw9VOR//vPqWy2yoN9KWoxBAkNQFblQpamMH4uJ47ZTLaxKW4JggUbdU7XlTJcnJElMC8VihWiKlkHyVHvCzuV6BtmK2QvDjVx'
    'qj+Kwo5tfbnzvOWACK/KQHmyBhZLEwZX+b+fVIbn/jS8/OrwIvgdV2mQ0CuBlj2kZSHdJYv3HxECtepn8fElCrNne8RQ5TlRBfiF'
    'vyJXPdg3Q90c44ZRgbJk1mGkybZQc0lTpMZYpQRkMiksS/l6yzQE1N8cVka6CvOKtppTtWqN8ctYdautrxvyIgM4oYV4LpTWx1gM'
    'xRT/++prAqehIARaf6VLCVJBYfV1/SgnUFBQOQWPnhH4FpwhaSnlophawZemo0zVECbTDImMEaYRsCTG+Xw0mjPpwEFRinUujZMM'
    'wy9+Pfzk3eHzfwGVsPvaSywNUPPIsYG3vPvWOyDuWBcNL70y/Oji/h/+JCRGbZF7rCyuwYyDuCR/L0j9sD3asjMTYigsq2XF9Kdk'
    '5ATQTWKxDAOcmDpK4V57Y//aL5mcQe6MUQl6CJMtn0HOGC7YNMBUGBlDo/Q7gs7rszmFwuEB25LjtNw+mVp51UJpEn3VucmF4mEg'
    '9c0gUziA/G4Z3tWum+Q8YycOV698SdZhxVQTKWAA/ZifqSezvGnWQDGBNQair55qo+ecqGYom8wWJQJQQDDG2ETExlpuBsPgroaf'
    'fbr33oX9nXOqHxFlx8ayvwzHcoQ8NqOZWCxuiKKjT1nAtvn1ROpksyjQhgD+0Zugdyv9AqUMKsOdC4rTlEejZqSvcOlKMWWRZ6Tz'
    'SalBjflS08WsMhRZLJ8ofgOyk7O+czZvydzupg8lAwf1XJ64JgPHA67I9R/vp2L0UoRtQUK2QvAYrJzD+9XNt0RG2fmXOJi495ed'
    '26++uHv1hVt//6+9X7yBsUDHEexbsDlYDQBrZgnrLNtZ22juAhK4Wh25zT6Rtz2qb3kQgTsXCfGIVU6JnxiZ+VWS3j1HzoQ2k/Eg'
    'sbMn0i5EbkPBh5LBKXCiOL6lReQwZROXkN2RmESMVPmVl6B8NiGIKcTjIhQ25W4w8kWhi4g0WaqNeA4Ru4EQl5Vg5IivTeWTWVc'
    'Pm/esybl0wYkcBWRTCkqGaO7d9/PxqVGCvqaiXrv53+6deOzvQ9+89XNS/D/3uX/GL72G6ZrUOj7f/ittPn7mCk1IT3m93I7Xr3z'
    '0PwsoGr/5svDc+/s33xh9/U/8IwyVDFuwCpRGxSTOC1AyuyxMDic2KUPb332zvDqtVs3Luxe+dvtKxeGv7+wf+1n++9dMRwY6Er1'
    'hLbmugiTkaG5njc0n9PXCLwN0Gi9dC2KPdo7XLIw95jdCmWsyyp53aC0DaoFqIVCD01Q8gA++ZiPnpgmdSnBrPZWYQmQJNYzO5bR'
    'oBbaqoGhBMQtCFFXAFPazrY5m1E2upi9plDukJeysAxWEkOTG1JPNGuE9RJpoR3NEWEXRlImPQ8cxx2rAcYfcI8krLfwFBGbtx+9'
    'xCxy64tfMfeAblDco/gm0wqWcYAILLvClMsUgmbkg/mAK0Lp5kGnCRagkCSFVV1EyVxu/YL7E9OKnOytAluS1VmW0S+y0AB9HuU/'
    'LhTlPcvscTtScsoquYGWfJDL+uCZZ1nahuDbv3kDhYUQfMXEbZXSLeJPNNhBPk5FQHavvDR8/3UG9d877zJdGsEcHlNJjKpU4IHT'
    'RL1V0zhct1EH0FEybfEQYULQoGpnDy1LsKf9Cbl9vsjUXiGPxhPFVbljJsKNS+bhu1qullSocseT9WahmqG8NK83Ox6Xb6Hz3pJ5'
    'Li5fVdptS4XjffKUoBg8sx/uSir2m6JN5H7G+spwMC2JAdALe6+jEACGbbe++/IORrEICcP/EuyKyuH8f+y+/DdWQ0Ib9EVLUgJr'
    '3ghhKyrJkNQah6TYUVirUhpJXs5DMQh4KqAauPuL6ykdvCWoIVw46b/dfukioA5V1i/espyazacyl2Xzle1t+QiaY61asPiwM5BI'
    'kkaew/cH+1qaHtlCFNyXrZ0l9qS3t61svUCNSS8ob4netY0oslSN/Uy7if9G7WCKLF4oQ3Q7BjVsVIOzsCSJ7SxtiF3CmqAQtB0p'
    'GCFOpr58cfjFq3mTDPGXbXJOaNjo21q6wUrJDsq82f3VX8C8yRmug76YzSjlKj5TiONoXQ0dTMejQNBxUO//r5NPf7/KO+tha8sW'
    'DaqrQQuzkHHy7hH0M7GyBgPnfhAMH3ei8yCkAqqPFyKLdUVgtIdpmNsqijcJU4Uj4rwH2hQikkbBuIW8CBlQoE9kGgM/6IGqggEx'
    '8fKP1X26u8XBxqLTpRQ74JeV9oGKuchTIDjLtYU879iIep1UsFzuXLkaN+6RURa+Fq8uS8OQp1E44q/nOlM+s7ta5c1RZ6AniTyn'
    'UmpAEtFwBpVbn33OIuo57TTiGL3jTG5vUH1pc+Cs6IRiUDkYgta/O1KxkZytGeAL9EYkx/bZCF1O0ReO0DFqwE8Z3ryUO+GE4Gmf'
    'oLj1pPY2ad1oa9M0XbQNTvMD7TnwJugSdZBtECdtXK9Zd86pmV/KzkgxDIwNX/ng1o0dTo4aeVIqCbp+TEfF6sPfvcmVURtffnH/'
    'pet7F6/tvXdhdFvaIcm31HZKxpy74kN2AZS0g9NgONc5gC1HKwozTE9l2MlUQv6s5eSBA3OZsiXJIV6l1igO4xLcih7NdKu0iYG2'
    '57lrMC1w4IeXruz+9Ty/avqu3HkkuNOMOYoNju5JhNRJRq+yjNY2TjPs6bRlxX4zjMCkkSF0MPo6hf71uHoOKVm6As3zABbI4TY/'
    'Gj5wUYilU76S2a/LNXODkek5oZbaFmLCuFyEGcAfiT8VeldpCzMZEXbrOWTJzT8wV4kykSyBtPd+fo3105c7z3P4Z3jplds7Hw8/'
    'fRd3Wsi2HV56Abd8P3399i8+uf3C58NLH7LhT6mJ1u6Hl25feY0B7r354ihoOgNiw0FfxJRw5+/Sh2K75/O3ocvhn/4IgBgi92Hx'
    '7sCMjKf0x3kO8pQrhydY+WaHc+U5YXbp5kef0iX0kSd5AEFQgGHMAdPaIh9r1gHrMAXAQTY7SgU7KIFMZIypLboR3uMotTBVKhnA'
    'gMFmS9ntHODDFrwv5SeySrHkZR7WwNyR1X3TxRlWXfSG4pN0I96TAQWHXLp4R7sxJk2yi3fMK3fu6K4dvkNncy2IA/2KnbjXeRZm'
    'nrCDA4o5BvMULxqhXHw3e5J38fAlPSIz8j5cxCNO5qJUq8ikXPNCHMx/ziqyibVJNdtBUn7UFhPeOsAGsbWSb0mz8ewNymoG7wVP'
    'bXn1DXDIoqfCdjtMlqq2s709m7VTh4WL56jUIbQ4aARhN11SBSPP9NJhYZGFoefY6kcojIMTMn1rzJELeeBCJHyJoxYu3g2TO29x'
    '+LB294w4byHHXk2CoJOd3nAon3lQgoakaM/W9POd2nnoZT47je4CPow5PSouVArSZygNP6toEoM8olq3AUXjT9Vqh+HGHbAuPzTF'
    'sxP7KjQk7NBMysYICgDZ3p4SWIAnRZgjDnvrx5i0dGcPr955yu8uMkG6GnZUUnIadZMaDXIjAjrC7OgV+a0RdQOVM01n+dC6v6Nj'
    '6A4D4VTpkbnOnOReIfMeRJoNHmcl9GYXwkUFTUlSvo2FxelC+JB3dNbo44CsaoeFlW0peDAPH6+RwcSKFHyCZBomjLcE5foVRnXo'
    'hg9Bl44YsugaBv2431iz7R+7IR05AqzyePTjZK6diOuk+pxADgsPALW0abspKoxOns7ICL6IBaZnBilSlpyVaqvtg6tJYFNw7Chd'
    'JgUGzKrgoRJb3XBVck5HTrJ8OqMwTYSdYRqIGXAMag3FlyNPMDL1l/imZhL5spx7FXn+CfDnxPvKmIONjnaez1bLIdcI+7fVITcY'
    'k1zrJSJZNxdYUR8VJTh8yEaI237hIgd3zU84m7CmJfjCGtynrNoBS1AlOkkS52WmQ6HYvHxyAFi0WUGyERJn/70LHKrce+Oz4bl3'
    'LJXM1wfM1PLtUbxR4nRN8gcIuhgLtrcpRfv/fD68fHF448/7b7xlDYy7Z9h2tsndyAappClo+F47lRd5nST0c2UV1LQcEaQ3rmsx'
    'qmofjAbqwhSjtnn0XMLuBTUBrEdfsvtGuFi+wjftAjE6pcqTkAPW32Se4dyR2eIacP7v7bfP7/3007mvPv81VBq+/zrrGgAr4Ghz'
    'k9DQofb9yNnIj4+U9MTm+u7VHfDAsTF0A26IyvHhD49kVQta4B4MxU2Rq0x9j4hIKctl1LJvrkWeQb+OGzbB/hKy7WSQCh1dF2um'
    'cSGpylDZ1tvb2XN9bna2nNbJDyIkw+x3LrAXpKv103HU6yYe96bcOxH1sJawD4qEonDiU+5QtLKAKktsBnt0zBRPxaEuEzezyWFX'
    'opbogrBQya6SwwD6GA3p+j08lZWrBQ2180GOZgGgSQdePnpRGuc5ruYfTxIkfMKcr6uvAjVFJIAw5tBVDmvSKRYPWdI+5cPRCS1X'
    'nlPgN0oe/Q7GFmuzrp47Ba9xgInKET4KTH97qwYEREJJS/uiMjpHp3bnazkXBPhcXZBQ8k2le0EHFEo3ssNyRQCBCsCRTDki+QQK'
    'Tlgs1LjCmK71UXjX+stivCvFXgd8xFDEN00XCqmBOS49K8xJeCL7ASmA1poXXxbTANw+N1cnHUQ4tcaqxCXOUyhUW18ZAv0y7Gjr'
    'wE45zBev3wMQtK6IjYE5GqRaItVsI0hiyHH7vO/BWKT9ixpNSMCAP2IdH3qIlLZ5hDTP5Ril3j1/efjKW1msmptTtJoijn+9/btf'
    'qvS7r26++WBfWQ+DL3d+CnJieOHvw48uZqBkvAR05f7vXmLIUBOj3kJGik7GCclizFrJR7Zu5LFOsWriTawZvwkrwBSoHngRY2Vq'
    'HEUsOnI7dNztKNkCjfLCZcw9Irh8NVpoascXVsjz4C4sEAbey/sQl1toPYjVkGJYJlksZfBHX7ng5ho5tdJOx9zZQAOZkA+FAJen'
    'O4HgTyNXQhfsy8WJ2t8saiTeO7l14+Lw/V8Or16zpFsWe9CMDV1NpCe9VY8yvI2u6AIGZh5x6JjqQOUluZ0aa0CidlOkdHnZTrYe'
    '4NveLpSLbBezX2luU9fSOYyzTCSGgnF4Gb0ZNf/i2URWyAgwu5AAp4b3flAYMEsCzLoxUiOLpk8hdW73/BUd89ghavEuShf9KLcQ'
    'TyBtPE1EqVfa2mOj3lM3ZbBY5JWoojePBFHl2ABOK0Mxp+GySBeBBdZMnqG3kZaYruX56sOH9UiP+U24E2e8ulm+fGYFMMXDW6rC'
    'mzPKRsQjnb99D0Tlrc+ugGXIO9BoK4INRVdQ7r97Ze/668MvXtUzHShXaoERJrpZIHSRISKOtcOTmCIrPLnMjlAWdIqcWokdP1oR'
    'T7RhnSC3GkuSMQQuyTgk4hHWPKV/x7nU/VIjcXhOJK/jBswL17JkCkeNVx4dkKik0wMwDHWkQPVZhmHtJu0cnvmqbYFn9svokgPZ'
    'tdwLFraHxycLSno1bJisfEko+zKzJlerU2rqaJUKlgFrfh7owTSgoOaooF9CBkQBxtJ55ko+pM19aXquNsfCV0OIYBb2kmwCKM5l'
    'CMvzLmy+gdz0ZgpVn0fRqEqHVyQaVzOLt+6Vei27H14CR0Wc1CEHjQ89sAOjHdw5P3z13PDye1q++8uSbHQZJTQxCiMlp7Qyqp+t'
    'l+k8jLbb790gv6sFMKxMMQuDaLy+5lLo2H5ozvQvcvQ0594rbYwiAnGOQFezSkEquih+O3x46s4ir0Wx88K5Yo4r51hzRkuJfFP6'
    'HIVbcRIjTZpMuJFAk5CFVIjl2kgiKgAeaCIj5msvoMFInGpHMnS8GhaBqRbGRAd0eV/o5ZlvfjnElfmMKq900gtlKilbOPk42iga'
    'v16jpLiAO1goEdnUXizzOEYzVOjSbE3mv5MQz1TDlHZLga5zvyaxPoLOZCq0Ya9RfrUZsYQSPahIuogL8X89fFdCh7SxnkUDRZxO'
    'LomS2WIsKLPFwlAOPqf/Z069OrgwmRTmIwxlMl6tsuhYX+jRqDrApTAQue5lzon0XQh169vb8lwDmK9ialg2mrAvXd9/4XO2WvF4'
    'K//Ox0vXh5/8iY7nXecS8OtFBvQY7AomWF8oCmcjtY2n8k0TRcaUnCohVxAzWcVz2UILzuKFy8PgH9LgtSc44mUMoINoo6gnblzc'
    '/fmHu5f+QhdyYb6LZfi6HDdjBSC3pN1lzZBZqRnfJ3RP7pjI21aR9LbMjWNjNtlwa64Kh/BNhgXPCyNAw6k46dbYtkZtykmqSpd'
    'JpX8MEzX7EzWOLw8uv8jY38YyBDljv7BiP7JAJLW9b1G/gxkSJ5hi6ksPV6qJpoIy21d0OpBQgrNjIkSMmVxw4EzLtpWuJswC7bp'
    'ATUtcDZ6R19symv77PK3luguy3u/xhJ3EkQi2pgLLOU+E3dbGI3cRTA3Yt3nHsS9vMG/P9gXV/MOnps0wGXeXCZjW0GLb/mjcck4'
    'VSHTo+4VhqnHrHFMMuwpxuUiBOJqE6i8hH6lpoiRdio4tcYW3QwmIQq8/gvJQJ5xNeKu6jcw7Du7qU1sTWv3tI25YA59PLxxepKr'
    '0hZKc7caCSZvVdUlaX0wQqc3w2a6VpsdVPVbFvrNMOm2/a1aqx2cXfDbQITTFGutNYA6g3jhR70kDVuc+wAltaTrN4Lp1SDdBLQv'
    'nPa7tbkj3bMm0MrakX4L6k8n4U+C2twj3bMLwGqnw07Wu7+amF0jpEcyQPC9wolsffyxFtwP6zRrD7RarQXAMgimB+YeOdo4Pruw'
    'SoiszXXPVpKoHTYrDzQfCY629I4qVZn3bcASABjc5hrMWrQRtzUVx4czlTOZexh6nC3DGFaf3oyhPv5nwuRgWx8EgViOI8dm1aRF'
    'Hf55Nrdq3GRx4DqZ+JOgqLtlSt2VubkrOchcRxSamcL8qc8jpWVcC8LTa2npkvJ1Rmqcp2MQivjfNIyyiwwIPbZ7652kBsSIkvDI'
    'UZi6e3T2W05FlMy6cy0wCUQnUGgfxjhrNPx2A7miubFWma5QO6B8pGlR9dg8FJWRQiOYb82JD9OYpdxLeBXlzw3V+AetFnJEJucE'
    '7NpXVUHwRwoW46HYlQ7nkZbfaoIj22yC6KjNzWrknZxRmKKLXBcouZzWtdYOWumCQPrs7Ld0mCnK4a4f8w96ER8cefhoc97PzfE4'
    'TLEbJSFtEsUBoD/cCLKRHDNGuHbjtREmXj9zhal58hWcsrzuZ4aDk3F433M44B4dCtAdMstMNOIBdurvqwnMfDx44//OgRDbTi'
    'Wkmwwh8cwc7BfBC0GrJ9HAR9gZLVCMTIur5WwZHAbx1T6DiKnCwaNqOMhMMODVXMCbk6WQMlcKY2K1ZH44hHFP3JJZg3V+6B5vyR'
    'uaNHJDJwjWuPQiPAeRoCgYu1XwdybEtBJGfclyOdraDUgWaVIxkxKbwIeTkxXUmoOIzxNHZ0df7I8Xl9XY9qPGTSixyVdgmRKbwI'
    'k80wZk1ZY6mwoGkonbPVutCdQQoRcxq+S9Z3Htb36AJKWSkgYLoGHyuwKmOmTypgmvRbrRsHNKsRc9QxkfES3pJTojRQNJk6Ic8g'
    'kgPmjx9/9KgAJs7dj1VCxFIl8NV4eLcyJ8Gwbm1Orf6RWXP5H2jNg+BqmDA0jfXI/LeU6K8gwIpQhfy5FabSVjBBVKPNTl+nfhqM'
    'KIiNxZY3L7Bs0ZA1pyGLxMWCSewCmqCITFLx7Qm6uKDFLtMYzeBhIJ0SjaFID2vjqic/B4JRmKmMGugDwbGg2WrIEYnZN+eDudZx'
    'E0w5yeTtN6KUoNMspawj+aFJmFK2mGsxqBr3DWTciWDLGUG3XNRQxNyImg0p/WjrSK6PijxH0hdkHAc0HClGRXW6MUSN58i8Rjer'
    'x4NHj5evBx+y6Gty49FjYHOYkkPQOVonj86idfLosY1Nx4CAGcrrfZ1HH871wTZefxz1amY177BMYlrFQTfwU/uoa1hUTt5ON828'
    'ewY8S1SkHZ0vog0nTRKB5HDiO4TlJm7OeNT+FUGBVZmFw6yAHIK7WCSncQpEkMSEYoKSIZ+Tt7fieAwJPOx1nEQBSW4VG5CbkZ6'
    'T51I0w2m9V+TZ5b6EVTFRNbq/OCf1wMgVjuT/MdRVTh9w9wfa+HPIeO5R+dHWfjHjyCh6Ha8ZtbkNX7By+yXKj0yrTXLRrfkZfF8'
    'wXaSn1gzHc+LwaRfYsQXVeOj89/Ki8TSMZYLs+lVPwkTMs1Mvi/HMSCynJvHMvCRHAPr/jhS/LFSF1zOvuBgFvxZbfS8gLlYQIZ6'
    'ybI5DA1OdWb+qYJ3/MZ4KW66FlT8brcNsh1nZyXipw4r4nJJv9NkyVFhggR6TmQ77IZIv1r5p5lTHZOsphHOEd7WHjZwdIchRmUt5'
    'w58+/GSafgSYXxB3KG+wqt8EqdeJOsEkfn3OGo6jzbxsK5WTxWYmc9Sr8rps16S5uvhp44K+qpeEW+aOH22B3S9UJwZfdD6o5HxB'
    '5ZdJh1JGagiKof/qJieP1HyChgrRpRHCshjmElJY1+nHiuoJiO5Up+NvCHqvVMENXDYvZvvi3P4X78oUi9yPja/0i44exuUG7qG4'
    '1w4wFlepzMxUaF/YT7ams1Dd9MZcDVREuAG8KlLAK3xcpBKu/dSlMoVCnETqaPAqDTW/BRDpUbWKEaibafSlwn5fEeUKD18uCK2'
    'mm2HNpuBTSoHnmCsDAq9nMTDTHZT60frG3oR9+ufB9EgKLt7UpTOyCFP4rdUQdmYCxZr5T1t0zUZTifllZdxhdnsHoJ57jTGYe'
    'tOWzMyN/ySeZUYFX+I4HiihcWgaf5Qj3wGX3r9enoxOiz4weTD2jJ4X7rXfGSFI4S2u6jtLY0YkL9b5GkclN2juZFg/8PFguDYq'
    '39PwJ8fk8w1MnocnyYMkpW1f3INBAvSz65k8L6MzeQZJVEmzxngilUvlfpVnokKVl41Y/Fw2Dpj2OMUQm3ykpxImFd43wB5EYRUV'
    'oe3UZ4tli97ckVneIqZvWnQiD0o/6iMb446v1lqe9sk3VaeAZLtHjD57uQY2lXmeZTE3w0t1HTdA8UdIlmeH13pHxtM88OR7MFy'
    'HA2qPBHFckcinLlnb4romtQmdj3Ksh5OUvaVJaFCqBtT4nqVE3L4PAo4zZXzNRQ8uFEysViqBWcoT0Cch6NBvSRH0+k+CmVm1Li'
    '/A0REiGxojEO/bQI05G2GwVOLTLA/RBRuqgQ5A/uc9SLwUTC5mP4NDciKUDuy6h0UXFvwxICJBMfGfq+OelRPoeFMkGvgH+ZZMU'
    'nZIimRihxG0H9Sb+AIW9bJG4EBuGgv/xeLJgafzQw/8lv2EB/xCOYCV40mhaf8NJ6+/0I5T6GWjtRBeaCVGTqqtsSXjRs7bgVU4Z'
    'q8nkz+xZ9qf95KXKmYBnfc3RROHdcWtFsiog3RTAxHfZITrgOvT5csU54ZsvX8T82qwDvUIanQzwsDRX9LxiY70FYQnHsO53C+X5'
    'VdVAOeMqn2i3jbr6QHE5WLjKA3TySN2KEOJ85E6W5i0zOa05A2q2ujiXsJPmi+vebL6ogEOdKgwwRp69BKQXLno64Aymkv40CSPn'
    '25sVKJTEZ/QoC1VvOpXlZbggObGKIhnK5F2M+CN3n4SV0mXhVLkMaIYtOqubFTlVn+6ACJr/ki1z524YfcUpSBbByvD4NYxPiJXJ'
    'hUnJAEn0nSQ020r2FQQ3FnRGSFWxRlQn8sq/ZWDxkr0w6iWeL+7DRI6JKkuVaFmWrFRqlb5IWJPY6uR4MBLvRGkdxlpUhimW2Qq0'
    'xlodrcNMSmilus7lyGXPpZB4JLLq6AHlNd+KkwNUrGFqvFJeoOv+QJPnaa184TK29rxRX3BU5a1Nlh/9rcgS+OFp8HYpmnR3RFdG'
    'bBqR8Q9u3r01RIFmeJrIQ2erAeRbWoaYuJqUJNyJYwpkUbIporKYM34AMp53HmoEuXUVtO4DH9i7RzL5KPmqT21WW46mgLSm0x'
    'Be9u3PlRGNKYwpb2fGn/UEH2L32CKXEA8z6MhcARMpUfIV8N7DD3GowQGYdP+LtJ6lHuCApB73C+pO7DaNOm04O0wCaDUompIEaB'
    'UGmaGeqyVafMb0VAJeWyAYxxyssQMxkaJkCCrSF7qTI9BxJcWTFMDUaFglasKQyWzp+tKu0khXnl60puip5nrr2JLoWAOyGFO8bB'
    'LMzJ6GcEXrQl1uaHODIal1AKwMpF+gpkfmeYlwNzRthZtNUyqeDeyEmxBXFod827Y/4WR8B1Dp+Rm0JcKISpY0peliEsArBnQpBS'
    'ClRCQsvzNvIyVl8WmeEN2JMiSkHbqBpSrFbJV0DhavbEDcpxHH1tWlGmzIop5jhL/XaAeatv7hTICmufAhkg2UU6yZXpo3LNVSDH'
    'goyURMniQN5mkKnsUg0M/ZZ84wR9r1PsRHIkhbXK5PZk8xspy8cK87vFXUeI88gU5TSJjuT3jhmYKwu4dPJBuvKgS8cM2RnRl1qF'
    'b2QfNV9xXHDMbCcj5EdyOOXxHIFoWh0OXWnfRokA4/b8qKmgZz++12tFmhowyVsKXt4JhO3oJWmeMxqnq2tZPFqUr5P4v2luwB'
    'lWz4SM+m3MDX9oUU3BGOhIwslRPY2EajSG6yLk+UxAHLG6i4ltnggG6yiOLsmLFoNsPspA4TVRwVA5A264jPuuEysjt5NMvri0vU'
    'K/384tR0TAwGCqAZx5UFpH40GcZ3FeU+mwLahFiU0tL0LxfU5TpO4xNe07FsdUdccy8RmX9MbHjC0O8dBHUnYIXycnaE7o757tr1'
    'u7PNlNEEbkbBUGVkQl2nOF4lojyrfib2EWSgxEH+p5QO0mjdYC+wc6b91N6kdI1IL9NiS5N3VKFkcFWO6iODNZne6o6bjxPjlnW'
    'y/aBM6u4HMeF/REGZcm7m5D+cUdH/hWETGeuNBqVRrxkiZUDO9YtWHlzGptsrvarrirmIHmMuhW/FTLap3QnNYoPGqWMcuqB7RE1'
    'BQayugfBZmfXHocew9pcymceVLOznmDE6duw0KfuP93LhqKvGNAgWhYKbjlLDXTGUrAO5CyTSf4H8whrQKRO7MtauVvUcOyLfhBI'
    'w4pyKLs0QiR/e2w+Ry7zg0OUQpUz7HzYMistJalR2luMPrf/QAPUM4D+8buuk+yWrjiFLVA1wX+YyDdgl4OWCo/QXm4TUqaTjxi'
    'ooJuihFdc0tYp4dCnPfejd5v1hW5Yy+khJe/8YUqWwGj5YG65X+s2atbBrZdSpVZ4KaUiv5Bs14xo9ulIzdDQ1/n6O9i99iIXI9h'
    '46VR/HJQLOqAZnfBoRPHrMpXZJKdh/uxFoINWKOUU4beL2A4F+GR0zG1xAQWhIyui9+SH2Sh9exXc4uGBYEPxC35+lZzLkJLMbN7'
    '2mE09hfVVUJFQ4KFoLiX6O6tnWwzVrd2FCbuk8Ejh3mQzROcRVuE71RSDyVZW3yDkCFP5aVCWaGyWJp0y1EhMxavN9LzWGXmaWaQ'
    'GJXqMs2HexqbNXo3ZpE9UifmiM/5mm2lPK0rjZsRm1TUmsRcoGmkKaU2mu7eiBJLcc9mlPx18slldEaa98WEygY4ZWekjNJ4tBkE'
    'NTNKH131flpnXxNpHGi8MT4nXbGpA2hghBGlhz3ul8XEAK2JK7WyLJgOIupx3/MUdLCpZQZy7u8MMzmcF75j+XJMcAhvqsMDAAeB'
    'KOBhYosgnxH/DNsF4jfCMiuAAYFmLNmhsu8olPuM2NdXXbAszwWP8ez82RtRGUxybkLBOAKe66uTmJoIMrDW2XgdVC6WJixToP'
    'Wf9uPTQqEIg3VR0Qjy8YC/wLTtwWA/tB0BlLclhBS3wcXUlLzJ5TgyqRluMm4xwcRqcDgIcG/x/2fibeh7gAAA=='
)

packed = base64.b64decode(payload, validate=True)
if hashlib.sha256(packed).hexdigest() != 'd39710736dac983414e13b08d5084728c6ba6228128549a9727bde31103f475f':
    raise RuntimeError('更新內容校驗失敗，尚未修改任何檔案；請完整貼上程式。')

data = json.loads(gzip.decompress(packed))
files = {}

for name, content in data['files'].items():
    p = root / name
    if p.exists() and p.read_text(encoding='utf-8') != content:
        raise RuntimeError('同名檔案已有不同內容，尚未寫入：' + name)
    files[name] = content

p = root / 'src/main.tsx'
s = p.read_text(encoding='utf-8')

def replace(old, new):
    global s
    if s.count(old) != 1:
        raise RuntimeError('主程式版本不符，尚未寫入：' + old[:60])
    s = s.replace(old, new, 1)

if marker not in s:
    s = 'import WorkTasks from "./WorkTasks";\nimport { useWorkTasks, unreadThreads } from "./work-tasks";\n' + s
    replace(
        'const branches = [...branchRows].sort(compareBranches);',
        'const branches = [...branchRows].sort(compareBranches);\n  const work = useWorkTasks(profile);'
    )
    replace(
        'if (page === "users") return;',
        'if (page === "users" || page === "work") return;'
    )
    replace(
        '["targets", "目標與轉介", LayoutDashboard],',
        '["targets", "目標與轉介", LayoutDashboard],\n    ...(canWrite ? [["work", "待辦事項", Check]] : []),'
    )
    replace(
        '              {label}\n              {id === "users"',
        '              {label}\n              {id === "work" && work.hasUnread && <i className="dot" aria-label="待辦事項有未讀變動" />}\n              {id === "users"'
    )
    replace(
        ': page === "targets" ? "追蹤目標達成、年度差距及各月轉介紀錄。"',
        ': page === "work" ? "追蹤據點待辦、子項目與討論。紅點代表其他人的未讀變動。" : page === "targets" ? "追蹤目標達成、年度差距及各月轉介紀錄。"'
    )
    s, count = re.subn(
        r' +<input\s+aria-label="統計月份"[\s\S]*?/>',
        lambda m: '                    {page !== "work" && (\n' + m.group() + '\n                    )}',
        s
    )
    if count != 1:
        raise RuntimeError('找不到唯一的統計月份欄位，尚未寫入')

    def branch_options(m):
        text = m.group()

        def option(n):
            v = n.group(1)
            return (
                '{' + v + '.name}{page === "work" && work.tasks.some(t=>t.branchIds.includes('
                + v
                + '.id) && unreadThreads(t,work.reads[t.id]).some(thread=>!t.deleted||thread==="main")) ? "（有未讀）" : ""}'
            )

        text, count = re.subn(r'\{(b|branch)\.name\}', option, text)
        if count != 1:
            raise RuntimeError('據點選單版本不符，尚未寫入')
        return text

    s, count = re.subn(
        r'<select\s+aria-label="選擇據點"[\s\S]*?</select>',
        branch_options,
        s
    )
    if count != 1:
        raise RuntimeError('找不到唯一的據點選單，尚未寫入')

    replace(
        '{page === "targets" && <Targets',
        '{page === "work" && canWrite && <WorkTasks profile={profile} branches={branches.filter(b=>!b.archived)} branchId={branchId} {...work} />}\n              {page === "targets" && <Targets'
    )
    files['src/main.tsx'] = s + '\n// ' + marker + '\n'

p = root / 'firestore.rules'
s = p.read_text(encoding='utf-8')

if 'storeasy-work-tasks-v1:' not in s:
    pattern = r'(?m)^[ \t]*match /\{document=\*\*\}\s*\{\s*allow read,\s*write:\s*if false;\s*\}'
    s, count = re.subn(
        pattern,
        lambda m: data['rules'] + '\n' + m.group(),
        s
    )
    if count != 1:
        raise RuntimeError('規則版本不符，尚未寫入')
    files['firestore.rules'] = s

for name, content in files.items():
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    print('已更新 ' + name)

print('文字待辦完成。部署後請將最新 firestore.rules 全文發布至 Firebase。')
