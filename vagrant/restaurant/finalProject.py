from flask import Flask, render_template, url_for, request, redirect

# CRUD operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem

# create flask app
app = Flask(__name__)

# create session to enable DB connection
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

'''#Fake Restaurants
restaurant = {'name': 'The CRUDdy Crab', 'id': '1'}

restaurants = [{'name': 'The CRUDdy Crab', 'id': '1'}, {'name':'Blue Burgers', 'id':'2'},{'name':'Taco Hut', 'id':'3'}]

#Fake Menu Items
items = [{'name':'Cheese Pizza', 'description':'made with fresh cheese', 'price':'$5.99', 'course' :'Entree', 'id':'1'},
         {'name':'Chocolate Cake', 'description':'made with Dutch Chocolate', 'price':'$3.99', 'course':'Dessert', 'id':'2'},
         {'name':'Caesar Salad', 'description':'with fresh organic vegetables', 'price':'$5.99', 'course':'Entree', 'id':'3'},
         {'name':'Iced Tea', 'description':'with lemon', 'price':'$.99', 'course':'Beverage', 'id':'4'},
         {'name':'Spinach Dip', 'description':'creamy dip with fresh spinach', 'price':'$1.99', 'course':'Appetizer', 'id':'5'}]

item = {'name':'Cheese Pizza', 'description':'made with fresh cheese', 'price':'$5.99', 'course' :'Entree'}'''

# page to list all restaurants
@app.route('/')
@app.route('/restaurants/')
def showRestaurants():
    restaurants = session.query(Restaurant).all()
    return render_template('restaurants.html', restaurants=restaurants)
    # return "This page will show all my restaurants"

# create a new restaurant
@app.route('/restaurants/new/', methods=['GET', 'POST'])
def newRestaurant():
    # query all restaurants from db and store in the variable restaurants
    restaurants = session.query(Restaurant).all()
    if request.method == 'POST':
        newItem = Restaurant(name=request.form['newRestaurant'])
        session.add(newItem)
        session.commit()
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('newRestaurant.html', restaurants=restaurants)
    # return "This page will be for a new restaurant"

# edit a restaurant
@app.route('/restaurant/<int:restaurant_id>/edit/', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    # select the restaurant to edit
    restaurantToEdit = session.query(Restaurant).filter_by(id=restaurant_id).one()
    # if the form's method is post, change restaurant name to user input and add to db
    if request.method == "POST":
        if request.form['editedRestaurantName']:
            restaurantToEdit.name = request.form['editedRestaurantName']
            restaurantToEdit = Restaurant(name=request.form['editedRestaurantName'])
            session.add(restaurantToEdit)
            session.commit()
            return redirect(url_for('showRestaurants'))
    else:
        return render_template('editRestaurant.html', restaurant_id=restaurantToEdit.id, restaurant_name=restaurantToEdit.name)
    # return "This page will be for editing %s" %restaurant_id

# delete a restaurant
@app.route('/restaurant/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    restaurantToDelete = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if request.method == 'POST':
        session.delete(restaurantToDelete)
        session.commit()
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('deleteRestaurant.html', restaurant_id=restaurantToDelete.id, deletedRestaurant=restaurantToDelete)
    # return "This page will be for deleting %s" %restaurant_id

# page to list all menu items of a particular restaurant
@app.route('/restaurant/<int:restaurant_id>/menu/')
def showMenu(restaurant_id):
    menuItems = session.query(MenuItem).filter_by(restaurant_id=restaurant_id)
    return render_template('menu.html', restaurant_id=restaurant_id, menuItems=menuItems)
    # return "This page is the menu for restaurant %s" %restaurant_id

# create a new menu item
@app.route('/restaurant/<int:restaurant_id>/menu/new/', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    # restaurant_to_add_menu = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if request.method == 'POST':
        # add the new menu item details to the database with restaurant_id as id/foreign key
        new_menu_item = MenuItem(name=request.form['newMenuItem'],
                                 course=request.form['newMenuCourse'],
                                 description=request.form['newMenuDescription'],
                                 price=request.form['newMenuPrice'],
                                 restaurant_id=restaurant_id)
        session.add(new_menu_item)
        session.commit()
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template('newMenuItem.html', restaurant_id=restaurant_id)
    # return "This page is for making a new menu item for restaurant %s" %restaurant_id

# edit a menu item
@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/edit/', methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
    # TODO -- check how the menu to edit is being picked?
    menu_to_edit = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        menu_to_edit.name = request.form['menuName']
        menu_to_edit.course = request.form['menuCourse']
        menu_to_edit.description = request.form['menuDescription']
        menu_to_edit.price = request.form['menuPrice']
        session.add(menu_to_edit)
        session.commit()
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template('editMenuItem.html', restaurant_id=restaurant_id,
                               menu_to_edit=menu_to_edit)
    # return "This page is for editing menu item %s" %menu_id

# delete a menu item
@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete/', methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    menu_to_delete = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        session.delete(menu_to_delete)
        session.commit()
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template('deleteMenuItem.html', restaurant_id=restaurant_id,
                               menu_id=menu_id, menu_to_delete=menu_to_delete)
    # return "This page is for deleing menu item %s" %menu_id

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
