import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
import os

cred = credentials.Certificate("firebase/serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'taskboard-app-5d3f5.appspot.com'
})

db = firestore.client()
bucket = storage.bucket()
