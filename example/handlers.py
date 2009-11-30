#/usr/bin/env python2.5
#-----------------------

"""
Provide user authentication request handlers.  Their names should be
self-explanatory.  You will need to modify them to work with your app.
"""

from google.appengine.ext.webapp import template

from users import User, UserSignup, salt_n_hash, signup_id


class Signup(RequestHandler):
	def post(self):
		nickname = self.request.get( 'nickname' )
		email = self.request.get( 'email' )
		password = self.request.get( 'password' )
		user = User.get_or_insert(nickname=nickname,
							email=email,
							pwd=salt_n_hash(password),
							key_name=nickname)
		self.session.start(None)
		if not User.authenticate(nickname, password):
			self.session[ 'flash_msg' ] = '<p>Sorry, the nickname you chose is already taken.</p>'
			self.redirect(self.request.url)
			return
		signup = UserSignup(user=user, key_name=signup_id(nickname))
		signup.put()
		confirm_url = self.request.relative_url('confirmsignup?id='+signup.id)
		from google.appengine.api import mail
		sender = 'Registrar <registrar@app-id.appspotmail.com>'
		subject = 'Confirm your registration'
		body = \
			'Hello %s,\n\n' % nickname + \
			'To confirm your registration, please visit the link below:\n\n' + \
			'<%s>\n' % confirm_url
		mail.send_mail( sender, email, subject, body )
		self.session[ 'flash_msg' ] = \
			'<p>Thank you for signing up, %s! A confirmation ' % nickname + \
			'message is on its way to your email inbox. It will contain a link ' + \
			'which you will need to visit in order to complete your registration.</p>' + \
			'<p>See you soon!</p>'
		self.redirect('/')


class ConfirmSignup(RequestHandler):
	def get(self):
		id = self.request.get('id')
		signup = UserSignup.get_by_key_name(id)
		if not signup:
			self.error(401)
			return
		user = signup.user
		user.suspended = False
		user.put()
		signup.delete()
		self.session.start(user)
		self.session['flash_msg'] = '<p>Your account has been confirmed.</p>'
		self.redirect('/user/' + user.nickname)


class Login(RequestHandler):
	"""Handle /login?redirect=%s request. You will need to define your GET method handler."""
	def post(self):
		user = User.authenticate(self.request.get('nickname'), self.request.get('password'))
		if user and not user.suspended:
			self.session.start(user)
			redirect = self.request.get('redirect')
			self.redirect(redirect)
		else:
			self.session.start( None )
			self.session[ 'flash_msg' ] = '<p>Incorrect nickname/password combination. Sorry!</p>'
			self.redirect(self.request.url)


def login_required(handler_method):
	"""
	A decorator to require that a user be logged in to access a handler method.

	>>> @login_required
	... def get(self):
	...     self.response.out.write('Hello, ' + self.session.user.nickname)

	We will redirect to a login page if the user is not logged in.
	"""
	def check_login(self, *args):
		if not self.session.user:
			self.redirect('/login?' + 'redirect=' + self.request.url)
		else:
			handler_method(self, *args)
	return check_login


class Logout(RequestHandler):
	def get(self):
		if not self.session.user:
			self.error(404)
			return
		nickname = self.session.user.nickname
		self.session.start(None)
		self.session['flash_msg'] = '<p>Goodbye, %s!</p>' % nickname
		self.redirect('/login')


ROUTES = (
	('/signup', Signup),
	('/confirmsignup', ConfirmSignup),
	('/login', Login),
	('/logout', Logout)
)
