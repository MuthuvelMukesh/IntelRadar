from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

DB_URL = "sqlite:///antigravity.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class NewsItem(Base):
    """A single news message fetched from a Telegram channel."""
    __tablename__ = "news_items"

    id          = Column(Integer, primary_key=True, index=True)
    source      = Column(String, index=True, default="telegram")
    channel     = Column(String, index=True)
    text        = Column(Text)
    date        = Column(DateTime, default=datetime.utcnow, index=True)
    link        = Column(String, unique=True, index=True)

    # LLM-enriched fields
    category    = Column(String, index=True, nullable=True)
    region      = Column(String, nullable=True)           # populated for region category
    tags        = Column(Text, nullable=True)             # JSON list stored as string
    summary     = Column(Text, nullable=True)
    importance  = Column(Integer, default=0)              # 0-10, used for alerts

    def __repr__(self):
        return f"<NewsItem id={self.id} channel={self.channel} category={self.category}>"


class MonitoredChannel(Base):
    """Channels actively monitored by the bot (managed via /addchannel)."""
    __tablename__ = "monitored_channels"

    id          = Column(Integer, primary_key=True)
    username    = Column(String, unique=True, index=True)   # e.g. "coindesk"
    added_by    = Column(BigInteger, nullable=True)          # Telegram user ID
    added_at    = Column(DateTime, default=datetime.utcnow)
    active      = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Channel @{self.username}>"


class UserSubscription(Base):
    """Per-user category and region subscription preferences."""
    __tablename__ = "user_subscriptions"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(BigInteger, index=True)
    chat_id     = Column(BigInteger, index=True)            # for sending messages
    categories  = Column(Text, default="all")               # comma-separated or "all"
    regions     = Column(Text, default="all")
    digest_on   = Column(Boolean, default=True)
    alerts_on   = Column(Boolean, default=False)            # real-time high-importance alerts
    created_at  = Column(DateTime, default=datetime.utcnow)

    def get_categories(self):
        if self.categories == "all":
            return "all"
        return [c.strip() for c in self.categories.split(",") if c.strip()]

    def get_regions(self):
        if self.regions == "all":
            return "all"
        return [r.strip() for r in self.regions.split(",") if r.strip()]


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
