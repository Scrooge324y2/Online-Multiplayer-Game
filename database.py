import bycrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, NVARCHAR, Numeric, Sequence
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
#engine = create_engine('sqlite:///database.db', echo=True)
engine = create_engine('sqlite:///:memory:', echo=True)

Session = sessionmaker(bind-engine)
session = Session()

class Base(declarative_base()):
    __abstract__ = True
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Users(Base):
    __tablename__ = 'users'
    UserID = Column(Integer, Sequence('user_id_seq'), primary_key=True) #Sequence() automatically increments the UserID
    Username = Column(VARCHAR, nullable=False)
    BycryptHash = Column(VARCHAR, nullable=False
                        

    @staticmethod
    def add_user(username, password):
        bytes = password.encode('utf-8) # converting password to array of bytes
        salt = bycrypt.gensalt() 
        hash = bycrypt.hashpw(bytes, salt) # hashing the password
        user = Users(Username=username, BycryptHash=hash)

    @staticmethod
    def validate_username(username): #checks if a specific username exists in the database (usernames are unique)
        stmt = select(Users).where(Users.Username == username)
        result = ssession.execute(stmt).first()
        return result is not None

    @staticmethod
    def authenticate_user(username_entered, password_entered):
        bytes = password.encode('utf-8) # converting password to array of bytes
        hash = session.execute(select(Users.BycryptHash).where(Users.Username == username))
        result = bycrypt.checkpw(bytes, hash)
        return result
        
     

class UserGames(Base):
    __tablename__ = 'user_games'
    UserID = Column(Integer, ForeignKey('users.UserID'))
    GameID = Column(Integer, ForeignKey('games.GameID'))

class Games(Base):
    __tablename__ = 'games'
    GameID = Column(Integer, Sequence('game_id_seq'), primary_key=True)
    Score = Column(Integer)
    Outcome = Column(VARCHAR)
    StartTime = Column(Time)
    EndTime = Column(End)
    RandomSeed = Column(Integer)
    
    
    

    
