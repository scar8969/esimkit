-- 📱 EasyLPAC schema
CREATE TABLE profiles(iccid TEXT PRIMARY KEY, eid TEXT, carrier TEXT, state TEXT DEFAULT 'installed', smdp TEXT, installed_at DATETIME);
CREATE TABLE notifications(id INTEGER PRIMARY KEY, profile_iccid TEXT REFERENCES profiles(iccid), kind TEXT, message TEXT, at DATETIME);
