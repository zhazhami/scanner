__auth__ = 'zzm'
def decode(x):
    try:
        return x.decode('utf-8')
    except:
        try:
            return x.decode('gbk')
        except:
            try:
                return x.decode('gb2312')
            except:
                return ''

def tolower(dic):
    return dict(zip(map(str.lower,dic.keys()),dic.values()))