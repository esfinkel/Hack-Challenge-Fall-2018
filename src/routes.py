from flask import Flask, request
#from sqlalchemy_imageattach.stores.fs import HttpExposedFileSystemStore
from db import db, User, Interest, Post, Comment, StaffRequest, Authentication
from db import Course, Photo, PastProject
from sqlalchemy import or_, func
import json
import time, datetime
import random

app = Flask(__name__)
db_filename = "testfile1.db"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///%s' % db_filename
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

#fs_store = HttpExposedFileSystemStore('user_picture', 'images/')
#app.wsgi_app = fs_store.wsgi_middleware(app.wsgi_app)

db.init_app(app)
with app.app_context():
  db.create_all()


def missing():
  return json.dumps({'success': False, 'data': 'Missing required fields'}), 400

def nouser():
  return json.dumps({'success': False, 'error': 'User not found! They may be inactive.'}), 404

def nopost():
  return json.dumps({'success': False, 'error': 'Post not found! It may be inactive.'}), 404

def nocomment():
  return json.dumps({'success': False, 'error': 'Comment not found!'}), 404

def activate(uid):
  user = User.query.filter_by(uid=uid).first()
  if user:
    user.active = True
    db.session.commit()

def clean_courses(courses, num=0):
  if not courses:
    return courses
  courses = [course.upper().replace(' ','') for course in courses.split(',')]
  if num and num <= courses.length:
    courses = courses[:num]
  return ', '.join(courses)

def clean_tags(tags):
  if not tags:
    return tags
  tags = [tag.strip() for tag in tags.split(',')]
  return ', '.join(tags)

def new_token():
  t = round(random.uniform(0,3372036854775807))
  while Authentication.query.filter_by(token=t).first() is not None:
    round(random.uniform(0,3372036854775807))
  return t

def wrong_token():
  return json.dumps({'success': False, 'error': 'Invalid token - not connected with the correct user.'}), 401

def invalid_token():
  return json.dumps({'success': False, 'error': 'Invalid token - not connected with any user.'}), 401

def token_to_uid(token):
  if type(token) not in [str, int]:
    token = token.get('token',0)
  if type(token) == str:
    token = int(token)
  session = Authentication.query.filter_by(token=token).first()
  if session is None:
    return None
  return session.uid

def extract(req):
  try:
    re = json.loads(req.data)
  except:
    re = req.args
  return re

@app.route('/api/login/create/', methods=['POST'])
def create_acc():
  acc_info = extract(request)
  if not (acc_info.get('email','') and acc_info.get('password','')):
    return missing()
  current = Authentication.query.filter_by(email=acc_info.get('email')).first()
  if current:
    if current.uid is not None:
      return json.dumps({'success': False, 'error': 'Account already exists with that email.'}), 400
    else:
      db.session.delete(current)
  auth = Authentication(
    token = new_token(),
    first_login = time.time(),
    email = acc_info.get('email'),
    password = acc_info.get('password'),
    uid=None
  )
  db.session.add(auth)
  db.session.commit()
  return json.dumps({'success': True, 'data': auth.deliver()}), 201

@app.route('/api/debug/')
def debug():
  re = request.args
  a = re.get('a','')
  return json.dumps({'success': True, 'data': a}), 200

@app.route('/api/users/', methods=['POST'])
def add_user():
  user_info = extract(request)
  #ask iOS to set it so user can't submit form without data:
  if not all(user_info.get(i,'') for i in ['name','contact_info','token']):
    return missing()
  token = user_info.get('token')
  if token_to_uid(token):
    return invalid_token()
  user = User(
    name = user_info.get('name'),
    profile_photo = user_info.get('profile_photo', None),
    major = user_info.get('major', ''),
    minor = user_info.get('minor', ''),
    contact_info = user_info.get('contact_info'),
    skills = clean_tags(user_info.get('skills', '')),
    role = clean_tags(user_info.get('role', '')),
    class_year = user_info.get('class_year', ''),
    courses_taken = clean_courses(user_info.get('courses_taken', '')),
    #location = user_info.get('location', ''),
    blurb = user_info.get('blurb', ''),
    creation_time = time.time()
  )
  db.session.add(user)
  db.session.commit()
  auth = Authentication.query.filter_by(token=token).first()
  auth.uid = user.uid
  db.session.commit()
  return json.dumps({'success': True, 'data': user.serialize_profile()}), 201

@app.route('/api/login/', methods=['POST'])
def login():
  login_info = extract(request)
  if not all(login_info.get(i,'') for i in ['email','password']):
    return missing()
  user = Authentication.query.filter_by(
    email=login_info.get('email'),
    password=login_info.get('password')
  ).first()
  if not user:
    if Authentication.query.filter_by(email=login_info.get('email')).first():
      return json.dumps({'success': False, 'error': 'Incorrect password'}), 404
    return json.dumps(
      {'success': False, 'error': 'User not found with that email and password combination'}
    ), 404
  user.last_login = time.time()
  user.token = new_token()
  db.session.commit()
  return json.dumps({'success': True, 'data': user.deliver()}), 200

@app.route('/api/login/', methods=['GET'])
def is_logged_in():
  uid = token_to_uid(extract(request))
  logged_in = (uid is not None)
  """  if uid==0 and type(uid)==int:
      logged_in = True"""
  return json.dumps({'success': True, 'data': logged_in}), 200

@app.route('/api/users/profile/<int:uid>/')
def get_user_profile(uid):
  user = User.query.filter_by(uid=uid).first()
  if user is None:
    return nouser()
  return json.dumps({'success': True, 'data': user.serialize_profile()}), 200

@app.route('/api/users/short/<int:uid>/')
def get_user_short(uid):
  user = User.query.filter_by(uid=uid).first()
  if user is None:
    return nouser()
  return json.dumps({'success': True, 'data': user.serialize_short()}), 200

@app.route('/api/users/allinfo/')
def get_all_user_info():
  users = User.query.all()
  info = [user.serialize_profile() for user in users]
  return json.dumps({'success': True, 'data': info}), 200

@app.route('/api/users/search/')
def search_users():
  try:
    search = extract(request)
  except:
    search = {}
  info = {
    'name': search.get('name', ''), 
    'major': search.get('major', ''),
    'minor': search.get('minor', ''),
    'class_year': search.get('class_year', ''),
    'courses_taken': clean_courses(search.get('courses_taken', '')),
    'skills': clean_tags(search.get('skills', '')),
    'role': clean_tags(search.get('role', ''))
    #'location': search.get('location', ''),
    #'blurb': search.get('blurb', '')
  }
  info = {k:v.lower() for k,v in info.items()}
  working_userlist = User.query
  working_userlist.filter_by(active=True)
  if info['name']:
    working_userlist = working_userlist.filter(func.lower(User.name) == info['name'])
  if info['major']:
    working_userlist = working_userlist.filter(or_(
      User.major.contains(mm) for mm in info['major'].split(', ')
    ))
  if info['class_year']:
    working_userlist = working_userlist.filter(func.lower(User.class_year) == info['class_year'])  
  if info['courses_taken']:
    working_userlist = working_userlist.filter(or_(
      func.lower(User.courses_taken).contains(cor) for cor in info['courses_taken'].split(', ')
    ))
  if info['skills']:
    working_userlist = working_userlist.filter(or_(
      func.lower(User.skills).contains(sk) for sk in info['skills'].split(', ')
    ))  
  if info['role']:
    working_userlist = working_userlist.filter(or_(
      func.lower(User.role).contains(ro) for ro in info['role'].split(', ')
    ))  
  userlist = working_userlist.all()
  ids = [user.uid for user in userlist]
  return json.dumps({'success': True, 'data': ids} ), 200

@app.route('/api/posts/search/')
def search_posts():
  search = extract(request)
  if 'kind' not in search:
    return missing()
  info = {
    'skills': clean_tags(search.get('skills', '')).lower(),
    'role': clean_tags(search.get('role', '')).lower(),
    'kind': int(search.get('kind')),
    'uid': search.get('uid', None),
    'group_size': None,
    'tags': None
  }
  kind = info['kind']
  if info['uid'] is not None:
    info['uid'] = int(info['uid'])
  if kind==1:
    info['group_size'] = search.get('group_size', None)
  if kind==2:
    info['tags'] = clean_tags(search.get('tags', '')).lower()
  
  working_postlist = Post.query
  working_postlist = working_postlist.filter_by(active=True,kind=kind)
  if info['skills']:
    working_postlist = working_postlist.filter(or_(
      func.lower(Post.skills).contains(skill) for skill in info['skills'].split(', ')
    ))
  if info['role']:
    working_postlist = working_postlist.filter(or_(
      func.lower(Post.role).contains(r) for r in info['role'].split(', ')
    ))
  if info['uid']:
    working_postlist = working_postlist.filter_by(uid=uid)
  if info['group_size']:
    working_postlist = working_postlist.filter_by(group_size=info['group_size'])
  if info['tags']:
    working_postlist = working_postlist.filter(or_(
      func.lower(Post.tags).contains(t) for t in info['tags'].split(', ')
    ))    
  postlist = working_postlist.all()
  return json.dumps({'success': True, 'data': [post.id for post in postlist]} ), 200

@app.route('/api/users/self/')
def get_own_profile():
  search = extract(request)
  uid = token_to_uid(search)
  if uid is None:
    return invalid_token()
  user = User.query.filter_by(uid=uid).first()
  return json.dumps({'success': True, 'data': user.serialize_profile()} ), 200

@app.route('/api/posts/self/')
def own_posts():
  search = extract(request)
  uid = token_to_uid(search.get('token'))
  if uid is None:
    return invalid_token()
  postlist = Post.query.filter_by(uid=uid).all()
  return json.dumps({'success': True, 'data': [post.id for post in postlist]} ), 200

@app.route('/api/posts/', methods=['POST'])
def make_post():
  post_body = extract(request)
  if not all(post_body.get(i,'') for i in ['text', 'token', 'title']):
    return missing()
  if 'kind' not in post_body:
    return missing()
  kind = int(post_body['kind'])
  if kind not in [0,1,2]:
    return missing()
  if kind==1 and ('group_size' not in post_body):
    return missing()
  if kind==1 and ('role' not in post_body):
    return missing()
  uid = token_to_uid(post_body) 
  if uid is None:
    return invalid_token()
  if not kind==0:
    post_body.pop('course',None)
  if not kind==1:
    post_body.pop('group_size',None)
  if not kind==2:
    post_body.pop('skills',None)
  if kind==1:
    role = clean_tags(post_body.get('role',))
  if kind==2:
    role = User.query.filter_by(uid=uid).first().role
  post = Post(
    uid = uid,
    title = post_body.get('title'),
    tags = clean_tags(post_body.get('tags','')),
    role = role,
    text = post_body.get('text'),
    creation_time = time.time(),
    kind = int(post_body.get('kind')),
    course = clean_courses(post_body.get('course_id', None),1),
    group_size = post_body.get('group_size', None),
    skills = clean_tags(post_body.get('skills', None))
  )
  activate(uid)
  db.session.add(post)
  db.session.commit()
  return json.dumps({'success': True, 'data': post.serialize()}), 201

@app.route('/api/posts/<int:id>/')
def get_post_by_id(id):
  post = Post.query.filter_by(id=id, active=True).first()
  if post:
    return json.dumps({'success': True, 'data': post.serialize()}), 200
  return nopost()

@app.route('/api/posts/users/<int:uid>/')
def get_user_posts(uid):
  posts = Post.query.filter_by(uid=uid, active=True).all()
  return json.dumps({'success': True, 'data': [post.serialize() for post in posts]}), 200

@app.route('/api/posts/<int:post_id>/comments/', methods=['POST'])
def add_post_comment(post_id):
  post = Post.query.filter_by(id=post_id, active=True).first()
  if post is None:
    return nopost()
  comment_body = extract(request)
  if 'text' not in comment_body or 'token' not in comment_body:
    return missing()
  uid = token_to_uid(comment_body)
  if uid is None:
    return invalid_token()
  comment = Comment(
    text = comment_body.get('text'),
    uid = uid,
    post_id = post_id,
    creation_time = time.time()
  )
  activate(uid)
  post.comments.append(comment)
  db.session.add(comment)
  db.session.commit()
  return json.dumps({'success': True, 'data':comment.serialize()}), 201

@app.route('/api/posts/<int:post_id>/comments/')
def get_post_comments(post_id):
  comments = Comment.query.filter_by(post_id=post_id).all()
  return json.dumps({'success': True, 'data': [comment.serialize() for comment in comments]}), 200

@app.route('/api/posts/comments/<int:comment_id>/', methods=['POST'])
def modify_comment(comment_id):
  comment = Comment.query.filter_by(id=comment_id).first()
  sender = token_to_uid(extract(request))
  if sender is None:
    return invalid_token()
  if comment is None:
    return nocomment()
  info = extract(request)
  new_text = info.get('text', None)
  if not sender==comment.uid:
    return wrong_token()
  if new_text not in [None, '']:
    comment.text = new_text
    db.session.commit()
  #activate(uid)
  return json.dumps({'success': True, 'data': comment.serialize()}), 200

@app.route('/api/users/profile/modify/', methods=['POST'])
def modify_user():
  info = extract(request)
  uid = token_to_uid(info)
  if uid is None:
    return invalid_token()
  user = User.query.filter_by(uid=uid).first()
  if user is None:
    return nouser()  
  if info.get('name',None)=="":
    info['name'] = user.name
  if info.get('contact_info',None)=="":
    info['contact_info'] = user.contact_info

  # for any fields with no update proposed, leave as is
  info1 = {k: v for k, v in info.items() if v not in [ None]}
  info = info1

  user.name = info.get('name', user.name)
  user.major = info.get('major', user.major)
  user.minor = info.get('minor', user.minor)
  user.contact_info = info.get('contact_info', user.contact_info)
  user.skills = clean_tags(info.get('skills', user.skills))
  user.role = clean_tags(info.get('role', user.role))
  user.class_year = info.get('class_year', user.class_year)
  user.courses_taken = clean_courses(info.get('courses_taken', user.courses_taken))
  #user.location = info.get('location', user.location)
  user.blurb = info.get('blurb', user.blurb)
  user.active = True
  db.session.commit()
  return json.dumps({'success': True, 'data': user.serialize_profile()}), 200

@app.route('/api/posts/<int:id>/modify/', methods=['POST'])
def modify_post(id):
  info = extract(request)
  uid = token_to_uid(info)
  if uid is None:
    return invalid_token()
  post = Post.query.filter_by(id=id).first()
  if post is None:
    return nopost()
  if not post.uid==uid:
    return wrong_token()
  kind = post.kind

  if info.get('title',None)=="":
    info['title'] = post.title
  if info.get('text',None)=="":
    info['text'] = post.text
  if info.get('role',None)=="":
    info['role'] = post.role
  if kind==1 and info.get('group_size',None)=="":
    info['group_size'] = post.group_size

  # for any fields with no update proposed, leave as is
  info1 = {k: v for k, v in info.items() if v not in ['', None]}
  info = info1

  post.title = info.get('title', post.title)
  post.tags = clean_tags(info.get('tags', post.tags))
  if kind==1:
    post.role = clean_tags(info.get('role', post.role))
  if kind==2: 
    post.role = User.query.filter_by(uid=uid).first().role
  post.text = info.get('text', post.text)
  if kind==0:
    post.course = clean_courses(info.get('course', post.course))
  if kind==1:
    post.group_size = info.get('group_size', post.group_size)
  if kind==2:
    post.skills = info.get('skills', post.skills)

  db.session.commit()
  return json.dumps({'success': True, 'data': post.serialize()}), 200

@app.route('/api/users/profile/toggle/', methods=['POST'])
def toggle_user_activity():
  uid = token_to_uid(extract(request))
  if uid is None:
    return invalid_token()
  user = User.query.filter_by(uid=uid).first()
  if user is None:
    return nouser()
  user.active = not user.active
  db.session.commit()
  return json.dumps({'success': True, 'data': user.serialize_profile()}), 200

@app.route('/api/users/profile/photo/', methods=['POST'])
def edit_user_photo():
  uid = token_to_uid(extract(request))
  if uid is None:
    return invalid_token()
  user = User.query.filter_by(uid=uid).first()
  if user is None:
    return nouser()
  info = extract(request)
  user.profile_photo = info.get('profile_photo', user.profile_photo)
  user.active = True
  db.session.commit()
  return json.dumps({'success': True, 'data': user.serialize_profile()}), 200

@app.route('/api/posts/<int:id>/confirm_ownership/')
def confirm_post_ownership(id):
  post = Post.query.filter_by(id=id).first()
  if post is None:
    return nopost()
  post_owner = post.uid
  sender = token_to_uid(extract(request))
  if sender is None:
    return invalid_token()
  match = (post_owner==sender)
  return json.dumps({'success': True, 'data': match}), 200

@app.route('/api/posts/comments/<int:id>/confirm_ownership/')
def confirm_comment_ownership(id):
  comment = Comment.query.filter_by(id=id).first()
  if comment is None:
    return nocomment()
  comment_owner = comment.uid
  sender = token_to_uid(extract(request))
  if sender is None:
    return invalid_token()
  match = (comment_owner==sender)
  return json.dumps({'success': True, 'data': match}), 200

@app.route('/api/posts/<int:id>/toggle/', methods=['POST'])
def toggle_post_activity(id):
  post = Post.query.filter_by(id=id).first()
  uid = token_to_uid(extract(request))
  if uid is None:
    return invalid_token()
  if post is None:
    return nopost()
  if not post.uid == uid:
    return wrong_token()
  post.active = not post.active
  db.session.commit()
  return json.dumps({'success': True, 'data': post.serialize()}), 200

@app.route('/api/posts/comments/<int:comment_id>/', methods=['DELETE'])
def delete_comment(comment_id):
  comment = Comment.query.filter_by(id=comment_id).first()
  if comment is None:
    return nocomment()
  if comment.uid is None:
    return # None
  if token_to_uid(extract(request))==comment.uid:
    db.session.delete(comment)
    db.session.commit()
  else:
    return wrong_token()
  return json.dumps({'success': True, 'data': comment.serialize()}), 200

@app.route('/api/posts/<int:post_id>/interest/', methods=['POST'])
def toggle_post_interest(post_id):
  post = Post.query.filter_by(id=post_id, active=True).first()
  info = extract(request)
  uid = token_to_uid(info)
  user = User.query.filter_by(uid=uid).first()
  if not user or not post:
    return missing()
  if uid is None:
    return invalid_token()
  interest = Interest.query.filter_by(uid=uid, post_id=post_id).first()
  if interest:
    db.session.delete(interest)
  else:
    interest = Interest(
      uid = uid,
      post_id = post_id
    )
    user.interested.append(interest)
    db.session.add(interest)
  db.session.commit()
  return json.dumps({'success': True, 'data': post.serialize()}), 200
  
@app.route('/api/users/interest/')
def find_interested_posts():
  uid = token_to_uid(extract(request))
  if uid is None:
    return invalid_token()
  user = User.query.filter_by(uid=uid).first()
  if not user:
    return nouser()
  posts = [inter.post_id for inter in user.interested]
  return json.dumps({'success': True, 'data': posts}), 200

@app.route('/api/users/interest/number/')
def find_number_interested_posts():
  uid = token_to_uid(extract(request))
  if uid is None:
    return invalid_token()
  user = User.query.filter_by(uid=uid).first()
  if not user:
    return nouser()
  number = len(user.interested)
  return json.dumps({'success': True, 'data': number}), 200

@app.route('/api/staff_request/', methods=['POST'])
def make_request():
  request_info = extract(request)
  if not all(request_info.get(i,'') for i in ['token', 'email', 'text']):
    return missing()
  uid = token_to_uid(request_info)
  """  if User.query.filter_by(uid=uid).first() is None:
    return nouser()"""
  req = StaffRequest(
    uid = uid,
    email = request_info.get('email'),
    text = request_info.get('text'),
    creation_time = time.time()
  )
  db.session.add(req)
  db.session.commit()
  return json.dumps({'success': True, 'data': req.serialize_short()}), 201

@app.route('/api/courses/', methods=['POST'])
def add_courses():
  info = extract(request)
  courses = info.get('courses')
  courses = [course.upper().replace(' ','') for course in courses.split(',')]
  for course in courses:
    if not Course.query.filter_by(name=course).first():
      db.session.add(Course(name=course)) 
  db.session.commit()
  return json.dumps({'success': True, 'data': courses}), 201

@app.route('/api/courses/all/', methods=['GET'])
def get_all_courses():
  cs = Course.query.all()
  return json.dumps({'success': True, 'data': [c.name for c in cs]}), 200

@app.route('/api/courses/', methods=['GET'])
def get_courses():
  start = extract(request).get('start','')
  matching = Course.query.filter(Course.name.contains(start)).all()
  return json.dumps({'success': True, 'data': [c.name for c in matching]}), 200

@app.route('/api/convert_time/')
def convert_time():
  # This implementation does not address time zones, but as the app is intended for use on Cornell
  # campus, I felt this was an acceptable flaw
  fl = extract(request).get('time',None)
  if fl is None:
    return missing()
  fl = float(fl)
  t = datetime.datetime.fromtimestamp(fl)
  timeinfo = {'year': t.year, 'month': t.month, 'day': t.day, 'hour': t.hour, 'minute': t.minute}
  return json.dumps({'success': True, 'data': timeinfo}), 200

@app.route('/api/posts/<int:post_id>/photos/', methods=['POST'])
def add_post_photo(post_id):
  info = extract(request)
  uid = token_to_uid(info)
  if uid is None:
    return invalid_token()
  if not info.get('photo',''):
    return missing()
  post = Post.query.filter_by(id=post_id).first()
  if not post:
    return nopost()
  if not post.uid == uid:
    return wrong_token()
  if len(post.photos)>3:
    return json.dumps({'success': False, 'error': "Post already has four photos. Please delete one before adding another."}), 400
  
  photo = Photo.query.filter_by(val=info.get('photo')).first()
  if photo is not None:
    return json.dumps({'success': True, 'data': photo.serialize()}), 200

  photo = Photo(
    post_id=post_id,
    val=info.get('photo')
  )
  db.session.add(photo)
  db.session.commit()
  return json.dumps({'success': True, 'data': photo.serialize()}), 201

@app.route('/api/posts/<int:post_id>/photos/', methods=['DELETE'])
def remove_post_photo(post_id):
  info = extract(request)
  uid = token_to_uid(info)
  if uid is None:
    return invalid_token()
  if not info.get('photo_id',''):
    return missing()
  post = Post.query.filter_by(id=post_id).first()
  if not post:
    return nopost()
  if not post.uid == uid:
    return wrong_token()
  photo_id = int(info.get('photo_id'))
  photo = Photo.query.filter_by(id=photo_id).first()
  if not photo:
    return json.dumps({'success': False, 'error': 'Photo not found!'}), 404
  if not photo.post_id == post_id:
    return json.dumps({'success': False, 'error': 'Photo does not belong to the given post.'}), 400
  db.session.delete(photo)
  db.session.commit()
  return json.dumps({'success': True, 'data': photo.serialize()}), 200

@app.route('/api/posts/<int:post_id>/photos/')
def get_post_photos(post_id):
  post = Post.query.filter_by(id=post_id).first()
  if not post:
    return nopost()
  photos = [p.serialize() for p in post.photos]
  return json.dumps({'success': True, 'data': photos}), 200

@app.route('/api/users/profile/past_projects/', methods=['POST'])
def add_past_project():
  info = extract(request)
  if not all(info.get(i,'') for i in ['description', 'token', 'name']):
    return missing()
  uid = token_to_uid(info)
  if not uid:
    return invalid_token()
  if PastProject.query.filter_by(uid=uid,name=info.get('name')).first():
    return json.dumps({'success': False, 'error': 'User already has a project with this name.'}), 400
  proj = PastProject(
    uid=uid,
    name=info.get('name'),
    skills=clean_tags(info.get('skills','')),
    link=info.get('link'),
    description=info.get('description'),
    timestamp=time.time()
  )
  db.session.add(proj)
  db.session.commit()
  return json.dumps({'success': True, 'data': proj.serialize()}), 201

@app.route('/api/users/profile/past_projects/modify/', methods=['POST'])
def modify_past_project():
  info = extract(request)
  uid = token_to_uid(info)
  if not uid:
    return invalid_token()
  proj = PastProject.query
  if 'id' not in info:
    return missing()
  if info.get('id',None):
    proj = proj.filter_by(id=int(info.get('id')))
  proj = proj.first()
  if not proj:
    return nopost()
  if not proj.uid==uid:
    return invalid_token()
  if info.get('name',''):
    proj.name=info.get('name')
  if 'skills' in info:
    proj.skills=clean_tags(info.get('skills',''))
  if info.get('description',''):
    proj.description=info.get('description')
  if 'link' in info:
    proj.link=info.get('link','')
  db.session.commit()
  return json.dumps({'success': True, 'data': proj.serialize()}), 200

@app.route('/api/users/profile/past_projects/', methods=['DELETE'])
def remove_past_project():
  info = extract(request)
  uid = token_to_uid(info)
  if not uid:
    return invalid_token()
  proj = PastProject.query
  if info.get('id',None):
    proj = proj.filter_by(id=int(info.get('id')))
  proj = proj.first()
  if not proj:
    return nopost()
  if not proj.uid==uid:
    return invalid_token()
  db.session.delete(proj)
  db.session.commit()
  return json.dumps({'success': True, 'data': proj.serialize()}), 200

@app.route('/api/users/<int:uid>/profile/past_projects/')
def get_past_projects(uid):
  user = User.query.filter_by(uid=uid).first()
  if not user:
    return nouser()
  projs = user.past_projects
  #projs = PastProject.query.filter(uid=uid).all()
  projs = [p.serialize() for p in projs]
  return json.dumps({'success': True, 'data': projs}), 200

@app.route('/api/users/profile/past_projects/')
def get_own_past_projects():
  info = extract(request)
  uid = token_to_uid(info)
  if not uid:
    return invalid_token()
  projs = PastProject.query.filter_by(uid=uid).all()
  projs = [p.serialize() for p in projs]
  return json.dumps({'success': True, 'data': projs}), 200

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)
