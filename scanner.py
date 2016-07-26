from urllib.parse import urlparse,urlunparse,urlencode,urljoin
from bloomfilter import BloomFilter
import xml.etree.cElementTree as ET
import json
import asyncio,aiohttp
import re
import sys
import myfunc

class Scanner():
    def __init__(self):
        self.sqli_bool = self.load('sqli_bool')
        self.sqli_error = self.load('sqli_error')
        self.form_pattern = re.compile(r"(?i)<form .+?>.+?</form>".encode())
        self.action_pattern = re.compile(r'''(?i)<form .*?action=["']([^\s"'<>]+)'''.encode())
        self.method_pattern = re.compile(r'''(?i)<form .*?method=["']([^\s"'<>]+)'''.encode())
        self.input_pattern = re.compile(r'''(?i)<input .*?type=["']([^\s"'<>]+).*?name=["']([^\s"'<>]+).*?value=["']([^\s"'<>]+)'''.encode())
        self.input_types = [b'',b'text',b'hidden',b'password']
        self.posted = BloomFilter()

    def load(self,tp):
        tree = ET.parse("payloads/"+tp+".xml")
        root = tree.getroot()
        payloads = []
        for x in root.findall('payload'):
            payloads.append((x[0].text,x[1].text))
        return payloads

    async def get_forms(self,url,session):
        response = None
        Forms = []
        try:
            response = await session.get(url)
            response.headers = myfunc.tolower(response.headers)
            content_type = response.headers.get('content-type','').split(';')[0]
            if content_type in ['text/html', 'application/xml']:
                body = await response.read()
                forms = self.form_pattern.findall(body)
                for form in forms:
                    Form = dict()
                    tmp = self.action_pattern.search(form)
                    action = tmp.group(1) if tmp else b''
                    tmp = self.method_pattern.search(form)
                    method = tmp.group(1) if tmp else b'get'
                    inputs = self.input_pattern.findall(form)
                    params = dict()
                    for ip in inputs:
                        if ip[0] in self.input_types:
                            params[myfunc.decode(ip[1])] = myfunc.decode(ip[2])
                    Form['action'] = urljoin(url,action.decode())
                    Form['method'] = method.decode()
                    Form['params'] = params
                    Forms.append(Form)
        except Exception as e:
            print(e)
        finally:
            await response.release()
        return Forms

    async def scan(self,url,session):
        #get型
        parse = urlparse(url)
        query = list(map(lambda x:x.split('='),parse.query.split('&')))
        for i in range(len(query)):
            if len(query[0])<2:
                break
            #bool盲注
            for payload in self.sqli_bool:
                q1 = dict()
                q2 = dict()
                for x in query:
                    q1[x[0]] = x[1]
                    q2[x[0]] = x[1]
                q1[query[i][0]] = query[i][1]+payload[0]
                q2[query[i][0]] = query[i][1]+payload[1]
                body1 = body2 = ''
                try:
                    q1 = urlunparse((parse.scheme,parse.netloc,parse.path,parse.params,urlencode(q1),parse.fragment))
                    q2 = urlunparse((parse.scheme,parse.netloc,parse.path,parse.params,urlencode(q2),parse.fragment))
                    resp1 = await session.get(q1)
                    body1 = await resp1.read()
                    resp2 = await session.get(q2)
                    body2 = await resp2.read()
                except:
                    pass
                if abs(1-len(body1)/len(body2))>0.98:
                    print(abs(1-len(body1)/len(body2)))
                    print("Type: Bool_Sqli[GET]")
                    print("Url: "+q1)
                    print("Payload: "+payload[0])
                    print("Param: "+query[i][0])
                    break
        #post型
        Forms = await self.get_forms(url,session)

        for Form in Forms:
            Form_json = json.dumps(Form)
            if self.posted.isContain(Form_json):
                continue
            self.posted.insert(Form_json)
            for param_key in Form['params'].keys():
                for payload in self.sqli_bool:
                    new_params1 = new_params2 = Form['params']
                    new_params1[param_key] = new_params1[param_key]+payload[0]
                    new_params2[param_key] = new_params2[param_key]+payload[1]
                    response1 = response2 = None
                    try:
                        if Form['method'].lower()=='get':
                            response1 = await session.get(Form['action'],params=new_params1)
                            body1 = await response1.read()
                            response2 = await session.get(Form['action'],params=new_params2)
                            body2 = await response2.read()
                        if Form['method'].lower()=='post':
                            response1 = await session.post(Form['action'],data=new_params1)
                            body1 = await response1.read()
                            response2 = await session.post(Form['action'],data=new_params2)
                            body2 = await response2.read()
                    finally:
                        body1 = await response1.read()
                        await response1.release()
                        body2 = await response2.read()
                        await response2.release()
                        if abs(1-len(body1)/len(body2))>0.98:
                            print(abs(1-len(body1)/len(body2)))
                            print("Type: Bool_Sqli[POST]")
                            print("Url: "+url)
                            print("Payload: "+payload[0])
                            print("Param: "+param_key)
                            break