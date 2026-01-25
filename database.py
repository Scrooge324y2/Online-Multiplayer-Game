import bcrypt
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, declarative_base, aliased
from sqlalchemy import Column, Time, DateTime, ForeignKey, Integer, NVARCHAR, Numeric, Sequence, select, VARCHAR
from sqlalchemy.sql import func, desc
engine = create_engine('sqlite:///database.db', echo=True)
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

    @staticmethod
    def get_user_id(username):
        result = session.execute(select(User.UserID).where(User.Username == username)).first()
        if result:
            return result[0]
        return None

    @staticmethod
    def get_top_10_by_wins():
        stmt = (
            select(
                User.Username,
                func.count(Game.GameID).label("wins")
            )
            .join(Game, Game.WinnerID == User.UserID)
            .group_by(User.UserID)
            .order_by(desc("wins"))
            .limit(10)
        )

        results = session.execute(stmt).all()
        return results

    @staticmethod
    def get_game_history(user_id):
        opponent_ug = aliased(UserGame)

        games = (
            session.execute(
                select(Game, User)
                .join(UserGame, UserGame.GameID == Game.GameID)
                .join(opponent_ug, and_(
                    opponent_ug.GameID == Game.GameID,
                    opponent_ug.UserID != user_id
                ))
                .join(User, User.UserID == opponent_ug.UserID)
                .where(UserGame.UserID == user_id)
                .order_by(Game.GameID.desc())

            )
        ).all()
        history = []


        for game, opponent in games:
            won = (game.WinnerID == user_id)

            total_seconds = int((game.EndTime - game.StartTime).total_seconds())

            minutes = total_seconds // 60
            seconds = total_seconds % 60

            history.append({
                'won': won,
                'duration': f"{minutes}:{seconds:02d}",
                'date_played': game.StartTime.date(),
                'opponent_username': opponent.Username
            })
        return history

    @staticmethod
    def get_win_rate(user_id):
        games_played = session.execute(
            select(func.count())
            .select_from(UserGame)
            .where(UserGame.UserID == user_id)
        ).scalar()

        if games_played == 0:
            return 0.0

        wins = session.execute(
            select(func.count())
            .select_from(Game)
            .join(UserGame, UserGame.GameID == Game.GameID)
            .where(
                UserGame.UserID == user_id,
                Game.WinnerID == user_id
            )
        ).scalar()

        return round((wins / games_played) * 100, 2)




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
    def add_game(winnerID, start_time, end_time, random_seed):
        game = Game(WinnerID=winnerID, StartTime=start_time, EndTime=end_time, RandomSeed=random_seed)
        session.add(game)
        session.commit()
        return game.GameID



Base.metadata.create_all(engine)
    
    


    
