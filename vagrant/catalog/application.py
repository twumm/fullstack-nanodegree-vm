from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User

app = Flask(__name__)

# Connect to the database and create a db sessionmaker
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

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
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
