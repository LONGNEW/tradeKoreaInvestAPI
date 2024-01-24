import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate('src/mykey.json')
firebase_admin.initialize_app(cred,{
    'databaseURL' : ''
})

def wipe_lists():
    db.reference().update({'/20second': {"restart": 0}})
    db.reference().update({'/candidate': {"restart": 0}})

def get_lists():
    return db.reference("/today").get()

def having_cnt():
    return db.reference("/cnt").get()

def limit_cnt():
    return db.reference("/limit").get()

if __name__ == '__main__':
    wipe_lists()