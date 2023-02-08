from flask import Flask, render_template, redirect, session, request, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import random
import os
from twilio.rest import Client

from dotenv import dotenv_values
env = dotenv_values(".env")
print(env)

app = Flask(__name__, static_url_path='', static_folder='public')
app.secret_key = env['FLASK_SECRET_KEY']
client = MongoClient(env['MONGO_DB_URI'])
db = client.opensea


@app.route("/")
def home_view():
    session.pop('user_id', None)
    users = list(db.users.find())
############### Arreglar la imagen de perfil de cada usuario #############
   # for profileImage in users:
   #     profileImage = db.profile_images.find_one(
   #         {'user': str(users['_id'])})
   # print(profileImage)

    return render_template("home.html", users=users)


@app.route("/landing")
def landing_view():

    users = list(db.users.find())
    userProfilesImages = db.profile_images.find_one({'user_id': users})

    return render_template("landing.html", userProfilesImages=userProfilesImages, users=users)


@app.route("/signin")
def signin_view():
    mensaje = request.args.get('mensaje')
    return render_template("signin.html", mensaje=mensaje)


@app.route("/signin/new_user")
def signin_user():
    newEmail = request.args.get('email')
    newPassword = request.args.get('password')
    new_user_name = request.args.get('user')

    if newEmail == "":
        return redirect('/signin?mensaje=Ingresa el Email')

    if newPassword == "":
        return redirect('/signin?mensaje=Ingresa una Contraseña')

    if len(newPassword) < 8:
        return redirect('/signin?mensaje=La contraseña debe contener 8 o más carácteres')

    if new_user_name == "":
        return redirect('/signin?mensaje=Ingresa un nombre de usuario')

    if len(new_user_name) < 5:
        return redirect('/signin?mensaje=El nombre de usuario no debe contener menos de 5 carácteres')

    if len(new_user_name) > 23:
        return redirect('/signin?mensaje=El nombre de usuario no debe contener  más de 23 carácteres')

    emailSplitted = newEmail.split('@')

    if len(emailSplitted) != 2 or emailSplitted[1] != 'gmail.com' != 'hotmail.com':

        return redirect('/signin?mensaje=la dirección de correo no es válida, debe contener @gmail.com ó @hotmail.com')

    time = datetime.now()

# Asignamos un número al usuario y lo aumentamos al crearse otro nuevo.
    users = list(db.users.find())

    for i in range(len(users)):
        total = i + 1 + 1
        print(total)

    newUser = {
        'email': newEmail,
        'password': newPassword,
        'user': new_user_name,
        'nfts': 0,
        'user_number': total,
        'user_created_at': time.strftime('%d-%m-%Y, %H:%M:%S')
    }
    userId = db.users.insert_one(newUser).inserted_id

    newWallet = {
        'name': "Mafiance Coin",
        'currency': "MFC",
        'balance': float(0),
        'user_id': userId,
    }
    db.wallets.insert_one(newWallet)

    session.pop('user_id', None)

    return redirect('/finished/' + str(userId))


@app.route("/finished/<id>")
def registration_finished_view(id):
    user = db.users.find_one({'_id': ObjectId(id)})
    return render_template("finished.html", user=user)


@app.route("/login")
def login_view():
    mensaje = request.args.get('mensaje')
    return render_template("login.html", mensaje=mensaje)


@app.route("/login/users")
def login_users():
    userEmail = request.args.get('email')
    userName = request.args.get('userName')
    userPassword = request.args.get('password')

    if userEmail == "" or userName == "":
        return redirect('/login?mensaje=Ingresa el mail o nombre de usuario')

    if userPassword == "":
        return redirect('/login?mensaje=Ingresa la contraseña')

    userDocument = db.users.find_one(
        {'$or': [{'email': userEmail}, {'user': userEmail}]})

    if not userDocument:
        return redirect('/login?mensaje=El usuario no existe')

    if userDocument['password'] != userPassword or userDocument['email'] != userEmail or userDocument['user'] != userName:
        return redirect('/login?mensaje=La contraseña o el usuario es inválido')

    session['user_id'] = str(userDocument['_id'])

    return redirect('/profile/' + str(userDocument['_id']))


@app.route("/profile/<id>")
def profile_view(id):

    userId = session.get('user_id')
    user = db.users.find_one({'_id': ObjectId(id)})
    userImage = db.profile_images.find_one({'user_id': str(user['_id'])})
    mensaje1 = request.args.get('mensaje1')
    mensaje2 = request.args.get('mensaje2')
    userWallet = db.wallets.find_one({'user_id': ObjectId(id)})
    if not userWallet:
        return abort(404)
#### No me muestra el boton de cargar imágenes aunque el id de la sesion sea el mismo #####
    print(userId)
    print(user['_id'])
####### LAS IMAGENES NO SE ESTÁN CREANDO EN DB ##############
#### Enumerar el carrito ####
    cartproducts = list(db.cart.find({'user_id': userId}))
    i = 0
    for i in range(len(cartproducts)):
        print(i)
    total = i + 1
    if not cartproducts:
        total = 0
#### suma de precios en el carrito (modal) ####
    montoTotal = 0
    for p in cartproducts:
        montoTotal = montoTotal + \
            float(p['listed']['fixed_amount'] * p['quantity'])

    ############################### Filtro #####################################
    name = request.args.get('name')
    maxamount = request.args.get('max')
    minamount = request.args.get('min')

    if name != None:
        # i: insentive case (no importan mayusculas o minusculas)

        # DISCLAIMER PARA DANIEL DEL FUTURO:
        # este uso de busqueda regex es una forma poco optima en
        # GRAN ESCALA con MUCHOS DATOS (>100GB)
        nfts = list(db.nfts.find(
            {'owner': str(user['_id']), 'name': {'$regex': name, '$options': 'i'}}))
    elif maxamount != None and minamount != None:
        # $lt: Less than
        # $lte: Less than or equal
        # $gt: Greater than
        # $gte: Greater than or equal
        nfts = list(db.nfts.find(
            {'owner': str(user['_id']), 'nft_value': {'$gte': float(minamount), '$lte': float(maxamount)}}))
    else:
        nfts = list(db.nfts.find({'owner': str(user['_id'])}))

    return render_template("profile.html",
                           user=user,
                           userImage=userImage,
                           nfts=nfts,
                           userWallet=userWallet,
                           userId=userId,
                           mensaje1=mensaje1,
                           mensaje2=mensaje2,
                           cartproducts=cartproducts,
                           total=total,
                           montoTotal=montoTotal
                           )


@app.route("/logout")
def logout():
    exit = request.args.get('logout')
    if exit:
        session.pop('user_id', None)
    return redirect('/')


@app.route("/upload/image")
def upload_img():
    if not session.get('user_id'):
        return redirect('/login')

    imageUrl = request.args.get('image')
    userId = session.get('user_id')
    user_name = db.users.find_one({'_id': ObjectId(userId)})

    imageUploaded = {}
    imageUploaded['image_url'] = imageUrl
    imageUploaded['user_id'] = userId
    imageUploaded['user'] = user_name

    db.profile_images.insert_one(imageUploaded)
    return redirect('/profile/' + str(userId))


@app.route("/creation")
def creation_view():
    if not session.get('user_id'):
        return redirect('/login')

    userId = session.get('user_id')
    user = db.users.find_one({'_id': ObjectId(userId)})
    nftImagePreview = db.nftsImagePreview.find_one({'user_id': userId})
    mensaje = request.args.get('mensaje')

    return render_template("creation.html", nftImagePreview=nftImagePreview, mensaje=mensaje, user=user)


@app.route("/nft/preview")
def preview():
    if not session.get('user_id'):
        return redirect('/login')

    imageUrl = request.args.get('image')
    userId = session.get('user_id')
    previewNft = {}
    previewNft['image_preview'] = imageUrl
    previewNft['user_id'] = userId
    db.nftsImagePreview.insert_one(previewNft)
    return redirect('/creation')


@app.route("/nft/creation")
def create():
    if not session.get('user_id'):
        return redirect('/login')

    imageUrl = request.args.get('image')
    nameNFT = request.args.get('name')
    externalLink = request.args.get('external_link')
    description = request.args.get('description')
    quantity = request.args.get('quantity')
    currency = request.args.get('currency')
    nftValue = request.args.get('value')
    userId = session.get('user_id')
    user_object = db.users.find_one({'_id': ObjectId(userId)})

    if quantity == "" or quantity == None or nftValue == "" or nftValue == None:
        return redirect('/creation?mensaje=Completa los campos obligatorios')

    if imageUrl != "" or nameNFT != "" or description != "" or quantity != 0 or currency != "" or nftValue != 0:
        time = datetime.now()

        newNft = {}
        newNft['image_url'] = imageUrl
        newNft['name'] = nameNFT
        newNft['external_link'] = externalLink
        newNft['description'] = description
        newNft['quantity'] = int(quantity)
        newNft['currency'] = currency
        newNft['nft_value'] = float(nftValue)
        newNft['owner'] = userId
        newNft['creator'] = user_object
        newNft['creation_date'] = time.strftime('%d-%m-%Y, %H:%M:%S')

    else:
        return redirect('/creation?mensaje=Completa los campos obligatorios')

    db.nfts.insert_one(newNft)

    db.users.update_one(
        {'_id': user_object['_id']},
        {'$set': {'nfts': int(user_object['nfts']) + int(quantity)}
         }
    )

    return redirect('/profile/' + str(userId))


@app.route("/blockchains")
def coins_view():
    if not session.get('user_id'):
        return redirect('/login')

    userId = session.get('user_id')
    user = db.users.find_one({'_id': ObjectId(userId)})
    coins = list(db.blockchains.find())

    return render_template("blockchains.html", coins=coins, user=user)


@app.route("/add/blockchain")
def add_currency():
    if not session.get('user_id'):
        return redirect('/login')

    quantity = float(request.args.get('quantity'))
    userId = session.get('user_id')

    wallet = db.wallets.find_one({'user_id': ObjectId(userId)})
    if not wallet:
        return abort(404)

    newTransaction = {
        'wallet_sender_id': 0,
        'wallet_receiver_id': str(wallet['_id']),
        'quantity': quantity,
        'currency': "MFC",
        'created_at': datetime.now()
    }

    db.transactions.insert_one(newTransaction)
    if wallet:
        db.wallets.update_one(
            {'user_id': ObjectId(userId), 'currency': "MFC"},
            {
                '$set': {'balance': wallet['balance'] + newTransaction['quantity']}
            }
        )
    else:
        return abort(404)

    return redirect('/profile/' + str(userId) + '?mensaje1=Criptoactivo agregado a la wallet')


@app.route("/nft/details/<id>")
def nft_details_view(id):
    if not session.get('user_id'):
        return redirect('/login')

    userId = session.get('user_id')
    nft = db.nfts.find_one({'_id': ObjectId(id)})
    listNfts = list(db.nfts.find({'owner': nft['owner']}))
    offers = list(db.offers.find({'product_id': nft['_id']}))
    orders = list(db.orders.find({'product_id': nft['_id']}))

   # for sender in orders:
    #    sender = list(db.users.find({'_id': orders['sender']}))
   # print(sender)
    ownerWallet = db.wallets.find_one(
        {'user_id': ObjectId(nft['owner'])})

    cartproducts = list(db.cart.find({'user_id': userId}))
    ######### cantidad de productos en el carrito #########
    i = 0
    for i in range(len(cartproducts)):
        print(i)
    total = i + 1
    if not cartproducts:
        total = 0
    ############ Suma de precios ##############
    montoTotal = 0
    for p in cartproducts:
        montoTotal = montoTotal + \
            float(p['listed']['fixed_amount'] * p['quantity'])

    ########### Habilitar botón para completar cierre de subasta ############

    #fechaActual = datetime.now()
    # if nft == nft['listed'] or nft['listed'] != None:
     #   fechaMaxima = nft['listed']['created_at']
    #    diferencia = fechaActual - fechaMaxima
    #    diferencia_segundos_fechas = diferencia.days * 24 * 3600 + diferencia.seconds
    # print(fechaActual)
    # print(fechaMaxima)
    # print(diferencia)
    # print(diferencia.seconds)

    mensaje1 = request.args.get('mensaje1')
    mensaje2 = request.args.get('mensaje2')
    mensaje3 = request.args.get('mensaje3')
    return render_template("nft_details.html", nft=nft,
                           listNfts=listNfts,
                           ownerWallet=ownerWallet,
                           cartproducts=cartproducts,
                           offers=offers,
                           orders=orders,
                           userId=userId,
                           mensaje1=mensaje1,
                           mensaje2=mensaje2,
                           mensaje3=mensaje3,
                           total=total,
                           montoTotal=montoTotal,
                           )


@app.route("/nft/listForSale/<id>")
def list_nft_view(id):
    if not session.get('user_id'):
        return redirect('/login')
    nft = db.nfts.find_one({'_id': ObjectId(id)})
    mensaje = request.args.get('mensaje')
    return render_template("nft_list_item.html", nft=nft, mensaje=mensaje)


@app.route("/nft/list/action/<id>")
def listed(id):
    if not session.get('user_id'):
        return redirect('/login')

    check_fixed = request.args.get('fixed')
    fixed_amount = request.args.get('fixed_amount')
    high_auction = request.args.get('high_price')
    low_auction = request.args.get('low_price')
    auction_amount = request.args.get('auction_amount')
    time_remaining = request.args.get('time')
    category = request.args.get('category')
    check_reserved_item = request.args.get('reserved_item')
    reserved_wallet_id = request.args.get('reserved_buyer_id')

    if fixed_amount == "":
        fixed_amount = float(0)
    if auction_amount == "":
        auction_amount = float(0)

    if fixed_amount != float(0) or auction_amount != float(0) or time_remaining != "Duración" or category != "Categoría del artículo":

        newNftListed = {}
        newNftListed['check_fixed'] = check_fixed
        newNftListed['fixed_amount'] = float(fixed_amount)
        newNftListed['high_auction'] = high_auction
        newNftListed['low_auction'] = low_auction
        newNftListed['auction_amount'] = float(auction_amount)
        newNftListed['created_at'] = datetime.now()
        newNftListed['time_remaining'] = int(time_remaining)
        newNftListed['category'] = category
        newNftListed['check_reserved_item'] = check_reserved_item
        newNftListed['reserved_wallet_id'] = reserved_wallet_id
    else:
        return redirect('/nft/listForSale/' + str(id) + '?mensaje=Tienes campos vacíos')

    nft = db.nfts.find_one({'_id': ObjectId(id)})

    db.nfts.update_one(
        {'_id': ObjectId(nft['_id'])},
        {
            '$set': {'listed': newNftListed}
        }
    )

    return redirect('/nft/details/' + str(id))


@app.route("/nft/add/cart/detail/<id>")
def add_cart(id):
    if not session.get('user_id'):
        return redirect('/login')

    userId = session.get('user_id')
    nft = db.nfts.find_one({'_id': ObjectId(id)})

    addNew = {}
    addNew['product_id'] = nft['_id']
    addNew['name'] = nft['name']
    addNew['image_url'] = nft['image_url']
    addNew['listed'] = nft['listed']
    addNew['quantity'] = 0
    addNew['nft_value'] = nft['nft_value']
    addNew['nft_currency'] = nft['currency']
    addNew['creator'] = nft['creator']
    addNew['owner'] = nft['owner']
    addNew['user_id'] = str(userId)
    addNew['description'] = nft['description']
    addNew['nft_external_link'] = nft['external_link']
    db.cart.insert_one(addNew)

    cartproduct = db.cart.find_one(
        {'name': nft['name'], 'user_id': userId})
    if cartproduct:
        db.cart.update_one(
            {'name': nft['name'], 'user_id': userId},
            {'$set':
                {'quantity': cartproduct['quantity'] + 1}
             }
        )
        return redirect('/nft/details/' + str(id) + '?mensaje1=Item agregado al carro')

    return redirect('/nft/details/' + str(id) + '?mensaje1=Item agregado al carro')


@app.route("/nft/add/cart/profile/<id>")
def add_cart_profile(id):
    if not session.get('user_id'):
        return redirect('/login')

    userId = session.get('user_id')
    nft = db.nfts.find_one({'_id': ObjectId(id)})

    addNew = {}
    addNew['product_id'] = nft['_id']
    addNew['name'] = nft['name']
    addNew['image_url'] = nft['image_url']
    addNew['listed'] = nft['listed']
    addNew['quantity'] = 0
    addNew['nft_value'] = nft['nft_value']
    addNew['nft_currency'] = nft['currency']
    addNew['creator'] = nft['creator']
    addNew['owner'] = nft['owner']
    addNew['user_id'] = str(userId)
    addNew['description'] = nft['description']
    addNew['nft_external_link'] = nft['external_link']
    db.cart.insert_one(addNew)

    cartproduct = db.cart.find_one(
        {'name': nft['name'], 'user_id': userId})
    if cartproduct:
        db.cart.update_one(
            {'name': nft['name'], 'user_id': userId},
            {'$set':
                {'quantity': cartproduct['quantity'] + 1}
             }
        )
    return redirect('/profile/' + str(userId) + '?mensaje1=Item agregado al carro')


@app.route("/remove/cart/product/<id>")
def remove_to_cart(id):

    # Pasos llevados a cabo:
    # 1) con el id en la vista html del producto en el carro lo traemos a la ruta.
    # 2) buscamos en la colección cart el objeto porque nos interesa el id del producto NFT que está dentro.
    # 3) luego a traves del id buscamos el objeto en la coleccion de nfts.
    # 4) borramos el primer producto del carts con delete one.
    # 5) Recargamos la vista de detalle del nft con el id del nft que fue borrado de la coleccion del carro.
    # 6) en la vista imprimimos el mensaje de que ya fue removido el item.

    product_to_delete = db.cart.find_one({'_id': ObjectId(id)})
    nft_remaining = db.nfts.find_one(
        {'_id': ObjectId(product_to_delete['product_id'])})

    db.cart.delete_one({'_id': ObjectId(id)})

    return redirect('/nft/details/' + str(nft_remaining['_id']) + '?mensaje2=Item removido')

    # Desarrollé dos checkouts, uno que utiliza los productos en el carrito y uno directo para un solo producto
    # Todo el proceso de la orden se realiza nuevamente pero sin lista de productos (Esto conllevó hacer dos
    # vistas para cada cosa a futuro considerar otras soluciones).


@app.route("/checkout")  # 1. Utiliza los productos del carro.
def checkout_view():
    if not session.get('user_id'):
        return redirect('/login')

    userId = session.get('user_id')
    cartproducts = list(db.cart.find({'user_id': userId}))

    if not cartproducts:
        return redirect('/login')

    subtotal = 0
    for p in cartproducts:
        subtotal = subtotal + \
            float(p['listed']['fixed_amount'] * p['quantity'])
    # operación para sumar iva ó comisión al total en este caso 10% del creador .
    total = float(subtotal) * 10 / 100

    wallet = db.wallets.find_one({'user_id': ObjectId(userId)})
    mensaje1 = request.args.get('mensaje1')
    mensaje2 = request.args.get('mensaje2')
    mensaje3 = request.args.get('mensaje3')
    return render_template("checkout.html",
                           cartproducts=cartproducts,
                           subtotal=subtotal,
                           total=total,
                           userId=userId,
                           wallet=wallet,
                           mensaje1=mensaje1,
                           mensaje2=mensaje2,
                           mensaje3=mensaje3
                           )


@app.route("/order/create")
def create_order_action():
    if not session.get('user_id'):
        return redirect('/login')

    document = request.args.get('document')
    firstName = request.args.get('first_name')
    lastName = request.args.get('last_name')
    address = request.args.get('address')
    state = request.args.get('state')
    country = request.args.get('country')
    phone = request.args.get('phone')
    email = request.args.get('email')
    terms = request.args.get('terms')
    total = float(request.args.get('total'))

    if document == "" or firstName == "" or lastName == "" or address == "" or state == "" or country == "" or phone == "" or email == "" or total == "" or terms == "":
        return redirect('/checkout?mensaje1=Tienes campos vacíos / Acepta nuestros términos')

    emailSplitted = email.split('@')
    # email = 'hola@gmail.com'
    # emailSplitted = email.split('@') --> ['hola', 'gmail.com']
    # emailSplitted[0] --> 'hola'
    # emailSplitted[1] --> 'gmail.com'
    if len(emailSplitted) != 2 or emailSplitted[1] != 'gmail.com':

        return redirect('/checkout?mensaje2=La dirección de correo no es válida debe contener @gmail.com ó @hotmail.com')

    userId = session.get('user_id')
    cartproducts = list(db.cart.find({'user_id': userId}))

    # newOrder es un diccionario que tiene el diccionario client dentro.
    newOrder = {}
    newOrder['client'] = {
        'document': document,
        'first_name': firstName,
        'last_name': lastName,
        'address': address,
        'state': state,
        'country': country,
        'phone': phone,
        'email': email,
        'terms': terms,
    }
    newOrder['event'] = "Venta"
    newOrder['user_id'] = userId
    newOrder['cart'] = cartproducts
    newOrder['total'] = total
    newOrder['created_at'] = datetime.now()

    # Buscamos billeteras de quien compra y del dueño del NFT y hacemos el trade
    # La primera wallet del cliente la ubicamos con la sesion. para la segunda tuvimos que ciclar
    # por cada elemento del carrito que tenga el mismo owner de la wallet y luego actualizamos el balance

    client_wallet = db.wallets.find_one({'user_id': ObjectId(userId)})

    for product in cartproducts:
        owner_wallet = db.wallets.find_one(
            {'user_id': ObjectId(product['owner'])})
    print(owner_wallet)

    if client_wallet['balance'] < total:
        return redirect('/checkout?mensaje3=Balance insuficiente')

    db.wallets.update_one(
        {'user_id': client_wallet['user_id'],
         'balance': client_wallet['balance']},
        {
            '$set': {'balance': client_wallet['balance'] - total}
        }
    )
    db.wallets.update_one(
        {'user_id': owner_wallet['user_id'],
         'balance': owner_wallet['balance']},
        {
            '$set': {'balance': owner_wallet['balance'] + total}
        }
    )

    #### Cambiamos el Propietario de los NFT en el carrito y la cantidad de suministro cambia ####
    for product in cartproducts:
        db.nfts.update_one(
            {'_id': product['product_id'], 'owner': product['owner']},
            {
                '$set': {'owner': newOrder['user_id']}
            }
        )
        productId = db.nfts.find_one({'_id': product['product_id']})
        if productId['quantity'] > 1:
            db.nfts.update_one(
                {'_id': productId['_id']},
                {
                    '$set': {'quantity': productId['quantity'] - 1}
                }
            )
    # Creamos la orden
    orderCreated = db.orders.insert_one(newOrder)
    orderId = orderCreated.inserted_id

    # Borrar todos los productos del carrito DEL USUARIO
    db.cart.delete_many({'user_id': userId})

    return redirect('/order/' + str(orderId))


@app.route("/order/<id>")
def order_view(id):
    if not session.get('user_id'):
        return redirect('/login')
    order = db.orders.find_one({'_id': ObjectId(id)})
    return render_template("order_completed.html", order=order)
################################ Fin Proceso de orden con carrito ##################################################


@app.route("/checkout/<id>")  # 2. Checkout de un solo producto.
def checkout_view_product(id):
    if not session.get('user_id'):
        return redirect('/login')

    userId = session.get('user_id')
    product = db.nfts.find_one({'_id': ObjectId(id)})

    subtotal = 0
    subtotal = subtotal + \
        float(product['listed']['fixed_amount'] * product['quantity'])
    # Operación para sumar iva ó comisión al total en este caso 10% del creador .
    total = float(subtotal) + float(subtotal) * 10 / 100

    wallet = db.wallets.find_one({'user_id': ObjectId(userId)})
    mensaje1 = request.args.get('mensaje1')
    mensaje2 = request.args.get('mensaje2')
    mensaje3 = request.args.get('mensaje3')
    return render_template("checkout_single.html",
                           product=product,
                           subtotal=subtotal,
                           total=total,
                           userId=userId,
                           wallet=wallet,
                           mensaje1=mensaje1,
                           mensaje2=mensaje2,
                           mensaje3=mensaje3
                           )


@app.route("/order/create/single/product/<id>")
def create_order_single(id):
    if not session.get('user_id'):
        return redirect('/login')

    document = request.args.get('document')
    firstName = request.args.get('first_name')
    lastName = request.args.get('last_name')
    address = request.args.get('address')
    state = request.args.get('state')
    country = request.args.get('country')
    phone = request.args.get('phone')
    email = request.args.get('email')
    terms = request.args.get('terms')
    total = float(request.args.get('total'))

    product = db.nfts.find_one({'_id': ObjectId(id)})

    if document == "" or firstName == "" or lastName == "" or address == "" or state == "" or country == "" or phone == "" or email == "" or total == "" or terms == "":
        return redirect('/checkout/' + str(product['_id']) + '?mensaje1=Tienes campos vacíos / Acepta nuestros términos')

    emailSplitted = email.split('@')
    if len(emailSplitted) != 2 or emailSplitted[1] != 'gmail.com':

        return redirect('/checkout/' + str(product['_id']) + '?mensaje2=La dirección de correo no es válida debe contener @gmail.com ó @hotmail.com')

    userId = session.get('user_id')

    newOrder = {}
    newOrder['client'] = {
        'document': document,
        'first_name': firstName,
        'last_name': lastName,
        'address': address,
        'state': state,
        'country': country,
        'phone': phone,
        'email': email,
        'terms': terms,
    }
    newOrder['event'] = "Venta"
    newOrder['user_id'] = userId
    newOrder['product'] = product
    newOrder['total'] = total
    newOrder['created_at'] = datetime.now()

    # Buscamos billeteras de quien compra y del dueño del NFT y hacemos el trade
    # La primera wallet del cliente la ubicamos con la sesion.
    # para la segunda buscamos por el dueño del nft.

    client_wallet = db.wallets.find_one({'user_id': ObjectId(userId)})

    owner_wallet = db.wallets.find_one({'user_id': ObjectId(product['owner'])})
    print(owner_wallet)

    if client_wallet['balance'] < total:
        return redirect('/checkout/' + str(product['_id']) + '?mensaje3=Balance insuficiente')

    db.wallets.update_one(
        {'user_id': client_wallet['user_id'],
         'balance': client_wallet['balance']},
        {
            '$set': {'balance': client_wallet['balance'] - total}
        }
    )
    db.wallets.update_one(
        {'user_id': owner_wallet['user_id'],
         'balance': owner_wallet['balance']},
        {
            '$set': {'balance': owner_wallet['balance'] + total}
        }
    )

    #### Cambiamos el Propietario del NFT y la cantidad de suministro cambia ####
    db.nfts.update_one(
        {'_id': product['_id'], 'owner': product['owner']},
        {
            '$set': {'owner': newOrder['user_id']}
        }
    )
    if product['quantity'] > 1:
        db.nfts.update_one(
            {'_id': product['_id']},
            {
                '$set': {'quantity': product['quantity'] - 1}
            }
        )
    # Creamos la orden (un solo producto)
    orderCreated = db.orders.insert_one(newOrder)
    orderId = orderCreated.inserted_id

    return redirect('/single/order/' + str(orderId))


@app.route("/single/order/<id>")
def single_order_view(id):
    if not session.get('user_id'):
        return redirect('/login')
    order = db.orders.find_one({'_id': ObjectId(id)})
    return render_template("single_order_completed.html", order=order)

####################################### Fin proceso de orden individual #####################################


@app.route("/user/offer/<id>")
def offer_view(id):
    if not session.get('user_id'):
        return redirect('/login')

    userId = session.get('user_id')
    nft = db.nfts.find_one({'_id': ObjectId(id)})
    userWallet = db.wallets.find_one({'user_id': ObjectId(userId)})
    mensaje1 = request.args.get('mensaje1')
    mensaje2 = request.args.get('mensaje2')
    mensaje4 = request.args.get('mensaje4')
    mensaje5 = request.args.get('mensaje5')
    return render_template("user_offer.html",
                           nft=nft,
                           userWallet=userWallet,
                           mensaje1=mensaje1,
                           mensaje2=mensaje2,
                           mensaje4=mensaje4,
                           mensaje5=mensaje5)


@app.route("/create/offer/<id>")
def create_offer_action(id):
    if not session.get('user_id'):
        return redirect('/login')

    userId = session.get('user_id')
    price = request.args.get('price')
    nft = db.nfts.find_one({'_id': ObjectId(id)})
    user = db.users.find_one({'_id': ObjectId(userId)})
    userWallet = db.wallets.find_one({'user_id': ObjectId(userId)})
    #### Para comparar el tiempo debemos revisar las ofertas antiguas antes de re####
################### validar un número ###############################

    if price == None or not price.isnumeric():
        return redirect('/user/offer/' + str(nft['_id']) + '?mensaje1=Introduzca un número, llene los campos y no use carácteres especiales:' + ' !*$?¿')

    if float(price) < float(nft['listed']['auction_amount']):
        return redirect('/user/offer/' + str(nft['_id']) + '?mensaje2=No puedes ofertar por un monto inferior al base')

    if float(userWallet['balance']) < float(price):
        return redirect('/user/offer/' + str(nft['_id']) + '?mensaje4=Tu balance es insuficiente para ofertar')

    # Diferencia de segundos entre dos fechas ################## Revisar vista nft_list_item.html
    fechaActual = datetime.now()
    fechaMaxima = nft['listed']['created_at']

    diferencia = fechaActual - fechaMaxima
    # OJOOOOOO debe dar números positivos para mostrar la diferencia de tiempo que yá pasó
    # Si necesitas saber la hora que aún no ha pasado es: fechaMaxima - fechaActual ###########
    diferencia_segundos_fechas = diferencia.days * 24 * 3600 + diferencia.seconds

    print(fechaActual)
    print(fechaMaxima)
    print(diferencia)
    print(diferencia.seconds)

    if diferencia_segundos_fechas > nft['listed']['time_remaining']:
        return redirect('/user/offer/' + str(nft['_id']) + '?mensaje5=Ya cerró la subasta, no puedes ofertar 😣')

    newOffer = {}
    newOffer['product_id'] = nft['_id']
    newOffer['name'] = nft['name']
    newOffer['price'] = float(price)
    newOffer['user_id'] = user
    newOffer['floor_difference'] = 0
    newOffer['time'] = fechaActual.strftime('%d-%m-%Y, %H:%M:%S')
    db.offers.insert_one(newOffer)

    return redirect('/nft/details/' + str(nft['_id']) + '?mensaje3=¡Oferta realizada con éxito!, es visible en el listado')

##### Subasta ####


@app.route("/auction/<id>")
def auction_view(id):
    if not session.get('user_id'):
        return redirect('/login')

####### Formúla para iterar sobre listas con un valor int o float y comparar cuál tiene el número mayor #######

    nft = db.nfts.find_one({'_id': ObjectId(id)})
    offers = list(db.offers.find({'product_id': nft['_id']}))

    bestOffer = offers[0]

    for i in range(0, len(offers)):
        if offers[i]['price'] > bestOffer['price']:
            bestOffer = offers[i]
    print(bestOffer)

    return render_template("auction.html",
                           nft=nft,
                           bestOffer=bestOffer
                           )


@app.route("/transfer/nft/action/<id>")
def transfer_nft(id):
    if not session.get('user_id'):
        return redirect('/login')

    offer = db.offers.find_one({'_id': ObjectId(id)})
    userId = session.get('user_id')

    newOrder = {}
    newOrder['event'] = "Transferencia"
    newOrder['receiver'] = offer['user_id']
    newOrder['sender'] = userId
    newOrder['product_id'] = offer['product_id']
    newOrder['price'] = offer['price']
    newOrder['created_at'] = datetime.now()

    owner_wallet = db.wallets.find_one({'user_id': ObjectId(userId)})
    print(owner_wallet)

    receiver_wallet = db.wallets.find_one(
        {'user_id': ObjectId(offer['user_id']['_id'])})
    print(receiver_wallet)

    fee_wallet = db.wallets.find_one({'fee_account': "True"})

    fee_amount = offer['price'] * 2.5 / 100
############## Consultar y si el otro usuario ya no dispone del balance cómo le cobro para darle el nft?  ###################

    db.wallets.update_one(
        {'user_id': receiver_wallet['user_id'],
         'balance': receiver_wallet['balance']},
        {
            '$set': {'balance': receiver_wallet['balance'] - offer['price']}
        }
    )
    db.wallets.update_one(
        {'user_id': owner_wallet['user_id'],
         'balance': owner_wallet['balance']},
        {
            '$set': {'balance': owner_wallet['balance'] + offer['price'] - fee_amount}
        }
    )
    db.wallets.update_one(
        {'fee_account': "True",
         'balance': fee_wallet['balance']},
        {
            '$set': {'balance': owner_wallet['balance'] + fee_amount}
        }
    )

    #### Cambiamos el Propietario del NFT ####

    db.nfts.update_one(
        {'_id': offer['product_id'], 'owner': owner_wallet['user_id']},
        {
            '$set': {'owner': offer['user_id']}
        }
    )
    #### Cambiamos el suministo tambien ####
    productId = db.nfts.find_one({'_id': offer['product_id']})
    if productId['quantity'] > 1:
        db.nfts.update_one(
            {'_id': productId['_id']},
            {
                '$set': {'quantity': productId['quantity'] - 1}
            }
        )
    # Creamos la orden
    orderCreated = db.orders.insert_one(newOrder)
    orderId = orderCreated.inserted_id

    # Borrar todas las ofertas del usuario.
    db.offers.delete_many({'user_id': offer['user_id']})

    return redirect("/nft/transfer/success/" + str(orderId))


@app.route("/nft/transfer/success/<id>")
def transfer_success_view(id):
    if not session.get('user_id'):
        return redirect('/login')

    orderId = db.orders.find_one({'_id': ObjectId(id)})
    nft = db.nfts.find_one({'_id': ObjectId(orderId['product_id'])})
    userId = session.get('user_id')
    user = db.users.find_one({'_id': ObjectId(userId)})
    user_wallet = db.wallets.find_one({'user_id': ObjectId(user['_id'])})
    return render_template("nft_transfer_successfully.html",
                           orderId=orderId,
                           nft=nft,
                           user_wallet=user_wallet,
                           user=user)
