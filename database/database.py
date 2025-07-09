from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class DBManager:
    def __init__(self, db_url: str = "sqlite:///xui_bot.db"):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.SessionLocal()
