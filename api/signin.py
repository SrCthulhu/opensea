from pymongo import MongoClient
from dotenv import dotenv_values
from bson.objectid import ObjectId
from datetime import datetime

env = dotenv_values(".env")

client = MongoClient(env["MONGO_DB_URI"])
db = client.opensea


def Signin(newEmail, newPassword, new_user_name):
    if newEmail == "":
        return {"success": False, "error": "Ingresa un Email"}

    if newPassword == "":
        return {"success": False, "error": "Ingresa la contraseña"}

    if len(newPassword) < 8:
        return {
            "success": False,
            "error": "La contraseña debe contener 8 o más caracteres",
        }

    if new_user_name == "":
        return {"success": False, "error": "Ingresa un nombre de usuario"}

    if len(new_user_name) < 5:
        return {
            "success": False,
            "error": "Nombre de usuario muy corto, debe contener 6 o más caracteres",
        }

    if len(new_user_name) > 15:
        return {
            "success": False,
            "error": "Nombre de usuario muy largo , NO debe contener más de 15 caracteres",
        }

    emailSplitted = newEmail.split("@")

    if len(emailSplitted) != 2 or emailSplitted[1] != "gmail.com" != "hotmail.com":
        return {
            "success": False,
            "error": "Dirección de correo inválida, debe tener las terminaciones: @gmail.com / @hotmail.com",
        }

    time = datetime.now()
    users = list(db.users.find())

    for i in range(len(users)):
        total = i + 1 + 1
        print(total)

    newUser = {
        "email": newEmail,
        "password": newPassword,
        "user": new_user_name,
        "nfts": 0,
        "user_number": total,
        "user_created_at": time.strftime("%d-%m-%Y, %H:%M:%S"),
    }
    userId = db.users.insert_one(newUser).inserted_id

    newWallet = {
        "name": "Mafiance Coin",
        "currency": "MFC",
        "balance": float(0),
        "user_id": userId,
    }
    db.wallets.insert_one(newWallet)
