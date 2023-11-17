from pymongo import MongoClient
from dotenv import dotenv_values
from bson.objectid import ObjectId

env = dotenv_values(".env")

client = MongoClient(env["MONGO_DB_URI"])
db = client.opensea


def Login(userName, userPassword):
    if userName == "":
        return {
            "success": False,
            "error": "Ingresa el mail o nombre de usuario",
        }

    if userPassword == "":
        return {
            "success": False,
            "error": "Ingresa la contraseña",
        }

    userDocument = db.users.find_one({"$or": [{"email": userName}, {"user": userName}]})

    if not userDocument:
        return {
            "success": False,
            "error": "El usuario no existe",
        }

    if userDocument["password"] != userPassword:
        return {
            "success": False,
            "error": "La contraseña o el usuario es inválido",
        }

    return {
        "success": True,
        "user_id": str(userDocument["_id"]),
    }
