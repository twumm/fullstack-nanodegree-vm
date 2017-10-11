import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(Base):
    '''creates a user instance to be stored in the user table in the catalog app'''
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    picture = Column(String(250))
    email = Column(String(100), nullable=False)


class Category(Base):
    '''creates a category instance to be stored in the categories table in the catalog app'''
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    items = relationship("Item", cascade="all, delete-orphan")

    @property
    def serialize(self):
        '''Returns a json of the category requested'''
        return {
        'name': self.name
    }


class Item(Base):
    '''creates an item instance to be stored in the items table in the catalog app'''
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(1000))
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    date_added = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def serialize(self):
        '''Returns a json of the item requested'''
        return {
        'name': self.name,
        'description': self.description,
        'date added' : self.date_added
    }


engine = create_engine('postgres://gvnojbpchanxvs:6873e7b0f778be02ea62a'
                       'de0e549eac0afa5fe4f6ea704a788c4d94c05ce1e27@ec2'
                       '-23-23-93-255.compute-1.amazonaws.com:5432/deqf'
                       '8tfcuf9813')

Base.metadata.create_all(engine)
