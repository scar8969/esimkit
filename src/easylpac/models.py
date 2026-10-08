from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Profile(db.Model):
    __tablename__ = "profiles"
    iccid = db.Column(db.String(32), primary_key=True)
    eid = db.Column(db.String(32), default="")
    carrier = db.Column(db.String(64), default="")
    state = db.Column(db.String(16), default="installed")  # installed|enabled|disabled|deleted
    smdp = db.Column(db.String(128), default="")
    installed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    profile_iccid = db.Column(db.String(32), db.ForeignKey("profiles.iccid"))
    kind = db.Column(db.String(16), default="")
    message = db.Column(db.String(256), default="")
    at = db.Column(db.DateTime, default=datetime.utcnow)
