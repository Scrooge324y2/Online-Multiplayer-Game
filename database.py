import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Time, DateTime, ForeignKey, Integer, NVARCHAR, Numeric, Sequence, select, VARCHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
engine = create_engine('sqlite:///database.db', echo=True)
#engine = create_engine('sqlite:///:memory:', echo=True)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()


class User(Base):
    __tablename__ = 'users'
    UserID = Column(Integer, Sequence('user_id_seq'), primary_key=True) #Sequence() automatically increments the UserID
    Username = Column(VARCHAR, nullable=False)
    BcryptHash = Column(VARCHAR, nullable=False)
                        

    @staticmethod #doesn't require an instance of the class to be called
    def add_user(username, password):
        passwordBytes = password.encode('utf-8') # converting password to array of bytes
        salt = bcrypt.gensalt()
        hashedPw = bcrypt.hashpw(passwordBytes, salt).decode('utf-8') # hashing the password
        user = User(Username=username, BcryptHash=hashedPw)
        session.add(user)
        session.commit()

    @staticmethod
    def validate_username(username): #checks if a specific username exists in the database (usernames are unique)
        stmt = select(User).where(User.Username == username)
        result = session.execute(stmt).first()
        return result is None

    @staticmethod
    def authenticate_user(usernameEntered, passwordEntered):
        bytesPw = passwordEntered.encode('utf-8') # converting password to array of bytes
        result = session.execute(select(User.BcryptHash).where(User.Username == usernameEntered)).first()
        if result:
            stored_hash = result[0].encode('utf-8')
            return bcrypt.checkpw(bytesPw, stored_hash)
        return False
        
     

class UserGame(Base):
    __tablename__ = 'user_games'
    UserID = Column(Integer, ForeignKey('users.UserID'), primary_key=True)
    GameID = Column(Integer, ForeignKey('games.GameID'), primary_key=True)

    @staticmethod
    def add_user_game(user_id, game_id):
        user_game = UserGame(UserID=user_id, GameID=game_id)
        session.add(user_game)
        session.commit()

class Game(Base):
    __tablename__ = 'games'
    GameID = Column(Integer, Sequence('game_id_seq'), primary_key=True)
    WinnerID = Column(Integer)
    StartTime = Column(DateTime)
    EndTime = Column(DateTime)
    RandomSeed = Column(Integer)

    @staticmethod
    def add_game(self, score, winnerID, start_time, end_time, random_seed):
        game = Game(Score=score, WinnerID=winnerID, StartTime=start_time, EndTime=end_time, RandomSeed=random_seed)
        session.add(game)
        session.commit()


Base.metadata.create_all(engine)
    
    

    
