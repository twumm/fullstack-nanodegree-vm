from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User

app = Flask(__name__)

# modules for login
from flask import session as login_session
import random, string

# modules for gconnect
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests


CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

# Connect to the database and create a db sessionmaker
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/category/json')
def category_json():
    '''Returns a json of the categories'''
    categories = session.query(Category).all()
    return jsonify(Categories=[category.serialize for category in categories])


# TODO
# @app.route('/category/<string:category>/json')
# def category_item_json(category, item):
#     '''Return a json of items in a category'''
#     category_selected = session.query(Category).filter_by(name=category).one()
#     items = session.query(Item).filter_by(name=item).all()
#     return jsonify(Items=[item.serialize for item in items])


# State token to prevent request forgery
@app.route('/login')
def do_login():
    '''Logins user using OAuth2'''
    state = ''.join(random.choice(string.ascii_uppercase+string.digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)
    # return "The current session state is %s" %login_session['state']

# when the
@app.route('/gconnect', methods=['POST'])
def gconnect():
    '''Checks and validates google login process to prevent fraud, among other things'''
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state secret'), 401)
        response.header['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        # Upgrade authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage' #what does this mean/do?
        credentials = oauth_flow.step2_exchange(code) #what does this mean/do?
        # if credentials is None:
        #     print "It is empty"
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1]) # does the result contain the user information?
    # if the result has an error, abort
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error'), 500))
        response.headers['Content-Type'] = 'application/json'
    # Verify that the access token is used for the intended user
    gplus_id = credentials.id_token['sub'] # how can I view the values in credentials?
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Verify that the access token is valid for this app
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID does not match app's"), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check if a user is already logged in
    stored_credentials = login_session.get('credentials') # how can I view the values in credentials?
    stored_gplus_id = login_session.get('gplus_id') # how can I view the values in credentials?
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected'), 200)
        response.header['Content-Type'] = 'application/json'

    # Store the access token in the session for later use
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text) # this returns a dict, right?

    # save the preferred user data
    login_session['username'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px; border-radius: '\
              '150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">'
    flash("you are now logged in as %s" %login_session['username'])
    return output


@app.route('/gdisconnect', methods=['GET', 'POST'])
def gdisconnect():
    # Only disconnect a connected user
    access_token = login_session.get('access_token')
    # credentials = login_session.get('credentials') # how do we get these credentials? where did we store the login credentials in this app?
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Use HTTP GET request to revoke the current user's access token
    # access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0] # why are we storing the first index? how can I see all the items returned

    # check status of the response received in result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        # send response
        response = make_response(json.dumps('Successfully disconnected user.'), 200) # I get a Current User not Connected
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # if the token is Invalid
        response = make_response(json.dumps('Failed to revoke token for a given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
@app.route('/category/')
def show_categories():
    '''Displays all categories'''
    # query categories
    categories = session.query(Category).all()
    # query last items filtering by date/time added
    items = session.query(Item).order_by(desc(Item.date_added)).limit(5).all()
    return render_template('showCategories.html', categories=categories, items=items)
    # return "This will display list of categories"


@app.route('/category/<string:category>', methods=['GET', 'POST'])
def specific_category(category):
    '''Displays items in a specific category'''
    # query category you are in
    category = session.query(Category).filter_by(name=category).first()
    items = session.query(Item).filter_by(category_id=category.id).all()
    return render_template('showSpecificCategory.html', category=category, items=items)
    # return "This will display list of category %s items" %(category)


@app.route('/category/add', methods=['GET', 'POST'])
def add_category():
    '''Adds a new category'''
    if request.method == 'POST':
        new_category_name = request.form['newCategoryName']
        new_category = Category(name=new_category_name)
        session.add(new_category)
        session.commit()
        return redirect(url_for('show_categories'))
    else:
        return render_template('addCategory.html')


@app.route('/category/<string:category_name>/edit', methods=['GET', 'POST'])
def edit_category(category_name):
    '''Edit a category'''
    category_to_edit = session.query(Category).filter_by(name=category_name).one()
    if request.method == 'POST':
        category_to_edit.name = request.form['editedCategoryName']
        session.add(category_to_edit)
        session.commit()
        return redirect(url_for('show_categories'))
    else:
        return render_template('editCategory.html', category_to_edit=category_to_edit)


@app.route('/category/<string:category_name>/delete/', methods=['GET', 'POST'])
def delete_category(category_name):
    '''Delete a category'''
    category_to_delete = session.query(Category).filter_by(name=category_name).first()
    if request.method == 'POST':
        session.delete(category_to_delete)
        session.commit()
        return redirect(url_for('show_categories'))
    else:
        return render_template('deleteCategory.html', category_to_delete=category_to_delete)


@app.route('/category/<string:category>/<string:item>', methods=['GET', 'POST'])
def specific_item(category, item):
    '''Show an item and its descripton'''
    category = session.query(Category).filter_by(name=category).one()
    item = session.query(Item).filter_by(name=item).first()
    return render_template('showItem.html', category=category, item=item)
    # return "This will return item %s in category %s and its description" %(item, category)


@app.route('/category/<string:category>/add', methods=['GET', 'POST'])
def add_item(category):
    '''Adds an item to a category'''
    category_selected = session.query(Category).filter_by(name=category).one()
    if request.method == 'POST':
        # pick item name and description from the form
        item_name = request.form['newItem']
        item_description = request.form['newItemDescription']
        new_item = Item(name=item_name, description=item_description, category=category_selected)
        # add item to the db
        session.add(new_item)
        session.commit()
        return redirect(url_for('specific_category', category=category_selected.name), code=302)
    else:
        return render_template('addItem.html', category_selected=category_selected)
    # return "This will let you add item %s in category %s" %(item, category)



@app.route('/category/<string:category>/<string:item>/edit', methods=['GET', 'POST'])
def edit_item(category, item):
    '''Edit an item in a category'''
    category_selected = session.query(Category).filter_by(name=category).one()
    item_to_edit = session.query(Item).filter_by(name=item).first()
    if request.method == 'POST':
        # pick edited item details
        item_to_edit.name = request.form['editedItemName']
        item_to_edit.description = request.form['editedItemDescription']
        # add edited item to db
        session.add(item_to_edit)
        session.commit()
        return redirect(url_for('specific_item', category=category_selected.name, item=item_to_edit.name))
    else:
        return render_template('editItem.html', category_selected=category_selected,
                               item_to_edit=item_to_edit)
    # return "This will let you edit item %s in category %s and its description" %(item, category)


@app.route('/category/<string:category>/<string:item>/delete', methods=['GET', 'POST'])
def delete_item(category, item):
    '''Delete an item in a category'''
    category_selected = session.query(Category).filter_by(name=category).one()
    item_to_delete = session.query(Item).filter_by(name=item).first()
    if request.method == 'POST':
        session.delete(item_to_delete)
        session.commit()
        return redirect(url_for('specific_category', category=category_selected.name))
    else:
        return render_template('deleteItem.html', category_selected=category_selected,
                               item_to_delete=item_to_delete)
    # return "This will let you delete item %s in category %s and its description" \
    #         %(item, category)

# Run application on localhost
if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
