import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
import unittest
from rsi.http_deadline import post_json


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_POST(self):
        value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        body=json.dumps({'echo':value}).encode()
        if self.path=='/drip':
            self.send_response(200);self.send_header('Content-Length',str(90+len(body)));self.end_headers()
            try:
                for _ in range(90):
                    self.wfile.write(b' ');self.wfile.flush();time.sleep(.03)
                self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):pass
        else:
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers()
            self.wfile.write(body)


class DeadlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.server.daemon_threads=True
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def test_complete_json(self):
        self.assertEqual(post_json(self.url,{'choice':'a1'},'test-only-token',2),{'echo':{'choice':'a1'}})

    def test_keepalive_cannot_extend_total_deadline(self):
        start=time.monotonic()
        with self.assertRaisesRegex(TimeoutError,'total response deadline'):
            post_json(self.url+'/drip',{},'test-only-token',.35)
        self.assertLess(time.monotonic()-start,1.5)

if __name__=='__main__':unittest.main()
