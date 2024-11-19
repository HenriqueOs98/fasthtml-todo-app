from fasthtml.common import *
from dataclasses import dataclass
import httpx
import os
from datetime import datetime

# Define Login dataclass
@dataclass
class Login:
    name: str
    pwd: str

# Database setup
db = database('data/todos.db')
todos, users = db.t.todos, db.t.users

# Create tables if they don't exist
if todos not in db.t:
    users.create(dict(
        name=str,
        pwd=str,
        auth_type=str
    ), pk='name')
    
    todos.create(dict(
        id=int,
        title=str, 
        done=bool,
        name=str,
        details=str,
        priority=int,
        due_date=float,
        created_at=float
    ), pk='id')

Todo, User = todos.dataclass(), users.dataclass()

# Authentication setup
login_redir = RedirectResponse('/login', status_code=303)

def before(req, sess):
    auth = req.scope['auth'] = sess.get('auth', None)
    if not auth: return login_redir
    todos.xtra(name=auth)

bware = Beforeware(before, skip=[
    r'/favicon\.ico', 
    r'/static/.*', 
    r'.*\.css', 
    '/login',
    '/auth/github',
    '/auth/github/callback'
])

app, rt = fast_app(before=bware)
@rt("/login")
def post(login:Login, sess):
    if not login.name or not login.pwd: 
        return login_redir
    
    try:
        user = users[login.name]
        now = datetime.now().timestamp()
        
        # Check if account is locked
        if user.locked_until and now < user.locked_until:
            return "Account is temporarily locked. Please try again later."
        
        # Verify password with constant-time comparison
        if not compare_digest(user.pwd.encode(), login.pwd.encode()):
            # Update failed attempts
            failed = (user.failed_attempts or 0) + 1
            users.update({
                'failed_attempts': failed,
                'last_attempt': now
            }, user.name)
            
            # Lock account if too many failed attempts
            if failed >= MAX_FAILED_ATTEMPTS:
                lock_until = now + LOGIN_TIMEOUT
                users.update({'locked_until': lock_until}, user.name)
                return "Too many failed attempts. Account is temporarily locked."
            
            return login_redir
        
        # Reset failed attempts on successful login
        users.update({
            'failed_attempts': 0,
            'last_attempt': now,
            'locked_until': None
        }, user.name)
        
    except NotFoundError:
        # Create new user with secure defaults
        user = users.insert({
            'name': login.name,
            'pwd': login.pwd,
            'auth_type': 'local',
            'failed_attempts': 0,
            'last_attempt': datetime.now().timestamp(),
            'locked_until': None
        })
    
    # Set secure session
    sess['auth'] = user.name
    sess['last_activity'] = datetime.now().timestamp()
    return RedirectResponse('/', status_code=303)

@rt("/login")
def get():
    frm = Form(
        Input(id='name', placeholder='Username'),
        Input(id='pwd', type='password', placeholder='Password'),
        Button('Login'),
        action='/login', 
        method='post',
        style="margin-bottom: 2rem;"
    )
    
    return Titled("Login", frm)

@rt("/")
def get(auth):
    title = f"{auth}'s Tasks"
    top = Grid(
        H1(title), 
        Div(A('Logout', href='/logout'), style='text-align: right')
    )
    
    new_inp = Input(id="new-title", name="title", placeholder="What needs to be done?")
    add = Form(
        Group(new_inp, Button("Add Task")),
        hx_post="/", 
        target_id='todo-list', 
        hx_swap="afterbegin"
    )
    
    frm = Form(
        *todos(order_by='priority'),
        id='todo-list', 
        cls='sortable todo-list', 
        hx_post="/reorder", 
        hx_trigger="end"
    )
    
    card = Card(Ul(frm), header=add, footer=Div(id='current-todo'))
    return Title(title), Container(top, card)


@rt("/")
async def post(todo:Todo):
    # Add timestamps
    todo.created_at = datetime.now().timestamp()
    todo.updated_at = todo.created_at
    return todos.insert(todo)



@rt("/")
async def put(todo:Todo):
    # Update timestamp
    todo.updated_at = datetime.now().timestamp()
    return todos.update(todo)

# ... rest of your code ...
serve()