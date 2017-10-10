'''An item catalog application with user authorization/authentication'''
from flask import Flask, render_template, request
from flask import flash, redirect, jsonify, url_for
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
# modules for gconnect
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
from functools import wraps
# modules for login
from flask import session as login_session
import random
import string

app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json', 'r').
                       read())['web']['client_id']

# Connect to the database and create a db sessionmaker
engine = create_engine('sqlite:///itemcatalogwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/category/json')
def category_json():
    '''Returns a json of the categories'''
    categories = session.query(Category).all()
    return jsonify(Categories=[category.serialize for category in categories])


@app.route('/category/<string:category>/json')
def category_item_json(category):
    '''Return a json of items in a category'''
    category_selected = session.query(Category).filter_by(name=category).one()
    items = session.query(Item).filter_by(
        category_id=category_selected.id).all()
    return jsonify(Category=[item.serialize for item in items])
    # restaurantMenu=[menuItem.serialize for menuItem in menu]


# State token to prevent request forgery
@app.route('/login')
def do_login():
    '''Logins user using OAuth2'''
    state = ''.join(random.choice(string.ascii_uppercase+string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    if 'username' not in login_session:
        user = login_session
        user.username = "Welcome"
        return render_template('login.html', STATE=state, user=user)
    else:
        user = login_session
        return render_template('showCategories.html')
    # return "The current session state is %s" %login_session['state']


@app.route('/gconnect', methods=['POST'])
def gconnect():
    '''Checks and validates google login process to prevent fraud,
    among other things'''
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state secret'), 401)
        response.header['Content-Type'] = 'application/json'
        return response
    code = request.data  # this is a json.
    try:
        # Upgrade authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        # if credentials is None:
        #     print "It is empty"
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the '
                                            'authorization code'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # if the result has an error, abort
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error'), 500))
        response.headers['Content-Type'] = 'application/json'
    # Verify that the access token is used for the intended user
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Verify that the access token is valid for this app
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID does not '\
                                'match app's"), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check if a user is already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already '
                                            'connected'), 200)
        response.header['Content-Type'] = 'application/json'

    # Store the access token in the session for later use
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    # save the preferred user data
    login_session['username'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]

    # check if the user is in db. if not, create a new user
    user_id = get_user_id(login_session['email'])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 50px; height: 50px; border-radius: '\
              '150px;-webkit-border-radius: 150px;-moz-border-radius: '\
              '150px;">'
    flash("you are now logged in as %s" % login_session['username'])
    return output


@app.route('/gdisconnect', methods=['GET', 'POST'])
def gdisconnect():
    '''Logs out a user'''
    # Only disconnect a connected user
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not '
                                            'connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Use HTTP GET request to revoke the current user's access token
    # access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
          % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    # check status of the response received in result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        return redirect(url_for('show_categories'))
        # send response
        # response = make_response(json.dumps('Successfully '\
        #                                     'disconnected user.'), 200)
        # response.headers['Content-Type'] = 'application/json'
        # return response

    else:
        # if the token is Invalid
        response = make_response(json.dumps('Failed to revoke token '
                                            'for a given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


# Login required function/decorator
def login_required(f):
    # Checks if user is logged in
    @wraps(f)
    def check_user_status(*args, **kwargs):
        if 'username' not in login_session:
            return redirect('/login')
        else:
            return f(*args, **kwargs)
    return check_user_status


@app.route('/')
@app.route('/category/')
def show_categories():
    '''Displays all categories'''
    # query categories
    categories = session.query(Category).all()
    # query last items filtering by date/time added
    items = session.query(Item).order_by(desc(Item.date_added)).limit(8).all()
    # commented out below to test front-end
    if 'username' not in login_session:
        user = login_session
        user.username = "Welcome"
        return render_template('publicCategories.html',
                               categories=categories, items=items, user=user)
    else:
        user = login_session
    # user = login_session
        return render_template('showCategories.html', categories=categories,
                               items=items, user=user)
    # return "This will display list of categories"


@app.route('/category/<string:category>', methods=['GET', 'POST'])
def specific_category(category):
    '''Displays items in a specific category'''
    # query category you are in
    category = session.query(Category).filter_by(name=category).first()
    items = session.query(Item).filter_by(category_id=category.id).all()
    if 'username' not in login_session:
        user = login_session
        user.username = "Welcome"
        return render_template('publicSpecificCategory.html',
                               category=category, items=items, user=user)
    else:
        user = login_session
        return render_template('showSpecificCategory.html',
                               category=category, items=items, user=user)
    # return "This will display list of category %s items" %(category)


@app.route('/category/add', methods=['GET', 'POST'])
@login_required
def add_category():
    '''Adds a new category'''
    user = login_session
    if request.method == 'POST':
        new_category = Category(name=request.form['newCategoryName'],
                                user_id=login_session['user_id'])
        session.add(new_category)
        session.commit()
        return redirect(url_for('show_categories'))
    else:
        return render_template('addCategory.html', user=user)


@app.route('/category/<string:category>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category):
    '''Edit a category'''
    category_to_edit = session.query(Category).filter_by(name=category).one()
    # Alert message if not user who owns this
    if category_to_edit.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert( "\
               "'You are not authorized to edit this category."\
               " Please create one in order to edit.');}</script><body "\
               "onload='myFunction()''>"
    if request.method == 'POST':
        category_to_edit.name = request.form['editedCategoryName']
        session.add(category_to_edit)
        session.commit()
        return redirect(url_for('show_categories'))
    else:
        return render_template('editCategory.html',
                               category_to_edit=category_to_edit,
                               user=login_session)


@app.route('/category/<string:category>/delete/', methods=['GET', 'POST'])
def delete_category(category):
    '''Delete a category'''
    category_to_delete = session.query(Category).\
                         filter_by(name=category).first()
    user = login_session
    if category_to_delete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert( "\
               "'You are not authorized to delete this category."\
               " Please create one in order to delete.');}</script><body "\
               "onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(category_to_delete)
        session.commit()
        return redirect(url_for('show_categories'))
    else:
        return render_template('deleteCategory.html',
                               category_to_delete=category_to_delete,
                               user=user)


@app.route('/category/<string:category>/<string:item>',methods=['GET','POST'])
def specific_item(category, item):
    '''Show an item and its descripton'''
    category = session.query(Category).filter_by(name=category).one()
    item = session.query(Item).filter_by(name=item).one()
    # user = get_user_info(category.user_id)
    if 'username' not in login_session:
        user = login_session
        user.username = "Welcome"
        return render_template('publicItems.html', category=category,
                               item=item, user=login_session)
    else:
        return render_template('showItem.html', category=category,
                               item=item, user=login_session)
    # return "This will return item %s in category %s and its description" %(item, category)


@app.route('/category/<string:category>/add', methods=['GET', 'POST'])
@login_required
def add_item(category):
    '''Adds an item to a category'''
    category_selected = session.query(Category).filter_by(name=category).one()
    if request.method == 'POST':
        # pick item name and description from the form
        item_name = request.form['newItem']
        item_description = request.form['newItemDescription']
        new_item = Item(name=item_name, description=item_description,
                        category=category_selected,
                        user_id=category_selected.user_id)
        # add item to the db
        session.add(new_item)
        session.commit()
        return redirect(url_for('specific_category',
                                category=category_selected.name), code=302)
    else:
        return render_template('addItem.html',
                               category_selected=category_selected,
                               user=login_session)
    # return "This will let you add item %s in category %s" %(item, category)



@app.route('/category/<string:category>/<string:item>/edit',
           methods=['GET', 'POST'])
@login_required
def edit_item(category, item):
    '''Edit an item in a category'''
    category_selected = session.query(Category).filter_by(name=category).one()
    item_to_edit = session.query(Item).filter_by(name=item).first()
    if item_to_edit.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert( "\
               "'You are not authorized to edit this item."\
               " Please create one in order to edit.');}</script><body "\
               "onload='myFunction()''>"
    if request.method == 'POST':
        # pick edited item details
        item_to_edit.name = request.form['editedItemName']
        item_to_edit.description = request.form['editedItemDescription']
        # add edited item to db
        session.add(item_to_edit)
        session.commit()
        return redirect(url_for('specific_item',
                                category=category_selected.name,
                                item=item_to_edit.name, user=login_session))
    else:
        return render_template('editItem.html',
                               category_selected=category_selected,
                               item_to_edit=item_to_edit, user=login_session)
    # return "This will let you edit item %s in category %s and its description" %(item, category)


@app.route('/category/<string:category>/<string:item>/delete',
           methods=['GET', 'POST'])
@login_required
def delete_item(category, item):
    '''Delete an item in a category'''
    category_selected = session.query(Category).filter_by(name=category).one()
    item_to_delete = session.query(Item).filter_by(name=item).first()
    if item_to_delete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert( "\
               "'You are not authorized to delete this item."\
               " Please create one in order to delete.');}</script><body "\
               "onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(item_to_delete)
        session.commit()
        return redirect(url_for('specific_category',
                                category=category_selected.name,
                                user=login_session))
    else:
        return render_template('deleteItem.html',
                               category_selected=category_selected,
                               item_to_delete=item_to_delete,
                               user=login_session)
    # return "This will let you delete item %s in category %s and its description" \
    #         %(item, category)


def get_user_id(email):
    '''Takes an email and returns user if email exists in db'''
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def get_user_info(user_id):
    '''Return user(object) information from the db'''
    user = session.query(User).filter_by(id=user_id).one()
    return user


def create_user(user):
    '''Creates a new user and returns the user's id'''
    new_user = User(name=user['username'], email=user['email'],
                    picture=user['picture'])
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(email=user['email']).one
    return user.id


# Run application on localhost
if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
