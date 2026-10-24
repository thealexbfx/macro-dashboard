"""Deployment smoke checks: no real credentials or paid API requests."""
import importlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from contextlib import ExitStack
from unittest.mock import patch
from urllib.request import urlopen

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]


class DeploymentSmokeTests(unittest.TestCase):
    def test_existing_pages_with_controlled_provider_data(self):
        # Exercise real renderers and calculations; only retrieval is replaced.
        modules=[]
        for package in ('data','indicators','app_pages'):
            for path in (ROOT/package).glob('*.py'):
                if path.stem!='__init__': modules.append(importlib.import_module(f'{package}.{path.stem}'))
        frame=pd.DataFrame({'date':pd.date_range('2016-01-31',periods=120,freq='ME'),
                            'value':[3+i*.01 for i in range(120)]})
        def provider(*args,**kwargs): return frame.copy()
        pages=['Home','UnitedStates','EuroArea','UnitedKingdom','Japan','RatesBonds',
               'Equities','Commodities','FX','Crypto','GlobalMacroView','RegimeMonitor',
               'CentralBankWatch','ResearchNotes','Calendar']
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ,{'OPENAI_API_KEY':'test-only-not-a-real-key'}))
            for module in modules:
                for name,value in list(vars(module).items()):
                    if name.startswith('get_') and callable(value):
                        stack.enter_context(patch.object(module,name,side_effect=provider))
            # Unmocked outbound access fails the test rather than hitting APIs.
            stack.enter_context(patch('requests.sessions.Session.request',side_effect=AssertionError('Unexpected network access in UI smoke test')))
            for page in pages:
                with self.subTest(page=page):
                    app=AppTest.from_file(str(ROOT/'app.py'))
                    app.query_params['page']=page
                    app.run(timeout=30)
                    self.assertEqual([e.message for e in app.exception],[])
                    self.assertEqual([e.value for e in app.error],[])

    def test_missing_openai_key_is_reported_on_overview(self):
        with patch.dict(os.environ,{},clear=True):
            app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
            self.assertEqual(len(app.exception),0)
            self.assertTrue(any('OpenAI API key not found' in e.value for e in app.error))

    def test_streamlit_http_health(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0))
            port=listener.getsockname()[1]
        process=subprocess.Popen([sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),
                                  '--server.address','0.0.0.0','--server.port',str(port),
                                  '--server.headless','true','--browser.gatherUsageStats','false'],
                                 cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                if process.poll() is not None: self.fail('Streamlit process exited before becoming healthy')
                try:
                    with urlopen(f'http://127.0.0.1:{port}/_stcore/health',timeout=1) as response:
                        self.assertEqual(response.status,200)
                        self.assertEqual(response.read(),b'ok')
                        return
                except OSError: time.sleep(.25)
            self.fail('Streamlit health endpoint did not become ready')
        finally:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)

    def test_bea_failure_does_not_display_secret_url(self):
        import tempfile
        import requests
        from data import bea
        bea.get_bea_nipa_series.clear()
        with tempfile.TemporaryDirectory() as tmp, patch('data.bea.CACHE_DIR',Path(tmp)), patch('data.bea.requests.get',side_effect=requests.ConnectionError('https://example.test/?UserID=test-secret')):
            with self.assertRaises(RuntimeError) as exc:
                bea.get_bea_nipa_series('TEST',1)
            self.assertNotIn('test-secret',str(exc.exception))
            cache=bea._cache_path('TEST',1,'Q')
            pd.DataFrame({'date':['2024-03-31'],'value':[1]}).to_csv(cache,index=False)
            with patch('data.bea._cache_is_fresh',return_value=False), patch('data.bea.st.warning') as warning:
                result=bea.get_bea_nipa_series('TEST',1)
                self.assertEqual(result.value.iloc[0],1)
                self.assertNotIn('test-secret',str(warning.call_args))
        bea.get_bea_nipa_series.clear()
