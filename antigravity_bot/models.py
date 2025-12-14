from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from datetime import datetime
from .db import Base

class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)  # e.g., "telegram", "newsapi"
    channel = Column(String, index=True) # e.g., "channel_name", "website_name"
    text = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)
    link = Column(String, unique=True, index=True) # Used for deduplication
    
    # LLM enriched fields
    category = Column(String, index=True, nullable=True) # e.g., "crypto", "markets"
    tags = Column(String, nullable=True) # Comma-separated tags
    summary = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<NewsItem(id={self.id}, source={self.source}, link={self.link})>"
