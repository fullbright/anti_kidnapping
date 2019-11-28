from sqlalchemy import Column, Integer, String, \
    Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

db_str = 'postgres://agzvarxu:PrM4uplKO3suxsBSts8c57'\
         'w3h8uxie6X@balarama.db.elephantsql.com:5432/agzvarxu'
# db_str = 'postgres://admin:admin@localhost:5432/antikidnapping'
db = create_engine(db_str)

Base = declarative_base()


class Child(Base):
    __tablename__ = 'child'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    photo_id = Column(String)
    is_inside = Column(Boolean)
    parents = relationship('Parent')

    def __init__(self, name, photo_id, is_inside=True):
        self.name = name
        self.photo_id = photo_id
        self.is_inside = is_inside

    def __repr__(self):
        return "<Child('%s','%s', '%s')>" % (
            self.name, self.is_inside, self.photo_id)


class Parent(Base):
    __tablename__ = 'parent'
    id = Column(Integer, primary_key=True)
    photo_id = Column(String)
    child_id = Column(Integer, ForeignKey('child.id'))

    def __init__(self, photo_id, child_id):
        self.photo_id = photo_id
        self.child_id = child_id

    def __repr__(self):
        return "<Parent('%d', '%s')>" % (self.child_id, self.photo_id)


Session = sessionmaker(db)
session = Session()

Base.metadata.create_all(db)
