uri = "mongodb+srv://davide:wh7fi4DBfryL8LxU@geo-guide-dev.69yiwuv.mongodb.net/?retryWrites=true&w=majority&appName=geo-guide-dev"


from pymongo import MongoClient

import certifi

c = MongoClient(uri, serverSelectionTimeoutMS=8000, tlsCAFile=certifi.where())
print(c.admin.command("ping"))

try:
    c.admin.command("ping")
    print("✅ Connesso a MongoDB Atlas")
except Exception as e:
    print("❌ Errore di connessione:", e)