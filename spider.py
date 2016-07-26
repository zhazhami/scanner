import aiohttp
import asyncio
from asyncio import Queue
from urllib import parse
import argparse
from bloomfilter import BloomFilter
import re
from scanner import Scanner
import myfunc

class Spider():
    def __init__(self,domain,max_tasks,scan_subdomain=False,loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.domain = domain
        self.main_domain = '.'.join(domain.split('.')[1:])
        self.max_tasks = max_tasks
        self.scan_subdomain = scan_subdomain
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.q = Queue(loop=self.loop)
        self.seen_urls = BloomFilter()
        self.link_pattern = re.compile(r'''(?i)href=["']([^\s"'<>]+)'''.encode())
        self.scanner = Scanner()
        self.file_type = ['.doc','.docx','.pdf','.zip','.ppt','.css','.js','.jpg','.png','.gif','.txt','.wmv','.mso','.mp4','.mp3','.rar','.7z','.gz']

    def normalize_url(self,url):
        parts = parse.urlsplit(url)
        query = parse.parse_qs(parts.query,keep_blank_values=True)
        new_query = dict()
        for key,value in query.items():
            if True:
                new_query[key] = ''
            else:
                new_query[key] = value[-1]
        new_query = parse.urlencode(new_query)
        new_url = parse.urlunsplit((parts.scheme,parts.netloc,parts.path,new_query,parts.fragment))
        return new_url

    def add_url(self,url):
        normal_url = self.normalize_url(url)
        if self.url_allowed(url) and (not self.seen_urls.isContain(normal_url)):
            self.q.put_nowait(url)
            self.seen_urls.insert(normal_url)

    def url_allowed(self,url):
        parts = parse.urlsplit(url)
        host, port = parse.splitport(parts.netloc)
        if not self.scan_subdomain and not host == self.domain:
            return False
        if self.scan_subdomain and not host.endswith(self.main_domain):
            return False
        return True

    def close(self):
        self.session.close()

    async def get_Links(self,response):
        response.headers = myfunc.tolower(response.headers)
        content_type = response.headers.get('content-type','').split(';')[0]
        if content_type in ['text/html', 'application/xml']:
            body = await response.read()
            urls = self.link_pattern.findall(body)
            for url in urls:
                normalized = parse.urljoin(response.url,myfunc.decode(url))
                defragmented, frag = parse.urldefrag(normalized)
                flag = False
                for t in self.file_type:
                    if defragmented.endswith(t):
                        flag = True
                        break
                if flag:
                    continue
                self.add_url(normalized)

    async def fetch(self,url):
        response = None
        try:
            response = await self.session.get(url)
            if int(response.status/100) == 2:
                await self.get_Links(response)
            if int(response.status/100) == 3:
                location = response.headers.get('location')
                next_url = parse.urljoin(url, location)
                self.add_url(next_url)
        except Exception as e:
            print(e)
        finally:
            await response.release()

    async def worker(self):
        try:
            while True:
                url = await self.q.get()
                print(url)
                await self.scanner.scan(url,self.session)
                await self.fetch(url)
                self.q.task_done()
        except:
            pass

    async def run(self):
        self.add_url("http://"+self.domain)
        workers = [asyncio.Task(self.worker(),loop=self.loop) for _ in range(self.max_tasks)]
        await self.q.join()
        for worker in workers:
            worker.cancel()

if __name__ == '__main__':
    spider = Spider("e.tju.edu.cn",20,scan_subdomain=True)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.run())
    spider.close()
