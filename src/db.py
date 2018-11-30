from flask_sqlalchemy import SQLAlchemy
import time
#from sqlalchemy_imageattach.entity import Image, image_attachment

db = SQLAlchemy()

class Interest(db.Model):
    __tablename__ = 'interest'
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=False, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False, primary_key=True)
    def __init__(self, **kwargs):
        self.uid = kwargs.get('uid')
        self.post_id = kwargs.get('post_id')
    def serialize(self):
        return {
            'uid': self.uid,
            'post_id': self.post_id
        }

"""
Interest = db.Table('interest',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('uid', db.Integer, db.ForeignKey('user.uid'), primary_key=True)
)
"""

class User(db.Model):
    __tablename__ = 'user'
    uid = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    profile_photo = db.Column(db.String, nullable=True)
    major_minor = db.Column(db.String, nullable=False)
    contact_info = db.Column(db.String, nullable=False)
    skills = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)
    class_year = db.Column(db.String, nullable=False)
    courses_taken = db.Column(db.String, nullable=False)
    blurb = db.Column(db.String, default="", nullable=False)
    past_projects = db.relationship('PastProject', cascade='delete')

    #location = db.Column(db.String, nullable=False)
    creation_time=db.Column(db.Float, nullable=False) # time.time called during creation
    posts = db.relationship('Post', cascade='delete')
    comments = db.relationship('Comment', cascade='delete')
    interested = db.relationship('Interest', cascade='delete')
    """interested = db.relationship('Post', secondary=Interest, lazy='subquery',
        backref=db.backref('user', lazy=True))"""
    
    def __init__(self, **kwargs):
        self.name = kwargs.get('name')
        self.active = True
        self.profile_photo = kwargs.get('profile_photo')
        self.major_minor = kwargs.get('major_minor')
        self.contact_info = kwargs.get('contact_info')
        self.skills = kwargs.get('skills')
        self.role = kwargs.get('role')
        self.class_year = kwargs.get('class_year')
        self.courses_taken = kwargs.get('courses_taken')
        self.blurb = kwargs.get('blurb')
        #self.location = kwargs.get('location')
        self.creation_time = kwargs.get('creation_time')

    def serialize_profile(self):
        return {
            'uid': self.uid,
            'name': self.name,
            'active': self.active,
            'profile_photo': self.profile_photo,
            'major_minor': self.major_minor,
            'contact_info': self.contact_info,
            'skills': self.skills,
            'role': self.role,
            'class_year': self.class_year,
            'courses_taken': self.courses_taken,
            #'location': self.location,
            'blurb': self.blurb,
            'creation_time': self.creation_time,
        }
    
    def serialize_short(self):
        return {}
    
"""
class UserPicture(db.Model, Image):
    __tablename__ = 'user_picture'
    uid = db.Column(db.Integer, db.ForeignKey('user.uid')  primary_key=True)
    user = db.relationship('User', cascade='delete')
"""

class Post(db.Model):
    __tablename__ = 'post'

    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=False)
    title = db.Column(db.String, nullable=False)
    tags = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)
    text = db.Column(db.String, nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    comments = db.relationship('Comment', cascade='delete')
    creation_time = db.Column(db.Float, nullable=False) # time.time called during creation
    interested = db.relationship('Interest', cascade='delete')
    photos = db.relationship('Photo', cascade='delete')
 

    kind = db.Column(db.Integer, nullable=False)
    # 0: study group
    course = db.Column(db.String, nullable=True)
    # 1: project seeking members
    group_size = db.Column(db.String, nullable=True)
    # 2: person seeking project
    skills = db.Column(db.String, nullable=True)

    def __init__(self, **kwargs):
        self.uid = kwargs.get('uid')
        self.title = kwargs.get('title')
        self.tags = kwargs.get('tags')
        self.role = kwargs.get('role')
        self.text = kwargs.get('text')
        self.active = True
        self.creation_time = kwargs.get('creation_time')

        self.kind = kwargs.get('kind')
        if self.kind == 0:
            self.course = kwargs.get('course')
        if self.kind == 1:
            self.group_size = kwargs.get('group_size')
        if self.kind == 2:
            self.skills = kwargs.get('skills')
    
    def serialize(self):
        #if self.kind==
        ubiquitious = {
            'id': self.id,
            'uid': self.uid,
            'title': self.title,
            'tags': self.tags,
            'role': self.role,
            'text': self.text,
            'active': self.active,
            'creation_time': self.creation_time,
            'kind': self.kind,
        }
        if self.kind == 0:
            ubiquitious['course'] = self.course
        if self.kind == 1:
            ubiquitious['group_size'] = self.group_size
        if self.kind == 2:
            ubiquitious['skills'] = self.skills
        return ubiquitious

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=False)
    creation_time = db.Column(db.Float, nullable=False) # time.time called during creation
    
    def __init__(self, **kwargs):
        self.text = kwargs.get('text')
        self.post_id = kwargs.get('post_id')
        self.uid = kwargs.get('uid')
        self.creation_time = kwargs.get('creation_time')

    def serialize(self):
        return {
            'id': self.id,
            'text': self.text,
            'post_id': self.post_id,
            'uid': self.uid,
            'creation_time': self.creation_time
        }

class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    def __init__(self, **kwargs):
        self.name = kwargs.get('name')

class StaffRequest(db.Model):
    __tablename__ = 'staff_request'
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=True)
    email = db.Column(db.String, nullable=False)
    text = db.Column(db.String, nullable=False)
    creation_time = db.Column(db.Float, nullable=False) # time.time called during creation
    addressed = db.Column(db.Boolean, nullable=False)
    address_time = db.Column(db.Float, nullable=True)

    def __init__(self, **kwargs):
        self.uid = kwargs.get('uid')
        self.email = kwargs.get('email')
        self.text = kwargs.get('text')
        self.creation_time = kwargs.get('creation_time')
        self.addressed = False
        self.address_time = None
    
    def serialize_short(self):
        return {
            'id': self.id,
            'uid': self.uid,
            'email': self.email,
            'text': self.text,
            'creation_time': self.creation_time
        }

    def serialize(self):
        return {
            'id': self.id,
            'uid': self.uid,
            'email': self.email,
            'text': self.text,
            'creation_time': self.creation_time,
            'addressed': self.addressed,
            'address_time': self.address_time
        }

class Authentication(db.Model):
    __tablename__ = 'authentication'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.Integer, nullable=False)
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=True)
    first_login = db.Column(db.Float, nullable=False)
    last_login = db.Column(db.Float, nullable=False)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)

    def __init__(self, **kwargs):
        self.token = kwargs.get('token')
        self.uid = kwargs.get('uid')
        self.first_login = kwargs.get('first_login')
        self.last_login = self.first_login
        self.email = kwargs.get('email')
        self.password = kwargs.get('password')
    
    def deliver(self):
        return {'token': self.token, 'uid': self.uid}

class Photo(db.Model):
    __tablename__ = 'photo'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    val = db.Column(db.String, nullable=False)
    def __init__(self, **kwargs):
        self.val = kwargs.get('val')
        self.post_id = kwargs.get('post_id')
    def serialize(self):
        return {
            'id': self.id,
            'val': self.val,
            'post_id': self.post_id
        }

class PastProject(db.Model):
    __tablename__ = 'past_project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    skills = db.Column(db.String, nullable=False)
    link = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.Float, nullable=False)
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=False)
    def __init__(self, **kwargs):
        self.uid = kwargs.get('uid')
        self.name = kwargs.get('name')
        self.skills = kwargs.get('skills')
        self.link = kwargs.get('link')
        self.description = kwargs.get('description')
        self.timestamp = kwargs.get('timestamp')
    def serialize(self):
        return {
            'id': self.id,
            'uid': self.uid,
            'name': self.name,
            'skills': self.skills,
            'link': self.link,
            'description': self.description,
            'timestamp': self.timestamp
        }
