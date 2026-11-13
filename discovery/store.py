"""SQLite persistence, material updates, and explicit research feedback."""
import json
import sqlite3

class SignalStore:
    def __init__(self, path):
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS signals (id TEXT PRIMARY KEY, body TEXT, version INTEGER)')
        self.db.execute('CREATE TABLE IF NOT EXISTS detections (id TEXT, detected TEXT, version INTEGER)')
        self.db.execute('CREATE TABLE IF NOT EXISTS signal_history (id TEXT, version INTEGER, body TEXT, PRIMARY KEY(id, version))')
        self.db.execute('CREATE TABLE IF NOT EXISTS feedback (id TEXT, label TEXT, note TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')

    def upsert(self, signal):
        material={k:v for k,v in signal.items() if k!='detection_timestamp'}
        # Ingestion timestamps alone do not constitute a changed observation.
        material=json.loads(json.dumps(material,allow_nan=False))
        material['data_source'].pop('ingestion_timestamp',None)
        body=json.dumps(material,sort_keys=True,allow_nan=False)
        old=self.db.execute('SELECT body,version FROM signals WHERE id=?',(signal['signal_id'],)).fetchone()
        if old and json.loads(old[0])['observation_date'] > material['observation_date']:
            return 'historical'
        if old and old[0]==body: return 'unchanged'
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO signals VALUES (?,?,?)',(signal['signal_id'],body,old[1]+1 if old else 1))
            self.db.execute('INSERT INTO detections VALUES (?,?,?)',(signal['signal_id'],signal['detection_timestamp'],old[1]+1 if old else 1))
            self.db.execute('INSERT INTO signal_history VALUES (?,?,?)',(signal['signal_id'],old[1]+1 if old else 1,body))
        return 'updated' if old else 'created'

    def feedback(self, signal_id, label, note=''):
        if label not in ('interesting','irrelevant','misleading','already_investigated'):
            raise ValueError('Invalid feedback')
        if not self.db.execute('SELECT 1 FROM signals WHERE id=?',(signal_id,)).fetchone(): raise ValueError('Unknown signal')
        with self.db: self.db.execute('INSERT INTO feedback (id,label,note) VALUES (?,?,?)',(signal_id,label,note))

    def close(self):
        self.db.close()
