from pymongo import MongoClient
from dotenv import dotenv_values
from bson.objectid import ObjectId
env = dotenv_values(".env")

client = MongoClient(env['MONGO_DB_URI'])
db = client.opensea


def transfer():
    # buscar las wallets de dueño actual y el creador
    owner_wallet = db.wallets.find_one(
        {'user_id': ObjectId(product['owner'])})
    creator_wallet = db.wallets.find_one(
        {'user_id': ObjectId(product['creator']['_id'])})

    # transferencia del NFT
    db.nfts.update_one(
        {'_id': product['product_id'], 'owner': product['owner']},
        {
            '$set': {'owner': newOrder['receiver']}
        }
    )
    # transferencia de los balances por cada producto y calculo de los fees
    db.wallets.update_one(
        {'user_id': client_wallet['user_id'],
         'balance': client_wallet['balance']},
        {
            '$set': {'balance': client_wallet['balance'] - fixedProductAmount}
        }
    )

    fee_creator = float(fixedProductAmount) * 10 / 100
    earning_owner = fixedProductAmount - fee_creator

    db.wallets.update_one(
        {'user_id': owner_wallet['user_id'],
         'balance': owner_wallet['balance']},
        {
            '$set': {'balance': owner_wallet['balance'] + earning_owner}
        }
    )

    db.wallets.update_one(
        {'user_id': creator_wallet['user_id'],
         'balance': creator_wallet['balance']},
        {
            '$set': {'balance': creator_wallet['balance'] + fee_creator}
        }
    )
