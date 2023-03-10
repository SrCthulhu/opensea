from pymongo import MongoClient
from dotenv import dotenv_values
from bson.objectid import ObjectId

env = dotenv_values(".env")

client = MongoClient(env['MONGO_DB_URI'])
db = client.opensea


def Transfer(client_wallet, product):
    # buscar las wallets de dueño actual y el creador
    owner_wallet = db.wallets.find_one(
        {'user_id': ObjectId(product['owner'])})
    creator_wallet = db.wallets.find_one(
        {'user_id': ObjectId(product['creator']['_id'])})

    # transferencia del NFT
    db.nfts.update_one(
        {
            '_id': product['product_id']
        },
        {
            '$set': {'owner': str(client_wallet['user_id'])}
        }
    )
    # transferencia de los balances por cada producto y calculo de los fees
    fixedProductAmount = float(product['listed']['fixed_amount'])
    fee_creator = round(float(fixedProductAmount) * 10 / 100)
    earning_owner = round(fixedProductAmount - fee_creator)
    fee_platform = 0

    # Fórmula para hacer que el creador si se compra a si mismo el nft que ya vendio no gane comision del creador,
    # También aplicamos comisión de la plataforma de 2.5%
    if owner_wallet['_id'] == creator_wallet['_id']:
        fee_creator = 0
        fee_platform = round(float(fixedProductAmount) * 2.5 / 100)
        earning_owner = round(fixedProductAmount - fee_platform)

        opensea_wallet = db.wallets.find_one({'fee_account': "True"})
        db.wallets.update_one(
            {
                'fee_account': "True"
            },
            {
                '$set': {'balance': opensea_wallet['balance'] + fee_platform}
            }
        )

    db.wallets.update_one(
        {
            'user_id': client_wallet['user_id']
        },
        {
            '$set': {'balance': client_wallet['balance'] - fixedProductAmount}
        }
    )

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
