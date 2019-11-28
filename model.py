from sqlalchemy import Column, Integer, String, \
    Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker


db = create_engine(
    'postgres://admin:admin@localhost:5432/antikidnapping')

Base = declarative_base()


class Child(Base):
    __tablename__ = 'child'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    photo_url = Column(String)
    is_inside = Column(Boolean)
    parents = relationship('Parent')

    def __init__(self, name, photo_url, is_inside=True):
        self.name = name
        self.photo_url = photo_url
        self.is_inside = is_inside

    def __repr__(self):
        return "<Child('%s','%s', '%s')>" % (self.name, self.is_inside, self.photo_url)


class Parent(Base):
    __tablename__ = 'parent'
    id = Column(Integer, primary_key=True)
    photo_url = Column(String)
    child_id = Column(Integer, ForeignKey('child.id'))

    def __init__(self, photo_url, child_id):
        self.photo_url = photo_url
        self.child_id = child_id

    def __repr__(self):
        return "<Parent('%d', '%s')>" % (self.child_id, self.photo_url)


Session = sessionmaker(db)
session = Session()

Base.metadata.create_all(db)
